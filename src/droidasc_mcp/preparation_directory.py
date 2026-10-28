"""Bounded ownership writes overlapped with subsequent DEX snapshot validation."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress

from .archive_errors import ArchiveError
from .class_directory import ClassDirectory
from .native_dex import InvalidDex
from .native_directory import class_names


class PreparationDirectory:
    def __init__(self, root, budget):
        self.root, self.budget = root, budget
        self.pending, self.owners = None, None
        self.duplicates = []

    def _open(self):
        self.owners = ClassDirectory(self.root / "owners.pending.sqlite", budget=self.budget)
        self.owners.__enter__()

    def __enter__(self):
        self.worker = ThreadPoolExecutor(max_workers=1, thread_name_prefix="droidasc-owners")
        try:
            self.worker.submit(self._open).result()
        except BaseException:
            self.worker.shutdown(wait=True)
            raise
        return self

    def _add(self, names, entry):
        self.duplicates.extend(self.owners.add(names, entry)[: max(0, 20 - len(self.duplicates))])

    def accept(self, archive, record):
        # The previous insertion already overlapped copying this member. Join it
        # before allocating the next names/set, keeping only one DEX directory live.
        if self.pending is not None:
            self.pending.result()
        # All native mappings end before returning to the snapshot writer. Only
        # owned class strings reach the background SQLite writer, including on Windows.
        archive.fp.flush()
        try:
            names = class_names(
                self.root / "analysis.apk",
                archive.getinfo(record.get("snapshot_entry", record["dex_entry"])),
                header_offset=record.get("logical_header_offset", 0),
            )
        except InvalidDex as exc:
            raise ArchiveError("invalid_dex", str(exc)) from exc
        record["class_count"] = len(names)
        if len(names) != record["declared_class_count"]:
            raise ArchiveError(
                "class_count_mismatch",
                f"Engine class count differs from DEX header: {record['path']}",
            )
        self.pending = self.worker.submit(self._add, names, record["dex_entry"])

    def _close(self, typ, value, traceback):
        result = None
        try:
            if typ is None:
                result = len(self.owners), self.duplicates, self.owners.metadata_bytes
        finally:
            self.owners.__exit__(typ, value, traceback)
        return result

    def __exit__(self, typ, value, traceback):
        try:
            if typ is not None:
                # Preserve the original snapshot/hash error, but join all writes
                # and close SQLite on its owning thread before session cleanup.
                if self.pending is not None:
                    with suppress(BaseException):
                        self.pending.result()
                self.worker.submit(self._close, typ, value, traceback).result()
                return
            try:
                if self.pending is not None:
                    self.pending.result()
            except BaseException as exc:
                self.worker.submit(self._close, type(exc), exc, exc.__traceback__).result()
                raise
            self.result = self.worker.submit(self._close, None, None, None).result()
            # The outer source hash and every member have now been validated.
            (self.root / "owners.pending.sqlite").replace(self.root / "owners.sqlite")
        finally:
            self.worker.shutdown(wait=True)
