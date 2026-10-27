"""Worker-owned, bounded storage of one complete selected reference scan."""

import hashlib
import json
import os
import sqlite3
import zlib
from contextlib import suppress
from pathlib import Path

SCHEMA = 2
MAX_VALUE_BYTES = 256 * 1024
BLOCK_ROWS = 128
BLOCK_BYTES = 64 * 1024
MAX_BLOCK_BYTES = MAX_VALUE_BYTES + 2
MAX_STORED_BLOCK_BYTES = MAX_BLOCK_BYTES + 1024
RECEIPT_BYTES = 8192
PAGE_FIELDS = {
    "items",
    "offset",
    "limit",
    "has_more",
    "truncated",
    "next_offset",
    "query_cache",
    "page_limited_by",
    "response_byte_limit",
}


def file_identity(path):
    stat = path.lstat()
    if not path.is_file() or path.is_symlink():
        raise OSError("Reference cache requires a regular file")
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def checksum(path, check=lambda: None):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(64 * 1024):
            check()
            digest.update(chunk)
    check()
    return digest.hexdigest()


def decode_block(encoded, count, raw_bytes):
    if (
        type(count) is not int
        or not 1 <= count <= BLOCK_ROWS
        or type(raw_bytes) is not int
        or not 2 <= raw_bytes <= MAX_BLOCK_BYTES
        or not isinstance(encoded, bytes)
        or not 0 < len(encoded) <= MAX_STORED_BLOCK_BYTES
    ):
        raise ValueError("Invalid reference block bounds")
    decoder = zlib.decompressobj()
    try:
        raw = decoder.decompress(encoded, raw_bytes + 1)
    except zlib.error as exc:
        raise ValueError("Invalid compressed reference block") from exc
    if len(raw) != raw_bytes or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
        raise ValueError("Incomplete or oversized reference block")
    rows = json.loads(raw.decode("utf-8"))
    if (
        not isinstance(rows, list)
        or len(rows) != count
        or not all(isinstance(r, dict) for r in rows)
    ):
        raise ValueError("Invalid reference block rows")
    return rows


class ReferenceSpool:
    def __init__(self, ticket, root, max_output_bytes):
        self.db = None
        self.enabled = False
        self.complete = False
        self.definitions = {}
        self.rows = 0
        self.buffer = []
        self.buffer_bytes = 2
        self.path = None
        self.limit = min(MAX_VALUE_BYTES, max_output_bytes)
        if ticket is None:
            return
        try:
            directory = Path(ticket["directory"])
            parent = root / "reference-cache"
            if (
                directory.parent != parent
                or directory.is_symlink()
                or parent.is_symlink()
                or len(directory.name) != 40
                or not directory.name.endswith(".pending")
                or any(c not in "0123456789abcdef" for c in directory.name[:-8])
                or list(directory.iterdir())
            ):
                return
            self.path = directory / "data.sqlite"
            self.key = ticket["key"]
            self.budget = ticket["budget_bytes"]
            pages = (self.budget - RECEIPT_BYTES) // 4096
            if pages < 4:
                return
            self.db = sqlite3.connect(self.path)
            self.db.execute("PRAGMA page_size=4096")
            self.db.execute(f"PRAGMA max_page_count={pages}")
            self.db.execute("PRAGMA cache_size=-2048")
            self.db.execute("PRAGMA journal_mode=OFF")
            self.db.execute("PRAGMA temp_store=MEMORY")
            self.db.execute(
                "CREATE TABLE sites (first_row INTEGER PRIMARY KEY, row_count INTEGER NOT NULL, "
                "raw_bytes INTEGER NOT NULL, value BLOB NOT NULL)"
            )
            self.db.execute("CREATE TABLE metadata (value TEXT NOT NULL)")
            self.enabled = True
        except (OSError, sqlite3.Error, KeyError, TypeError, ValueError):
            self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __call__(self, row):
        if not self.enabled:
            return
        try:
            encoded = json.dumps(row, separators=(",", ":")).encode()
            if len(encoded) > self.limit:
                self.close()
                return
            if self.buffer and self.buffer_bytes + len(encoded) + 1 > BLOCK_BYTES:
                self._flush()
            self.buffer_bytes += len(encoded) + bool(self.buffer)
            self.buffer.append(encoded)
            self.rows += 1
            if len(self.buffer) == BLOCK_ROWS or self.buffer_bytes >= BLOCK_BYTES:
                self._flush()
        except (OSError, sqlite3.Error):
            self.close()

    def _flush(self):
        if not self.buffer:
            return
        raw = b"[" + b",".join(self.buffer) + b"]"
        self.db.execute(
            "INSERT INTO sites VALUES (?,?,?,?)",
            (self.rows - len(self.buffer), len(self.buffer), len(raw), zlib.compress(raw, 1)),
        )
        self.buffer.clear()
        self.buffer_bytes = 2

    def scanned(self, definitions):
        self.complete = True
        self.definitions = definitions

    def finish(self, result):
        if not self.enabled or not self.complete or result.get("status") != "ok":
            return
        try:
            if self.rows != result["total"]:
                return
            self._flush()
            encoded = json.dumps(
                {
                    "schema": SCHEMA,
                    "key": self.key,
                    "base": {k: v for k, v in result.items() if k not in PAGE_FIELDS},
                    "definitions": self.definitions,
                },
                separators=(",", ":"),
            )
            if len(encoded.encode()) > self.limit:
                return
            self.db.execute("INSERT INTO metadata VALUES (?)", (encoded,))
            self.db.commit()
            self.close()
            receipt = json.dumps(
                {
                    "schema": SCHEMA,
                    "key": self.key,
                    "size": self.path.stat().st_size,
                    "sha256": checksum(self.path),
                },
                separators=(",", ":"),
            )
            if len(receipt.encode()) * 2 > RECEIPT_BYTES:
                return
            pending = self.path.with_name("complete.partial")
            pending.write_text(receipt, encoding="utf-8")
            os.replace(pending, self.path.with_name("complete.json"))
        except (OSError, sqlite3.Error, KeyError, TypeError, ValueError):
            self.close()

    def close(self):
        self.enabled = False
        self.buffer.clear()
        self.buffer_bytes = 2
        if self.db is not None:
            with suppress(sqlite3.Error):
                self.db.close()
            self.db = None
