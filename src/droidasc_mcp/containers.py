"""Capability routing and budgeted DEX snapshots from Android/JAR containers."""

from __future__ import annotations

import io
import os
import re
import stat
import zipfile
from contextlib import ExitStack, contextmanager

from .archive_errors import ArchiveError
from .archive_worker import _digest, _entries, _identity, _read, page


def validate_budget(value, settings):
    if type(value) is not int or not 1 <= value <= settings.max_apk_bytes:
        raise ValueError("max_uncompressed_bytes must be positive and within the input byte limit")
    return value


@contextmanager
def stable_archive(path, maximum, *, preparation=False):
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ArchiveError("input_changed", "Container is no longer a regular file")
        if before.st_size > maximum:
            raise ArchiveError("input_limit", "Container exceeds the input byte budget")
        digest = _digest(handle)
        from .preparation_zip import PreparationZipFile

        archive_type = PreparationZipFile if preparation else zipfile.ZipFile
        with archive_type(handle) as archive:
            entries = archive.inventory if preparation else _entries(archive)
            yield archive, entries, digest
        with path.open("rb") as current:
            if (
                _identity(before) != _identity(os.fstat(handle.fileno()))
                or _identity(before) != _identity(os.fstat(current.fileno()))
                or digest != _digest(handle)
            ):
                raise ArchiveError("input_changed", "Container changed during analysis; retry")
            # Reopen after hashing: Windows path-stat timestamps can differ from fstat.
            with path.open("rb") as final:
                if any(
                    _identity(before) != _identity(os.fstat(stream.fileno()))
                    for stream in (handle, current, final)
                ):
                    raise ArchiveError("input_changed", "Container changed during analysis; retry")


def select(entries, kind, module):
    if module is not None and (kind != "aab" or not re.fullmatch(r"[A-Za-z0-9_.-]+", module)):
        raise ArchiveError("invalid_query", "module selects one exact AAB module name")
    if kind == "aab":
        chosen = module or "base"
        return sorted(
            name
            for name in entries
            if name.startswith(chosen + "/dex/")
            and name.lower().endswith(".dex")
            and not entries[name].is_dir()
        )
    return sorted(
        name for name in entries if name.lower().endswith(".dex") and not entries[name].is_dir()
    )


def capabilities(archive, entries, kind, module, budget, *, preparation=False):
    selected = select(entries, kind, module)
    active = {
        name: (archive, entries[name])
        for name in entries
        if name.lower().endswith((".dex", ".class"))
    }
    nested = ExitStack()
    nested_cost = 0
    nested_names = set()
    try:
        for jar_name in sorted(name for name in entries if name.lower().endswith(".jar")):
            info = entries[jar_name]
            if info.is_dir():
                continue
            if info.file_size > min(64 * 1024**2, budget - nested_cost):
                raise ArchiveError("container_limit", "Nested JAR exceeds expansion budget")
            raw, complete = _read(archive, info, budget - nested_cost)
            if not complete:
                raise ArchiveError("invalid_archive", "Nested JAR is incomplete")
            nested_cost += len(raw)
            from .preparation_zip import PreparationZipFile

            archive_type = PreparationZipFile if preparation else zipfile.ZipFile
            inner = nested.enter_context(archive_type(io.BytesIO(raw)))
            inner_entries = inner.inventory if preparation else _entries(inner)
            prefix = jar_name + "!/"
            names = {prefix + name for name in inner_entries}
            if any(name in entries or name in nested_names for name in names):
                raise ArchiveError(
                    "ambiguous_entry", "Nested provenance collides with an entry name"
                )
            if kind == "aar" and jar_name == "classes.jar":
                selected += [prefix + name for name in select(inner_entries, "jar", None)]
            nested_names.update(names)
            active.update(
                {
                    prefix + name: (inner, inner_entries[name])
                    for name in inner_entries
                    if name.lower().endswith((".dex", ".class"))
                }
            )
            if len(entries) + len(nested_names) > 100_000:
                raise ArchiveError("entry_limit", "Combined archive inventory exceeds entry budget")
    except BaseException:
        nested.close()
        raise
    selected.sort()
    classes = sorted(
        name for name in active if name.lower().endswith(".class") and not active[name][1].is_dir()
    )
    splits = sorted(name for name in entries if name.lower().endswith(".apk"))
    modules = (
        sorted(
            {
                name.split("/")[0]
                for name in entries
                if re.fullmatch(r"[^/]+/dex/.+", name) and name.lower().endswith(".dex")
            }
        )
        if kind == "aab"
        else []
    )
    metadata = {
        "artifact_kind": kind,
        "selected_module": (module or "base") if kind == "aab" else None,
        "modules": modules,
        "dex_entries": selected,
        "jvm_class_count": len(classes),
        "nested_apk_count": len(splits),
        "dex_analysis": bool(selected),
        "jvm_decompilation": False,
        "split_reconstruction": False,
        "coverage": "selected_aab_module_direct_dex"
        if kind == "aab"
        else "selected_direct_dex_only",
    }
    rows = (
        [
            {"kind": "dex", "path": name, "size_bytes": active[name][1].file_size}
            for name in selected
        ]
        + [
            {
                "kind": "jvm_class",
                "path": name,
                "size_bytes": active[name][1].file_size,
                "class_name": "L" + name.rsplit("!/", 1)[-1][:-6] + ";",
            }
            for name in classes
        ]
        + [
            {"kind": "nested_apk", "path": name, "size_bytes": entries[name].file_size}
            for name in splits
        ]
    )
    return (
        metadata,
        sorted(rows, key=lambda row: row["path"]),
        nested,
        active,
        selected,
        nested_cost,
    )


