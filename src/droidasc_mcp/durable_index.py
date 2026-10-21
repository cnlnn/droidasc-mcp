"""Opt-in content-addressed index copies with a process-safe disk budget."""

import hashlib
import json
import os
import re
import shutil
import stat
import time
from contextlib import contextmanager

from .runner import DroidAscError

_KEY = re.compile(r"[0-9a-f]{64}")
_MANIFEST_LIMIT = 4096
_MAX_ENTRIES = 64


def _copy(source, target, limit):
    digest = hashlib.sha256()
    size = 0
    with source.open("rb") as reader, target.open("xb") as writer:
        while block := reader.read(1024 * 1024):
            size += len(block)
            if size > limit:
                raise DroidAscError("Persistent index copy exceeds disk budget")
            writer.write(block)
            digest.update(block)
        writer.flush()
        os.fsync(writer.fileno())
    return size, digest.hexdigest()


class DurableIndexes:
    def __init__(self, settings):
        self.root = settings.xref_cache_dir
        self.budget = settings.max_xref_cache_bytes
        self.index_limit = settings.max_xref_index_bytes
        self.ttl = settings.xref_cache_ttl_seconds

    @contextmanager
    def _locked(self):
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = self.root.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise DroidAscError("Persistent index cache must be a real directory")
        if os.name != "nt" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
            raise DroidAscError("Persistent index cache requires an owner-only directory (0700)")
        lock = self.root / "cache.lock"
        if lock.is_symlink():
            raise DroidAscError("Persistent index cache lock cannot be a symlink")
        with lock.open("a+b") as handle:
            if not lock.stat().st_size:
                handle.write(b"0")
                handle.flush()
            while True:
                try:
                    handle.seek(0)
                    if os.name == "nt":
                        import msvcrt

                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl

                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    time.sleep(0.05)
                except OSError as exc:
                    if os.name != "nt" or exc.errno not in (13, 36):
                        raise
                    time.sleep(0.05)
            try:
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _entries(self):
        entries = []
        now = time.time()
        for path in self.root.iterdir():
            if path.name == "cache.lock":
                continue
            if path.name == "pending" or _KEY.fullmatch(path.name):
                if path.is_symlink() or not path.is_dir():
                    raise DroidAscError("Unexpected persistent index cache entry")
                if path.name == "pending" or now - path.stat().st_mtime >= self.ttl:
                    shutil.rmtree(path)
                    continue
                files = list(path.iterdir())
                if any(p.is_symlink() or not p.is_file() for p in files):
                    raise DroidAscError("Unexpected persistent index cache contents")
                entries.append((path, sum(p.stat().st_size for p in files)))
            else:
                raise DroidAscError("Persistent index cache directory contains unrelated files")
        entries.sort(key=lambda item: (item[0].stat().st_mtime_ns, item[0].name))
        while entries and (sum(n for _, n in entries) > self.budget or len(entries) > _MAX_ENTRIES):
            shutil.rmtree(entries.pop(0)[0])
        return entries

    @staticmethod
    def _key(identity):
        return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()

    def restore(self, identity, target, workspace):
        if self.root is None:
            return False
        with self._locked():
            self._entries()
            entry = self.root / self._key(identity)
            if not entry.is_dir():
                return False
            temporary = workspace / "restored.partial.sqlite"
            try:
                manifest = entry / "manifest.json"
                if manifest.stat().st_size > _MANIFEST_LIMIT:
                    raise ValueError("manifest size")
                data = json.loads(manifest.read_bytes())
                if (
                    data["identity"] != identity
                    or data["size"] > self.index_limit
                    or (entry / "index.sqlite").stat().st_size != data["size"]
                ):
                    raise ValueError("identity or quota")
                from .query_cache import clear_cache

                clear_cache(target.parent)
                size, digest = _copy(entry / "index.sqlite", temporary, self.index_limit)
                if (size, digest) != (data["size"], data["sha256"]):
                    raise ValueError("checksum")
                os.replace(temporary, target)
                os.utime(entry, None)
                return True
            except (ValueError, KeyError, TypeError, FileNotFoundError):
                # Incomplete or corrupted entries are rebuildable, never query evidence.
                shutil.rmtree(entry)
                return False
            finally:
                temporary.unlink(missing_ok=True)

    def publish(self, identity, source):
        if self.root is None:
            return "disabled"
        size = source.stat().st_size
        if size > self.index_limit or size + _MANIFEST_LIMIT > self.budget:
            return "too_large"
        with self._locked():
            entries = self._entries()
            destination = self.root / self._key(identity)
            # A second builder may finish after the first; publish our verified copy.
            entries = [(p, n) for p, n in entries if p != destination]
            if destination.exists():
                shutil.rmtree(destination)
            while entries and (
                sum(n for _, n in entries) + size + _MANIFEST_LIMIT > self.budget
                or len(entries) >= _MAX_ENTRIES
            ):
                shutil.rmtree(entries.pop(0)[0])
            pending = self.root / "pending"
            pending.mkdir(mode=0o700)
            try:
                size, digest = _copy(source, pending / "index.sqlite", self.index_limit)
                data = json.dumps({"identity": identity, "size": size, "sha256": digest}).encode()
                if len(data) > _MANIFEST_LIMIT:
                    raise DroidAscError("Persistent index manifest exceeds budget")
                with (pending / "manifest.json").open("xb") as writer:
                    writer.write(data)
                    writer.flush()
                    os.fsync(writer.fileno())
                os.replace(pending, destination)
                return "stored"
            finally:
                if pending.exists():
                    shutil.rmtree(pending)
