"""Bounded subprocess adapter for the public droidasc CLI."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .config import Settings

ReferenceKind = Literal["string", "type", "method", "field"]


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
        }


class DroidAscRunner:
    """Runs each ASC operation in an isolated process group."""

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

    def get_manifest(self, apk: Path, *, offset: int, limit: int) -> LinePage:
        return self._run_paged(["getmanifest", str(apk)], offset=offset, limit=limit)

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
            args.extend(["--prefix", prefix])
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
        if kind in {"string", "type"}:
            if not value:
                raise ValueError(f"value is required for {kind} searches")
            query_args = [kind, value]
        else:
            if not value and not class_name:
                raise ValueError(f"{kind} search needs value or class_name")
            query_args = [kind]
            if value:
                query_args.append(value)
            if class_name:
                query_args.extend(["--class", class_name])
            if fuzzy_class:
                query_args.append("--fuzzy-class")

        args = ["findrefs", "--threads", str(_threads(threads)), str(apk), *query_args]
        page = self._run_paged(args, offset=offset, limit=limit)
        parsed = [_parse_reference(line) for line in page.items]
        result = page.as_dict()
        result["items"] = parsed
        return result

    def _run_paged(self, args: list[str], *, offset: int, limit: int) -> LinePage:
        offset, limit = self._page_bounds(offset, limit)
        with self._slots, tempfile.TemporaryDirectory(prefix="droidasc-mcp-") as directory:
            output = Path(directory) / "result.txt"
            self._execute([*args, "-o", str(output)])
            if not output.is_file():
                raise DroidAscError("Droid ASC completed without creating its output file")
            size = output.stat().st_size
            if size > self.settings.max_output_bytes:
                raise DroidAscError(
                    f"Droid ASC output exceeds {self.settings.max_output_bytes} bytes; "
                    "narrow the query with a prefix or a more specific reference"
                )
            return _read_line_page(output, offset=offset, limit=limit)

    def _page_bounds(self, offset: int, limit: int) -> tuple[int, int]:
        if offset < 0:
            raise ValueError("offset must be zero or greater")
        if limit <= 0:
            raise ValueError("limit must be greater than zero")
        return offset, min(limit, self.settings.max_page_size)

    def _execute(self, args: list[str]) -> None:
        command = [self.python_executable, "-m", self.module_name, *args]
        env = os.environ.copy()
        env.setdefault("PYTHONUTF8", "1")
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            start_new_session=os.name != "nt",
            creationflags=creationflags,
        )
        try:
            _, stderr = process.communicate(timeout=self.settings.timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            _terminate_process_tree(process)
            _, stderr = process.communicate()
            detail = _clean_error(stderr)
            suffix = f": {detail}" if detail else ""
            raise DroidAscError(
                f"Droid ASC timed out after {self.settings.timeout_seconds} seconds{suffix}"
            ) from exc
        if process.returncode != 0:
            detail = _clean_error(stderr) or f"exit code {process.returncode}"
            raise DroidAscError(f"Droid ASC failed: {detail}")


def _threads(value: int) -> int:
    if value <= 0:
        raise ValueError("threads must be greater than zero")
    return min(value, 32)


def _read_line_page(path: Path, *, offset: int, limit: int) -> LinePage:
    items: list[str] = []
    total = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for total, line in enumerate(handle, start=1):
            index = total - 1
            if offset <= index < offset + limit:
                items.append(line.rstrip("\r\n"))
    return LinePage(items=items, total=total, offset=offset, limit=limit)


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


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":  # pragma: no cover - exercised by Windows CI only
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=2)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
