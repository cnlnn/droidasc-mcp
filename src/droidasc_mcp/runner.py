"""Bounded subprocess adapter for the public droidasc CLI."""

from __future__ import annotations

import io
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import threading
import time
from collections import OrderedDict
from concurrent.futures import CancelledError as FutureCancelledError
from concurrent.futures import Future
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import contextmanager, suppress
from contextvars import ContextVar
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Literal

import psutil
from anyio import from_thread

from .config import Settings

ReferenceKind = Literal["string", "type", "method", "field", "extends", "impl"]
PREPARATION_PROGRESS = ContextVar("droidasc_preparation_progress", default=None)


class DroidAscError(RuntimeError):
    """Raised when Droid ASC fails or violates an adapter limit."""


@dataclass(frozen=True)
class LinePage:
    items: list[str]
    total: int
    offset: int
    limit: int

    def as_dict(self) -> dict[str, object]:
        return {
            "items": self.items,
            "total": self.total,
            "offset": self.offset,
            "limit": self.limit,
            "truncated": self.offset + len(self.items) < self.total,
            "has_more": self.offset + len(self.items) < self.total,
            "next_offset": (
                self.offset + len(self.items)
                if self.offset + len(self.items) < self.total
                else None
            ),
        }


@dataclass(frozen=True)
class Snapshot:
    created_at: float
    lines: tuple[str, ...]
    size_bytes: int

    @classmethod
    def build(cls, data: bytes, *, sort: bool, budget: int) -> Snapshot:
        # Account for decoded strings and tuple pointers, not just wire bytes.
        lines = []
        used = sys.getsizeof(())
        if used > budget:
            raise DroidAscError("Decoded snapshot exceeds memory budget; narrow the query")
        pointer_bytes = sys.getsizeof((None,)) - sys.getsizeof(())
        for index, raw in enumerate(io.BytesIO(data)):
            if index % 256 == 0:
                _check_cancelled()
            line = raw.rstrip(b"\r\n").decode("utf-8", errors="replace")
            used += sys.getsizeof(line) + pointer_bytes
            if used > budget:
                raise DroidAscError("Decoded snapshot exceeds memory budget; narrow the query")
            lines.append(line)
        if sort:
            lines.sort()
        return cls(time.monotonic(), tuple(lines), used)