def inspect(archive, entries, kind, query):
    budget = query.get("max_uncompressed_bytes", 128 * 1024**2)
    if type(budget) is not int or not 1 <= budget <= 2 * 1024**3:
        raise ArchiveError("invalid_query", "Expansion budget must be within 1 byte and 2 GiB")
    if type(query.get("include_summary", False)) is not bool:
        raise ArchiveError("invalid_query", "include_summary must be a boolean")
    metadata, rows, nested, _, _, used = capabilities(
        archive, entries, kind, query.get("module"), budget
    )
    try:
        inventory = rows
        if query.get("class_query") is not None or query.get("class_prefix") is not None:
            inventory = [
                row
                for row in rows
                if row["kind"] == "jvm_class"
                and (query.get("class_query") or "").lower() in row["class_name"].lower()
                and row["class_name"].startswith(query.get("class_prefix") or "")
            ]
        result = {
            "status": "ok",
            **metadata,
            **page(inventory, query.get("offset", 0), query.get("limit", 100)),
        }
        if query.get("include_summary", False):
            from .artifact_summary import summarize

            result["summary"] = summarize(
                archive, entries, kind, metadata["selected_module"], budget - used
            )
        if query.get("compare_to"):
            from pathlib import Path

            with stable_archive(Path(query["compare_to"]), query["max_input_bytes"]) as (
                other,
                other_entries,
                digest,
            ):
                other_metadata, other_rows, other_nested, _, _, _ = capabilities(
                    other,
                    other_entries,
                    Path(query["compare_to"]).suffix.lower()[1:],
                    query.get("module"),
                    budget,
                )
                try:
                    old = {row["class_name"] for row in rows if row["kind"] == "jvm_class"}
                    new = {row["class_name"] for row in other_rows if row["kind"] == "jvm_class"}
                    differences = sorted(
                        [{"class_name": name, "change": "added"} for name in new - old]
                        + [{"class_name": name, "change": "removed"} for name in old - new],
                        key=lambda row: row["class_name"],
                    )
                    result.update(
                        comparison="jvm_class_identities_only",
                        behavior_comparison="not_performed",
                        new_artifact_sha256=digest,
                        new_artifact_path=query["compare_to"],
                        counts={
                            "added": len(new - old),
                            "removed": len(old - new),
                            "common": len(old & new),
                        },
                        dex_comparison_required=metadata["dex_analysis"]
                        or other_metadata["dex_analysis"],
                        **page(differences, query.get("offset", 0), query.get("limit", 100)),
                    )
                finally:
                    other_nested.close()
        return result
    finally:
        if nested is not None:
            nested.close()


