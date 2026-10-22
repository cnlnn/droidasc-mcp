"""Stable sorted pages with bounded memory, including deep offsets."""

import heapq
import json
import sqlite3
import tempfile
from pathlib import Path

from .worker_errors import DroidAscError


class ReverseKey:
    def __init__(self, key):
        self.key = key

    def __lt__(self, other):
        return self.key > other.key

    def __eq__(self, other):
        return isinstance(other, ReverseKey) and self.key == other.key


class SortedPage:
    def __init__(self, settings, offset, limit, workspace=None):
        self.offset, self.limit = offset, limit
        self.capacity = offset + limit
        self.total = self.used = 0
        self.heap = []
        self.budget = settings.max_output_bytes
        self.directory = None
        self.connection = None
        if self.capacity > 4096:
            self.directory = tempfile.TemporaryDirectory(prefix="droidasc-page-", dir=workspace)
            try:
                self.connection = sqlite3.connect(Path(self.directory.name) / "page.sqlite")
                self.connection.execute("PRAGMA journal_mode=OFF")
                self.connection.execute("PRAGMA cache_size=-2048")
                self.connection.execute("PRAGMA temp_store=FILE")
                self.connection.execute(
                    f"PRAGMA max_page_count={max(1, settings.max_xref_index_bytes // 4096)}"
                )
                self.connection.execute(
                    "CREATE TABLE rows(a BLOB,b BLOB,c INTEGER,n INTEGER,payload TEXT)"
                )
            except BaseException:
                self.close()
                raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        if self.connection:
            self.connection.close()
        if self.directory:
            self.directory.cleanup()

    def add(self, key, row):
        serial = self.total
        self.total += 1
        if self.connection:
            try:
                self.connection.execute(
                    "INSERT INTO rows VALUES(?,?,?,?,?)", (*key, serial, json.dumps(row))
                )
            except sqlite3.Error as exc:
                raise DroidAscError("Sorted query exceeds its temporary disk budget") from exc
            return
        if len(self.heap) == self.capacity and key >= self.heap[0][0].key:
            return
        size = len(json.dumps(row))
        value = (ReverseKey(key), -serial, size, row)
        if len(self.heap) == self.capacity:
            self.used -= heapq.heapreplace(self.heap, value)[2]
        else:
            heapq.heappush(self.heap, value)
        self.used += size
        if self.used > self.budget:
            raise DroidAscError("Sorted query page exceeds the configured output byte limit")

    def items(self):
        if self.offset >= self.total:
            return []
        if self.connection:
            try:
                return [
                    json.loads(row[0])
                    for row in self.connection.execute(
                        "SELECT payload FROM rows ORDER BY a,b,c,n LIMIT ? OFFSET ?",
                        (self.limit, self.offset),
                    )
                ]
            except sqlite3.Error as exc:
                raise DroidAscError("Could not page the bounded query spool") from exc
        ordered = sorted(self.heap, key=lambda item: (item[0].key, -item[1]))
        return [item[3] for item in ordered[self.offset : self.capacity]]