class DroidAscRunner:
    """Runs each ASC operation in a supervised process tree."""

    def __init__(
        self,
        settings: Settings,
        *,
        python_executable: str | None = None,
        module_name: str = "droidasc",
    ) -> None:
        self.settings = settings
        self.python_executable = python_executable or sys.executable
        self.module_name = module_name
        self._slots = threading.BoundedSemaphore(settings.max_parallel)
        self._cache_lock = threading.Lock()
        self._cache = OrderedDict()
        self._inflight: dict[tuple, Future] = {}

    def get_manifest(self, apk: Path, *, offset: int, limit: int) -> LinePage:
        return self._run_paged(["getmanifest", str(apk)], offset=offset, limit=limit)

    def apk_info(self, apk: Path, include_sha256: bool) -> dict:
        with self._acquire(self._slots):
            data = self._execute(
                [str(apk), "sha256" if include_sha256 else "no-hash"],
                module_name="droidasc_mcp.info_worker",
            )
        if len(data) > 256 * 1024:
            raise DroidAscError("APK metadata exceeds response budget")
        return json.loads(data)

    def query_archive(self, apk: Path, query: dict) -> dict:
        if query.get("operation") in {
            "list_entries",
            "manifest_summary",
            "manifest_xml",
            "artifact_inventory",
        }:
            offset, limit = self._page_bounds(query.get("offset", 0), query.get("limit", 100))
            query = {**query, "offset": offset, "limit": limit}
        request = {
            "apk_path": str(apk),
            "allowed_roots": [str(path) for path in self.settings.allowed_roots],
            "max_input_bytes": self.settings.max_apk_bytes,
            "max_output_bytes": self.settings.max_output_bytes,
            "max_page_size": self.settings.max_page_size,
            "query": query,
        }
        with tempfile.TemporaryDirectory(prefix="droidasc-apk-") as root:
            request_path = Path(root) / "request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            with self._acquire(self._slots):
                data = self._execute([str(request_path)], module_name="droidasc_mcp.archive_worker")
        if len(data) > 256 * 1024:
            raise DroidAscError("APK response exceeds response budget")
        return json.loads(data)

    def analyze_dex(self, paths: list[Path], query: dict) -> dict:
        request = self._dex_request(paths, query)
        # The parent owns temporary storage so cancellation/worker kills also clean it up.
        with tempfile.TemporaryDirectory(prefix="droidasc-dex-") as root:
            return self._run_dex_request(request, Path(root))

    def prepare_dex(self, paths: list[Path], root: Path, input_bytes: int) -> dict:
        request = self._dex_request(paths, {"operation": "info", "offset": 0, "limit": 1})
        request["max_input_bytes"] = min(input_bytes, self.settings.max_apk_bytes)
        request["prepare"] = True
        return self._run_dex_request(request, root)

    def prepare_artifact(self, path: Path, root: Path, budget: int, module: str | None) -> dict:
        request = self._dex_request([], {"operation": "info", "offset": 0, "limit": 1})
        request.update(
            artifact_path=str(path), max_uncompressed_bytes=budget, module=module, prepare=True
        )
        return self._run_dex_request(request, root)

    def query_dex_session(self, root: Path, query: dict) -> dict:
        request = self._dex_request([], query)
        request["prepared_root"] = str(root)
        with tempfile.TemporaryDirectory(prefix="droidasc-query-") as temporary:
            return self._run_dex_request(request, Path(temporary))

    def _dex_request(self, paths: list[Path], query: dict) -> dict:
        return {
            "paths": [str(path) for path in paths],
            "allowed_roots": [str(path) for path in self.settings.allowed_roots],
            "max_input_bytes": self.settings.max_apk_bytes,
            "max_output_bytes": self.settings.max_output_bytes,
            "max_page_size": self.settings.max_page_size,
            "max_xref_index_bytes": self.settings.max_xref_index_bytes,
            "xref_cache_dir": str(self.settings.xref_cache_dir)
            if self.settings.xref_cache_dir
            else None,
            "max_xref_cache_bytes": self.settings.max_xref_cache_bytes,
            "xref_cache_ttl_seconds": self.settings.xref_cache_ttl_seconds,
            "jadx_home": str(self.settings.jadx_home) if self.settings.jadx_home else None,
            "dexlib_home": str(self.settings.dexlib_home) if self.settings.dexlib_home else None,
            "java_executable": self.settings.java_executable,
            "query": query,
        }

    def _run_dex_request(self, request: dict, root: Path) -> dict:
        with self._acquire(self._slots):
            request_path = root / "request.json"
            request_path.write_text(json.dumps(request), encoding="utf-8")
            data = self._execute([str(request_path)], module_name="droidasc_mcp.dex_worker")
        if len(data) > 256 * 1024:
            raise DroidAscError("DEX result exceeds response budget; narrow the query")
        return json.loads(data)

    @contextmanager
    def _acquire(self, lock):
        deadline = time.monotonic() + self.settings.timeout_seconds
        while True:
            _check_cancelled()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise DroidAscError("Analysis queue timed out; retry later")
            if lock.acquire(timeout=min(0.05, remaining)):
                break
        try:
            yield
        finally:
            lock.release()

    def list_classes(
        self,
        apk: Path,
        *,
        prefix: str | None,
        threads: int,
        offset: int,
        limit: int,
    ) -> LinePage:
        args = ["listclass", "--threads", str(_threads(threads)), str(apk)]
        if prefix:
            args.append("--prefix=" + prefix)
        return self._run_paged(args, offset=offset, limit=limit)

    def get_class_source(
        self,
        apk: Path,
        *,
        class_name: str,
        threads: int,
        offset: int,
        limit: int,
    ) -> LinePage:
        args = [
            "getclass",
            "--threads",
            str(_threads(threads)),
            str(apk),
            class_name,
        ]
        return self._run_paged(args, offset=offset, limit=limit)

    def find_refs(
        self,
        apk: Path,
        *,
        kind: ReferenceKind,
        value: str | None,
        class_name: str | None,
        fuzzy_class: bool,
        threads: int,
        offset: int,
        limit: int,
    ) -> dict[str, object]:
        # ASC dispatches this token before argparse processes the option terminator.
        if value == "--gui":
            raise ValueError("The droidasc CLI reserves '--gui'; use a narrower search value")
        if kind not in {"string", "type", "method", "field", "extends", "impl"}:
            raise ValueError("Unknown reference kind")
        hierarchy = kind in {"extends", "impl"}
        if hierarchy and (class_name is not None or fuzzy_class):
            raise ValueError("Hierarchy searches use value only; class filters are not supported")
        if kind in {"string", "type", "extends", "impl"}:
            if not value:
                raise ValueError(f"value is required for {kind} searches")
            query_args = [kind, "--", value]
        else:
            if not value and not class_name:
                raise ValueError(f"{kind} search needs value or class_name")
            query_args = [kind]
            if class_name:
                query_args.append("--class=" + class_name)
            if fuzzy_class:
                query_args.append("--fuzzy-class")
            if value:
                query_args.extend(["--", value])

        args = ["findrefs", "--threads", str(_threads(threads)), str(apk), *query_args]
        page = self._run_paged(args, offset=offset, limit=limit)
        parsed = [
            _parse_hierarchy(line, kind) if hierarchy else _parse_reference(line)
            for line in page.items
        ]
        result = page.as_dict()
        result["items"] = parsed
        result["format"] = "cli-text-best-effort"
        result["warning"] = (
            "CLI text may contain embedded newlines; "
            "total counts output lines, not semantic references."
        )
        if hierarchy:
            result["relation_scope"] = "direct"
            result["warning"] = (
                "Direct DEX declarations only, not transitive inheritance or runtime dispatch. "
                "CLI text is parsed best-effort; raw output is preserved."
            )
        return result

    def _run_paged(self, args: list[str], *, offset: int, limit: int) -> LinePage:
        offset, limit = self._page_bounds(offset, limit)
        snapshot = self._get_snapshot(args)
        items = []
        used = 0
        for line in snapshot.lines[offset : offset + limit]:
            size = len(json.dumps(line, ensure_ascii=True).encode()) * 3 + 256
            if used + size > 256 * 1024:
                if not items:
                    raise DroidAscError(
                        "A single line exceeds the response budget; narrow the query"
                    )
                break
            items.append(line)
            used += size
        return LinePage(items, len(snapshot.lines), offset, limit)

    def _get_snapshot(self, args: list[str]) -> Snapshot:
        apk = next(Path(arg) for arg in args if Path(arg).suffix.lower() == ".apk")
        stat = apk.stat()
        key = (
            tuple(args),
            stat.st_dev,
            stat.st_ino,
            stat.st_size,
            stat.st_mtime_ns,
            stat.st_ctime_ns,
        )
        with self._acquire(self._cache_lock):
            now = time.monotonic()
            for old in list(self._cache):
                if now - self._cache[old].created_at > 60:
                    del self._cache[old]
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            pending = self._inflight.get(key)
            leader = pending is None
            if leader:
                pending = Future()
                self._inflight[key] = pending
        # Only identical queries wait for one another. No subprocess runs under the cache lock.
        if not leader:
            deadline = time.monotonic() + self.settings.timeout_seconds
            while True:
                _check_cancelled()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise DroidAscError("Snapshot wait timed out; retry later")
                try:
                    return pending.result(timeout=min(0.05, remaining))
                except FutureCancelledError:
                    with self._cache_lock:
                        if self._inflight.get(key) is pending:
                            self._inflight.pop(key)
                    return self._get_snapshot(args)
                except FutureTimeoutError:
                    pass
        try:
            with self._acquire(self._slots):
                data = self._execute(args)
                after = apk.stat()
                if (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns) != (
                    after.st_dev,
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                    after.st_ctime_ns,
                ):
                    raise DroidAscError("APK changed during analysis; retry the query")
                snapshot = Snapshot.build(
                    data, sort=args[0] == "findrefs", budget=self.settings.max_output_bytes
                )
                del data
            with self._acquire(self._cache_lock):
                while (
                    self._cache
                    and sum(entry.size_bytes for entry in self._cache.values())
                    + snapshot.size_bytes
                    > self.settings.max_output_bytes
                ):
                    self._cache.popitem(last=False)
                if len(self._cache) >= 8:
                    self._cache.popitem(last=False)
                self._cache[key] = snapshot
            pending.set_result(snapshot)
            return snapshot
        except BaseException as exc:
            if isinstance(exc, Exception):
                pending.set_exception(exc)
            else:
                pending.cancel()
            raise
        finally:
            with self._cache_lock:
                if self._inflight.get(key) is pending:
                    self._inflight.pop(key)

    def _page_bounds(self, offset: int, limit: int) -> tuple[int, int]:
        if offset < 0:
            raise ValueError("offset must be zero or greater")
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        return offset, min(limit, self.settings.max_page_size)

    def _command(self, args: list[str], module_name: str | None) -> list[str]:
        return [self.python_executable, "-m", module_name or self.module_name, *args]

    def _execute(self, args: list[str], *, module_name: str | None = None) -> bytes:
        command = self._command(args, module_name)
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        try:
            process, job = _start_process(command, env, self.settings.max_worker_memory_bytes)
        except Exception as exc:
            raise DroidAscError("Could not start supervised Droid ASC worker") from exc
        exceeded = threading.Event()
        stopped = threading.Event()
        read_errors = []
        buffers = [bytearray(), bytearray()]

        def drain(stream, buffer, cap):
            try:
                if os.name == "nt":
                    from .windows_job import read_pipe

                    read = partial(read_pipe, stream, stopped)
                else:
                    read = partial(stream.read, 8192)
                while chunk := read():
                    remaining = cap - len(buffer)
                    buffer.extend(chunk[:remaining])
                    if len(chunk) > remaining:
                        exceeded.set()
                        return
            except Exception as exc:
                read_errors.append(exc)
            finally:
                try:
                    stream.close()
                except Exception as exc:
                    read_errors.append(exc)

        deadline = time.monotonic() + self.settings.timeout_seconds
        memory_check_at = 0.0
        progress_at = 0.0
        last_progress = None
        progress_callback = PREPARATION_PROGRESS.get()
        progress_path = (
            Path(args[0]).parent / "progress.json"
            if (progress_callback and module_name == "droidasc_mcp.dex_worker" and args)
            else None
        )
        started = []
        try:
            readers = [
                threading.Thread(
                    target=drain,
                    args=(stream, buffer, cap),
                    daemon=True,
                    name=f"droidasc-reader-{index}",
                )
                for index, (stream, buffer, cap) in enumerate(
                    (
                        (process.stdout, buffers[0], self.settings.max_output_bytes),
                        (process.stderr, buffers[1], 65536),
                    )
                )
            ]
            for reader in readers:
                reader.start()
                started.append(reader)
            while True:
                _check_cancelled()
                now = time.monotonic()
                if progress_path is not None and (now >= progress_at or process.poll() is not None):
                    progress_at = now + 0.1
                    try:
                        encoded = progress_path.read_bytes()
                        if encoded != last_progress:
                            update = json.loads(encoded)
                            progress_callback(
                                update["completed"], update["total"], update["message"]
                            )
                            last_progress = encoded
                    except (FileNotFoundError, ValueError, KeyError):
                        pass
                if now >= memory_check_at:
                    if _process_tree_rss(process.pid) > self.settings.max_worker_memory_bytes:
                        raise DroidAscError(
                            "Droid ASC exceeded the configured aggregate worker memory limit"
                        )
                    memory_check_at = now + 0.05
                if exceeded.is_set():
                    raise DroidAscError("Droid ASC output exceeds configured stream limit")
                if read_errors:
                    raise DroidAscError("Droid ASC stream read failed") from read_errors[0]
                if process.poll() is not None and not any(r.is_alive() for r in readers):
                    break
                if now >= deadline:
                    raise DroidAscError(
                        f"Droid ASC timed out after {self.settings.timeout_seconds} seconds"
                    )
                time.sleep(0.01)
            # Readers may finish between the loop's flag check and completion check.
            if exceeded.is_set():
                raise DroidAscError("Droid ASC output exceeds configured stream limit")
            if read_errors:
                raise DroidAscError("Droid ASC stream read failed") from read_errors[0]
            if process.returncode != 0:
                stderr = buffers[1].decode("utf-8", errors="replace")
                if "DROIDASC_MCP_MEMORY_LIMIT_EXCEEDED" in stderr:
                    raise DroidAscError("Droid ASC exceeded the configured worker memory limit")
                detail = _clean_error(stderr)
                raise DroidAscError(f"Droid ASC failed: {detail or process.returncode}")
            return bytes(buffers[0])
        finally:
            try:
                _terminate_process_tree(process, job)
            finally:
                stopped.set()
                for reader in started:
                    reader.join(timeout=1)
                with suppress(subprocess.TimeoutExpired):
                    process.wait(timeout=2)
                if not any(reader.is_alive() for reader in started):
                    for stream in (process.stdout, process.stderr):
                        with suppress(OSError):
                            stream.close()


