"""Session-private ownership directory with bounded cache and exact UTF-16 ordering."""

import re
import sqlite3
from functools import wraps
from itertools import islice
from json.encoder import encode_basestring_ascii

from .archive_errors import ArchiveError


def checked(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except sqlite3.Error as exc:
            self.failed = True
            if "database or disk is full" in str(exc):
                raise ArchiveError(
                    "metadata_limit", "Prepared DEX metadata exceeds budget"
                ) from exc
            raise ArchiveError("invalid_query", "Invalid prepared class directory") from exc

    return call


SUPPLEMENTARY = re.compile(r"[\U00010000-\U0010ffff]")


def surrogate_pair(match):
    value = ord(match[0]) - 0x10000
    return chr(0xD800 + (value >> 10)) + chr(0xDC00 + (value & 1023))


def key(name):
    # Internal CESU-8 keys retain UTF-16 code-unit ordering, including lone
    # surrogates, without doubling the dominant ASCII class/package names.
    if name.isascii():
        return name.encode("ascii")
    return SUPPLEMENTARY.sub(surrogate_pair, name).encode("utf-8", "surrogatepass")


def decode_key(value):
    text = value.decode("utf-8", "surrogatepass")
    if text.isascii():
        return text
    return text.encode("utf-16-be", "surrogatepass").decode("utf-16-be", "surrogatepass")


class ClassDirectory:
    def __init__(self, path, *, budget=None):
        self.path, self.budget, self.connection = path, budget, None
        self.metadata_bytes, self.rows, self.failed = 2, 0, False
        self.entries = set()
        self.key, self.decode_key = key, decode_key

    @checked
    def __enter__(self):
        try:
            self.connection = sqlite3.connect(
                self.path.as_uri() + ("?mode=ro" if self.budget is None else "?mode=rwc"), uri=True
            )
            self.connection.execute("PRAGMA cache_size=-512")
            self.connection.execute("PRAGMA temp_store=FILE")
            if self.budget is not None:
                if self.budget < 2:
                    raise ArchiveError("metadata_limit", "Prepared DEX metadata exceeds budget")
                # Unpublished, disposable session data: no WAL or rollback copies.
                self.connection.execute("PRAGMA journal_mode=OFF")
                self.connection.execute("PRAGMA synchronous=OFF")
                self.connection.execute("PRAGMA page_size=4096")
                self.connection.execute("PRAGMA user_version=1")
                # Account logical JSON-equivalent metadata separately from SQLite's
                # fixed pages/UTF-16 storage. Both fit the existing disk reservation.
                self.connection.execute(f"PRAGMA max_page_count={(2 * self.budget + 8192) // 4096}")
                self.connection.execute(
                    "CREATE TABLE classes(name BLOB PRIMARY KEY, entry TEXT NOT NULL) WITHOUT ROWID"
                )
            else:
                version = self.connection.execute("PRAGMA user_version").fetchone()[0]
                if version == 0:
                    self.key = lambda name: name.encode("utf-16-be", "surrogatepass")
                    self.decode_key = lambda value: value.decode("utf-16-be", "surrogatepass")
                elif version != 1:
                    raise ArchiveError("invalid_query", "Unsupported prepared class directory")
                self.connection.execute("SELECT name,entry FROM classes LIMIT 0")
            return self
        except BaseException:
            if self.connection is not None:
                self.connection.close()
            raise

    @checked
    def __exit__(self, typ, value, traceback):
        try:
            if typ is None and self.budget is not None and not self.failed:
                self.connection.commit()
        finally:
            self.connection.close()

    @checked
    def add(self, names, entry):
        if entry in self.entries:
            raise ArchiveError("invalid_query", "Class directory entry was already inserted")
        self.entries.add(entry)
        before = self.connection.total_changes
        records = ((self.key(name), entry) for name in names)
        # Stay below SQLite's oldest supported 999-variable limit and bound
        # transient allocations; avoid one Python/SQLite transition per class.
        while batch := list(islice(records, 128)):
            self.connection.execute(
                "INSERT OR IGNORE INTO classes VALUES" + ",".join(["(?,?)"] * len(batch)),
                [value for row in batch for value in row],
            )
        added = self.connection.total_changes - before
        new_names = (
            names if added == len(names) else [name for name in names if self[name] == entry]
        )
        self.metadata_bytes += sum(len(encode_basestring_ascii(name)) for name in new_names)
        self.metadata_bytes += added * (len(encode_basestring_ascii(entry)) + 4)
        if not self.rows and added:
            self.metadata_bytes -= 2
        self.rows += added
        if self.metadata_bytes > self.budget:
            self.failed = True
            raise ArchiveError("metadata_limit", "Prepared DEX metadata exceeds budget")
        if added == len(names):
            return []
        duplicates = []
        for name in names:
            previous = self[name]
            if previous != entry:
                duplicates.append({"class_name": name, "dex_entries": [previous, entry]})
                if len(duplicates) == 20:
                    break
        return duplicates

    @checked
    def __len__(self):
        return self.connection.execute("SELECT count(*) FROM classes").fetchone()[0]

    @checked
    def __getitem__(self, name):
        row = self.connection.execute(
            "SELECT entry FROM classes WHERE name=?", (self.key(name),)
        ).fetchone()
        if row is None:
            raise KeyError(name)
        return row[0]

    def __contains__(self, name):
        if name is None:
            return False
        try:
            self[name]
        except KeyError:
            return False
        return True

    @checked
    def page(self, prefix, offset, limit):
        lower = self.key(prefix or "")
        upper = bytearray(lower)
        while upper and upper[-1] == 255:
            upper.pop()
        if upper:
            upper[-1] += 1
            where, values = "name>=? AND name<?", (lower, bytes(upper))
        else:
            where, values = "name>=?", (lower,)
        total = self.connection.execute(
            "SELECT count(*) FROM classes WHERE " + where, values
        ).fetchone()[0]
        if offset >= total:
            return total, []
        rows = self.connection.execute(
            "SELECT name,entry FROM classes WHERE " + where + " ORDER BY name LIMIT ? OFFSET ?",
            (*values, min(limit, total), offset),
        )
        return total, [
            {"class_name": self.decode_key(name), "dex_entry": entry} for name, entry in rows
        ]
