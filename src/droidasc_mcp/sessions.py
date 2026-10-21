"""Bounded immutable DEX preparations, pinned while supervised queries execute."""

from __future__ import annotations

import copy
import itertools
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .runner import _check_cancelled


def error(code, message):
    return {"status": "error", "code": code, "message": message}


@dataclass
class Entry:
    storage: tempfile.TemporaryDirectory
    info: dict
    size: int
    touched: float
    order: int
    users: int = 0
    closing: bool = False


class DexSessions:
    def __init__(self, settings, runner):
        self.settings = settings
        self.runner = runner
        self.lock = threading.RLock()
        self.entries: dict[str, Entry] = {}
        self.order = itertools.count()
        self.reserved = 0
        self.opening = 0
        self.closed = False
        self.stop = threading.Event()
        self.reaper = None

    def _drop(self, key):
        entry = self.entries[key]
        entry.storage.cleanup()
        del self.entries[key]

    def _expire(self):
        now = time.monotonic()
        for key, entry in list(self.entries.items()):
            if not entry.users and (
                entry.closing or now - entry.touched >= self.settings.dex_session_ttl_seconds
            ):
                self._drop(key)

    def _sweep(self):
        interval = min(30, self.settings.dex_session_ttl_seconds)
        while not self.stop.wait(interval):
            with self.lock:
                self._expire()

    def open(self, paths):
        # Reserve for the ZIP bundle, a temporary single-DEX ZIP, and bounded metadata.
        input_bytes = sum(path.stat().st_size for path in paths)
        reservation = input_bytes * 2 + self.settings.max_output_bytes * 2 + 1024**2
        with self.lock:
            if self.closed:
                return error("session_store_closed", "Session store is closed")
            self._expire()
            if reservation > self.settings.max_dex_session_bytes:
                return error("session_capacity", "DEX preparation exceeds session disk budget")
            while (
                len(self.entries) + self.opening >= self.settings.max_dex_sessions
                or sum(e.size for e in self.entries.values()) + self.reserved + reservation
                > self.settings.max_dex_session_bytes
            ):
                candidates = [(e.order, key) for key, e in self.entries.items() if not e.users]
                if not candidates:
                    return error(
                        "session_capacity", "Session capacity is occupied by active analyses"
                    )
                self._drop(min(candidates)[1])
            self.opening += 1
            self.reserved += reservation
            if self.reaper is None:
                self.reaper = threading.Thread(
                    target=self._sweep, name="droidasc-session-reaper", daemon=True
                )
                self.reaper.start()
        storage = None
        committed = False
        try:
            storage = tempfile.TemporaryDirectory(prefix="droidasc-session-")
            root = Path(storage.name)
            info = self.runner.prepare_dex(paths, root, input_bytes)
            _check_cancelled()
            if info.get("status") != "ok":
                return info
            size = sum(path.stat().st_size for path in root.iterdir() if path.is_file())
            if size > reservation:
                return error("session_capacity", "Prepared data exceeds reserved disk budget")
            with self.lock:
                if self.closed:
                    return error("session_store_closed", "Session store closed during preparation")
                key = uuid.uuid4().hex
                self.entries[key] = Entry(
                    storage, copy.deepcopy(info), size, time.monotonic(), next(self.order)
                )
                committed = True
                return {
                    **info,
                    "session_id": key,
                    "reuse": "validated_dex_bundle",
                    "stored_bytes": size,
                    "idle_ttl_seconds": self.settings.dex_session_ttl_seconds,
                }
        finally:
            if storage is not None and not committed:
                storage.cleanup()
            with self.lock:
                self.opening -= 1
                self.reserved -= reservation

    def query(self, key, query):
        with self.lock:
            self._expire()
            entry = self.entries.get(key)
            if entry is None or entry.closing or self.closed:
                return error("session_not_found", "Session is unknown, expired, or closed")
            entry.users += 1
        try:
            result = self.runner.query_dex_session(Path(entry.storage.name), query)
            return {**result, "session_id": key}
        finally:
            with self.lock:
                entry.users -= 1
                entry.touched = time.monotonic()
                entry.order = next(self.order)
                if entry.closing and not entry.users:
                    self._drop(key)

    def close(self, key):
        with self.lock:
            self._expire()
            entry = self.entries.get(key)
            if entry is None:
                return error("session_not_found", "Session is unknown, expired, or closed")
            entry.closing = True
            pending = bool(entry.users)
            if not pending:
                self._drop(key)
            return {"status": "ok", "session_id": key, "cleanup_pending": pending}

    def shutdown(self):
        self.stop.set()
        if self.reaper is not None:
            self.reaper.join(timeout=2)
        with self.lock:
            self.closed = True
            for key, entry in list(self.entries.items()):
                entry.closing = True
                if not entry.users:
                    self._drop(key)