def _threads(value: int) -> int:
    if value <= 0:
        raise ValueError("threads must be greater than zero")
    return min(value, 32)


def _parse_hierarchy(line: str, kind: str) -> dict[str, str]:
    relation = "extends" if kind == "extends" else "implements"
    match = re.fullmatch(
        rf"(classes(?:[0-9]+)?\.dex) \| (L[^\s;|]+;) {relation} (L[^\s;|]+;)", line
    )
    if not match:
        return {"raw": line}
    dex, class_name, target = match.groups()
    return {
        "dex": dex,
        "class_name": class_name,
        "relation": relation,
        "target": target,
        "raw": line,
    }


def _parse_reference(line: str) -> dict[str, str]:
    parts = line.split(" | ", 2)
    if len(parts) != 3:
        return {"raw": line}
    matched = parts[2]
    if matched.startswith("matched=(") and matched.endswith(")"):
        matched = matched[9:-1]
    return {"dex": parts[0], "method": parts[1], "matched": matched, "raw": line}


def _clean_error(value: str | None) -> str:
    if not value:
        return ""
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    text = " | ".join(lines[-20:])
    return text[-8000:]


def _check_cancelled() -> None:
    # Direct library callers are not necessarily running in an AnyIO worker thread.
    with suppress(RuntimeError):
        from_thread.check_cancelled()