@contextmanager
def selected_dex(settings, path, budget, module):
    kind = path.suffix.lower()[1:]
    with stable_archive(path, settings.max_apk_bytes, preparation=True) as (
        archive,
        entries,
        digest,
    ):
        metadata, _, nested, active, selected, used = capabilities(
            archive, entries, kind, module, budget, preparation=True
        )
        try:
            if not selected:
                raise ArchiveError(
                    "no_analyzable_dex",
                    "Container has no selected direct DEX; inspect artifact capabilities",
                )
            if len(selected) > 64:
                raise ArchiveError("dex_count_limit", "Select at most 64 DEX entries")
            if used + sum(active[name][1].file_size for name in selected) > budget:
                raise ArchiveError(
                    "container_limit", "Nested and DEX bytes exceed expansion budget"
                )

            for name in selected:
                _, info = active[name]
                if info.flag_bits & 1 or info.is_dir():
                    raise ArchiveError(
                        "invalid_entry", "DEX entry must be an unencrypted regular file"
                    )
            metadata = {**metadata, "artifact_path": str(path), "artifact_sha256": digest}
            # Full names already passed safety, duplicate, nested-collision and
            # inventory-limit checks. Member readers only need retained ZipInfos;
            # release resource names before DEX buffers/class directories grow.
            entries.clear()
            yield ((active[name][0], active[name][1], name) for name in selected), metadata
        finally:
            if nested is not None:
                nested.close()


@contextmanager
def snapshot_stream(settings, path, root, budget, module):
    from concurrent.futures import ThreadPoolExecutor

    with selected_dex(settings, path, budget, module) as (inputs, metadata):

        def extract(item):
            index, (reader, info, name) = item
            target = root / f"import-{index}.dex"
            copied = 0
            with reader.open(info) as source, target.open("wb") as output:
                while block := source.read(min(256 * 1024, info.file_size - copied + 1)):
                    copied += len(block)
                    if copied > info.file_size:
                        raise ArchiveError("container_limit", "Expanded bytes exceed declared size")
                    output.write(block)
            if copied != info.file_size:
                raise ArchiveError("invalid_entry", "DEX entry size differs from its declaration")
            return target, name

        with ThreadPoolExecutor(max_workers=2) as workers:
            yield workers.map(extract, enumerate(inputs)), metadata


def snapshot(settings, path, root, budget, module):
    with snapshot_stream(settings, path, root, budget, module) as (stream, metadata):
        snapshots = list(stream)
    return (
        [target for target, _ in snapshots],
        [name for _, name in snapshots],
        metadata,
    )


@contextmanager
def prefetched(source, chunk_size=256 * 1024):
    """Overlap bounded ZIP decompression with hashing/copying, without raw files."""
    from queue import Full, Queue
    from threading import Event, Thread

    pending = Queue(maxsize=1)
    stopped = Event()

    def send(value):
        while not stopped.is_set():
            try:
                pending.put(value, timeout=0.05)
                return True
            except Full:
                continue
        return False

    def produce():
        try:
            while block := source.read(chunk_size):
                if not send(block):
                    return
            send(None)
        except BaseException as exc:
            send(exc)

    class Reader:
        name = source.name

        def __init__(self):
            self.block, self.position, self.finished = b"", 0, False

        def read(self, count):
            if not 0 < count <= 256 * 1024:
                raise ValueError("Prefetched reads must be positive and at most 256 KiB")
            if self.position == len(self.block):
                if self.finished:
                    return b""
                block = pending.get()
                if isinstance(block, BaseException):
                    raise block
                if block is None:
                    self.finished = True
                    return b""
                self.block, self.position = block, 0
            start = self.position
            self.position = min(start + count, len(self.block))
            # Short reads are legal: do not concatenate adjacent owned blocks just
            # to fill the request, or duplicate complete chunks on every transfer.
            return self.block[start : self.position]

    worker = Thread(target=produce, name="droidasc-dex-prefetch")
    worker.start()
    try:
        yield Reader()
    finally:
        stopped.set()
        worker.join()


@contextmanager
def prefetched_entries(inputs):
    from collections import deque

    pending = deque()
    inputs = iter(inputs)

    def advance():
        item = next(inputs, None)
        if item is None:
            return
        reader, info, name = item
        lifetime = ExitStack()
        try:
            source = lifetime.enter_context(reader.open(info))
            stream = lifetime.enter_context(prefetched(source, chunk_size=64 * 1024))
        except BaseException:
            lifetime.close()
            raise
        pending.append((stream, info, name, lifetime))

    def consume():
        while pending:
            stream, info, name, lifetime = pending[0]
            yield stream, info, name
            lifetime.close()
            pending.popleft()
            advance()

    try:
        advance()
        advance()
        yield consume()
    finally:
        for _, _, _, lifetime in pending:
            lifetime.close()
