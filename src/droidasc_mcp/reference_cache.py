"""Session-accounted selected reference sets with private worker publication."""

import hashlib
import json
import shutil
import sqlite3
import threading
import uuid
from collections import OrderedDict
from contextlib import closing, suppress
from pathlib import Path

from .memory_cache import signature
from .reference_page import OPERATIONS as OPERATIONS
from .reference_page import reference_page
from .reference_spool import (
    BLOCK_ROWS,
    MAX_BLOCK_BYTES,
    MAX_STORED_BLOCK_BYTES,
    MAX_VALUE_BYTES,
    RECEIPT_BYTES,
    SCHEMA,
    checksum,
    decode_block,
    file_identity,
)
from .runner import _check_cancelled

MAX_SESSION_BYTES = 32 * 1024**2
MAX_ENTRY_BYTES = 16 * 1024**2
MIN_ENTRY_BYTES = 64 * 1024


def selector(query):
    return {k: v for k, v in query.items() if k not in {"offset", "limit"}}


def _read_metadata(db, maximum):
    rows = db.execute(
        "SELECT CASE WHEN length(CAST(value AS BLOB))<=? THEN value END FROM metadata LIMIT 2",
        (maximum,),
    ).fetchall()
    if len(rows) != 1 or rows[0][0] is None:
        raise ValueError("Invalid reference metadata size")
    return json.loads(rows[0][0])


def _connect(path):
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("PRAGMA cache_size=-1024")
    except BaseException:
        with suppress(sqlite3.Error):
            db.close()
        raise
    return db


def _page_rows(db, start, stop):
    if start >= stop:
        return
    blocks = db.execute(
        "SELECT rowid,row_count,raw_bytes,CASE WHEN length(value)<=? THEN value END "
        "FROM sites WHERE rowid >= COALESCE((SELECT max(rowid) FROM sites WHERE rowid<=?),0) "
        "AND rowid<? ORDER BY rowid",
        (MAX_STORED_BLOCK_BYTES, start, stop),
    )
    position = start
    for first, count, raw_bytes, encoded in blocks:
        _check_cancelled()
        rows = decode_block(encoded, count, raw_bytes)
        if not first <= position < first + count:
            raise ValueError("Noncontiguous reference blocks")
        selected = rows[position - first : min(stop - first, count)]
        yield from selected
        position += len(selected)
    if position != stop:
        raise ValueError("Incomplete reference blocks")