def _process_tree_rss(pid: int) -> int:
    if os.name != "nt":
        total = 0
        for process in psutil.process_iter():
            try:
                if os.getpgid(process.pid) == pid:
                    total += process.memory_info().rss
            except (ProcessLookupError, psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return total
    try:
        owner = psutil.Process(pid)
        processes = [owner, *owner.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0
    total = 0
    for process in processes:
        with suppress(psutil.NoSuchProcess, psutil.AccessDenied):
            total += process.memory_info().rss
    return total


def _start_process(command, env, memory_limit_bytes=None):
    if os.name == "nt":
        from .windows_job import start_process

        return start_process(command, env, memory_limit_bytes)
    worker_env = env.copy()
    if memory_limit_bytes is not None:
        worker_env["DROIDASC_MCP_WORKER_MEMORY_BYTES"] = str(memory_limit_bytes)
    bootstrap = str(Path(__file__).with_name("worker_bootstrap.py"))
    return subprocess.Popen(
        [command[0], bootstrap, *command[2:]],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=worker_env,
        start_new_session=True,
    ), None


def _terminate_process_tree(process: subprocess.Popen, job=None) -> None:
    if job is not None:
        job.close()
        return
    if os.name == "nt":
        raise DroidAscError("Windows worker has no Job Object")
    # The group can outlive its leader. Never gate cleanup on parent.poll().
    with suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGKILL)
