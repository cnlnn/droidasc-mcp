"""Bounded immutable DEX preparations, pinned while supervised queries execute."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import secrets
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from .grouped_references import grouped_reference_page
from .memory_cache import PageCache
from .reference_cache import (
    MAX_SESSION_BYTES,
    MIN_ENTRY_BYTES,
    ReferenceCache,
    selector,
)
from .reference_cursor import cursor_identity
from .reference_page import operand_query, selected_query
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
    index_lock: threading.Lock = field(default_factory=threading.Lock)
    pages: PageCache = field(default_factory=PageCache)
    references: ReferenceCache | None = None
    query_locks: tuple = field(default_factory=lambda: tuple(threading.Lock() for _ in range(32)))
    cursor_key: bytes = field(default_factory=lambda: secrets.token_bytes(32), repr=False)


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

    def status(self):
        with self.lock:
            self._expire()
            return {
                "open_count": sum(not entry.closing for entry in self.entries.values()),
                "active_queries": sum(entry.users for entry in self.entries.values()),
                "opening_count": self.opening,
            }

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

    def open(self, paths, *, artifact=None, budget=None, module=None):
        # Reserve for the ZIP bundle, a temporary single-DEX ZIP, and bounded metadata.
        input_bytes = sum(path.stat().st_size for path in paths) if artifact is None else budget
        normalization = artifact is not None
        if artifact is None:
            for path in paths:
                with path.open("rb") as stream:
                    normalization |= stream.read(8) == b"dex\n041\0"
        index_budget = self.settings.max_xref_index_bytes
        reservation = (
            input_bytes * (7 if normalization else 2)
            + self.settings.max_output_bytes * 2
            + 1024**2
            + index_budget
        )
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
            info = (
                self.runner.prepare_dex(paths, root, input_bytes)
                if artifact is None
                else self.runner.prepare_artifact(artifact, root, budget, module)
            )
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
                    storage,
                    copy.deepcopy(info),
                    size + index_budget,
                    time.monotonic(),
                    next(self.order),
                )
                committed = True
                return {
                    **info,
                    "session_id": key,
                    "reuse": "validated_dex_bundle",
                    "stored_bytes": size,
                    "reserved_index_bytes": index_budget,
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
            if query.get("reference_format") == "grouped":
                root = Path(entry.storage.name)
                identity = cursor_identity(self.settings, root)
                if identity is None:
                    return error("reference_changed", "Reference preparation is unavailable")
                result = grouped_reference_page(
                    self.settings,
                    key,
                    entry.cursor_key,
                    query,
                    lambda page: self._query_entry(entry, page, reference_chunk=True),
                    identity,
                )
                if identity != cursor_identity(self.settings, root):
                    return error(
                        "reference_changed", "Reference preparation changed during collection"
                    )
            else:
                result = self._query_entry(entry, query)
            return {**result, "session_id": key}
        finally:
            with self.lock:
                entry.users -= 1
                entry.touched = time.monotonic()
                entry.order = next(self.order)
                if entry.closing and not entry.users:
                    self._drop(key)

    def _query_entry(self, entry, query, *, reference_chunk=False):
        from .xref_index import (
            DISCOVERY_OPERATIONS,
            INDEX_OPERATIONS,
            REFERENCE_OPERATIONS,
            STRUCTURE_OPERATIONS,
        )

        root = Path(entry.storage.name)
        if query.get("operation") not in (
            INDEX_OPERATIONS | REFERENCE_OPERATIONS | DISCOVERY_OPERATIONS | STRUCTURE_OPERATIONS
        ):
            return self.runner.query_dex_session(root, query)
        native_read = operand_query(query) or query.get("operation") in {
            "find_method_refs",
            "get_method_calls",
            "find_field_refs",
            "find_string_refs",
            "search_refs",
            "search_members",
            "search_strings",
            "search_classes",
        }
        # Equal selectors share a stripe; index publication uses the session builder lock.
        stripe = (
            int.from_bytes(
                hashlib.sha256(
                    json.dumps(
                        selector(query) if selected_query(query) else query,
                        sort_keys=True,
                    ).encode()
                ).digest()[:2],
                "big",
            )
            % 32
        )
        lock = entry.query_locks[stripe] if native_read else entry.index_lock
        with self.runner._acquire(lock):
            _check_cancelled()

            def execute():
                cache = self._reference_cache(entry, root, query)
                if cache is None:
                    return self.runner.query_dex_session(root, query)
                cached = cache.read_chunk(query) if reference_chunk else cache.read(query)
                if cached is not None:
                    return cached
                ticket = cache.begin(query)
                if ticket is None:
                    return self.runner.query_dex_session(root, query)
                publish = False
                try:
                    result = self.runner.query_dex_session(root, query, reference_cache=ticket)
                    publish = True
                    return result
                finally:
                    cache.finish(ticket, publish=publish)

            return (
                execute()
                if reference_chunk or query.get("operation") == "build_xref_index"
                else entry.pages.execute(self.settings, root, query, execute)
            )

    def _reference_cache(self, entry, root, query):
        if not selected_query(query):
            return None
        with self.lock:
            if entry.references is None:
                if not (root / "prepared.json").is_file():
                    return None
                budget = min(
                    MAX_SESSION_BYTES,
                    self.settings.max_dex_session_bytes
                    - self.reserved
                    - sum(e.size for e in self.entries.values()),
                )
                if budget < MIN_ENTRY_BYTES:
                    return None
                entry.references = ReferenceCache(self.settings, root, budget)
                entry.size += budget
            return entry.references

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

    def compare(self, old_key, new_key, query):
        with self.lock:
            self._expire()
            entries = {key: self.entries.get(key) for key in (old_key, new_key)}
            if self.closed or any(entry is None or entry.closing for entry in entries.values()):
                return error("session_not_found", "Both revision sessions must be open")
            for entry in entries.values():
                entry.users += 1
        try:
            result = self.runner.query_dex_session(
                Path(entries[old_key].storage.name),
                {
                    **query,
                    "operation": "revision_diff",
                    "other_prepared_root": entries[new_key].storage.name,
                },
            )
            return {**result, "old_session_id": old_key, "new_session_id": new_key}
        finally:
            with self.lock:
                for key, entry in entries.items():
                    entry.users -= 1
                    entry.touched = time.monotonic()
                    entry.order = next(self.order)
                    if entry.closing and not entry.users:
                        self._drop(key)

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