class ReferenceCache:
    def __init__(self, settings, root, budget):
        self.settings = settings
        self.root = root
        self.directory = root / "reference-cache"
        self.budget = budget
        self.identity = None
        self.entries = OrderedDict()
        self.pending = {}
        self.used = 0
        self.lock = threading.RLock()

    def _key(self, query):
        identity = signature(self.settings, self.root)
        if identity != self.identity:
            for key in list(self.entries):
                self._drop(key)
            self.identity = identity
        key = hashlib.sha256(
            json.dumps([repr(identity), selector(query)], sort_keys=True).encode()
        ).hexdigest()
        return key, identity

    def _drop(self, key):
        path, size, _ = self.entries[key]
        try:
            shutil.rmtree(path.parent)
        except FileNotFoundError:
            pass
        except OSError:
            return False
        del self.entries[key]
        self.used -= size
        return True

    def _validate_read(self, path, expected, identity):
        if file_identity(path) != expected or identity != signature(self.settings, self.root):
            raise ValueError("Reference storage or prepared input changed during read")
        _check_cancelled()

    def read(self, query):
        _check_cancelled()
        with self.lock:
            key, identity = self._key(query)
            entry = self.entries.get(key) if identity is not None else None
            if entry is None:
                return None
            path, _, expected = entry
            try:
                if file_identity(path) != expected:
                    raise ValueError("Reference storage changed")
                maximum = min(MAX_VALUE_BYTES, self.settings.max_output_bytes)
                with closing(_connect(path)) as db:
                    metadata = _read_metadata(db, maximum)
                    base, definitions = metadata["base"], metadata["definitions"]
                    total = base["total"]
                    offset = query.get("offset", 0)
                    limit = min(query.get("limit", 100), self.settings.max_page_size)
                    if offset < 0 or limit <= 0:
                        return None
                    stop = min(offset + limit, total)
                    rows = _page_rows(db, offset, stop)
                    items, size, limited = [], 0, False
                    for row in rows:
                        _check_cancelled()
                        row_size = len(json.dumps(row, separators=(",", ":")).encode())
                        if row_size > maximum:
                            raise ValueError("Invalid reference row size")
                        size += row_size
                        if size > maximum:
                            limited = True
                            break
                        items.append(row)
                if not limited and len(items) != min(limit, max(0, total - offset)):
                    raise ValueError("Incomplete reference page")
                for row in items:
                    target = row.get("field_descriptor", row.get("callee"))
                    if target is None:
                        continue
                    row["target_dex_entry"] = definitions.get(target)
                    row["target_resolution"] = (
                        "defined_in_input" if target in definitions else "not_defined_in_input"
                    )
                more = offset + len(items) < total
                result = {
                    **base,
                    "items": items,
                    "offset": offset,
                    "limit": limit,
                    "has_more": more,
                    "truncated": more,
                    "next_offset": offset + len(items) if more else None,
                    "query_cache": {
                        "hit": True,
                        "scope": "selected_reference_set",
                        "budget_bytes": self.budget,
                        "stored_bytes": self.used,
                    },
                }
                result = reference_page(result, maximum, check=_check_cancelled)
                self._validate_read(path, expected, identity)
                self.entries.move_to_end(key)
                return result
            except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
                self._drop(key)
                return None

    def begin(self, query):
        _check_cancelled()
        with self.lock:
            key, identity = self._key(query)
            if (
                identity is None
                or key in self.entries
                or any(value[2] == key for value in self.pending.values())
            ):
                return None
            budget = min(MAX_ENTRY_BYTES, self.budget)
            if budget < MIN_ENTRY_BYTES:
                return None
            pending_bytes = sum(value[1] for value in self.pending.values())
            while self.entries and self.used + pending_bytes + budget > self.budget:
                if not self._drop(next(iter(self.entries))):
                    return None
            if self.used + pending_bytes + budget > self.budget:
                return None
            try:
                self.directory.mkdir(exist_ok=True)
                if self.directory.is_symlink():
                    return None
                directory = self.directory / (uuid.uuid4().hex + ".pending")
                directory.mkdir()
            except OSError:
                return None
            ticket = {"directory": str(directory), "key": key, "budget_bytes": budget}
            self.pending[str(directory)] = (identity, budget, key)
            return ticket

    def finish(self, ticket, *, publish):
        directory = Path(ticket["directory"])
        with self.lock:
            lease = self.pending.get(str(directory))
            if lease is None:
                return
            retained = False
            try:
                identity, budget, key = lease
                if not publish or identity != signature(self.settings, self.root):
                    return
                _check_cancelled()
                receipt_path = directory / "complete.json"
                if file_identity(receipt_path)[2] > RECEIPT_BYTES // 2:
                    return
                receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
                path = directory / "data.sqlite"
                expected = file_identity(path)
                size = expected[2] + receipt_path.stat().st_size
                if (
                    receipt["schema"] != SCHEMA
                    or receipt["key"] != key
                    or receipt["size"] != expected[2]
                    or size > budget
                    or {p.name for p in directory.iterdir()} != {"complete.json", "data.sqlite"}
                    or checksum(path, _check_cancelled) != receipt["sha256"]
                ):
                    return
                with closing(_connect(path)) as db:
                    meta = _read_metadata(db, min(MAX_VALUE_BYTES, self.settings.max_output_bytes))
                    total = meta["base"]["total"]
                    if (
                        meta["schema"] != SCHEMA
                        or meta["key"] != key
                        or meta["base"]["status"] != "ok"
                        or type(total) is not int
                        or not 0 <= total < 2**63
                        or not isinstance(meta["definitions"], dict)
                    ):
                        return
                    expected_row = 0
                    for first, count, raw_bytes, block_bytes in db.execute(
                        "SELECT rowid,row_count,raw_bytes,length(value) FROM sites ORDER BY rowid"
                    ):
                        _check_cancelled()
                        if (
                            first != expected_row
                            or type(count) is not int
                            or not 1 <= count <= BLOCK_ROWS
                            or type(raw_bytes) is not int
                            or not 2 <= raw_bytes <= MAX_BLOCK_BYTES
                            or type(block_bytes) is not int
                            or not 0 < block_bytes <= MAX_STORED_BLOCK_BYTES
                        ):
                            return
                        expected_row += count
                    if expected_row != total:
                        return
                if expected != file_identity(path) or identity != signature(
                    self.settings, self.root
                ):
                    return
                _check_cancelled()
                if key in self.entries and not self._drop(key):
                    return
                self.entries[key] = (path, size, expected)
                self.used += size
                retained = True
            except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
                pass
            finally:
                cleaned = True
                if not retained:
                    try:
                        shutil.rmtree(directory)
                    except FileNotFoundError:
                        pass
                    except OSError:
                        # Keep its reservation until session cleanup can remove the files.
                        cleaned = False
                if cleaned:
                    del self.pending[str(directory)]
