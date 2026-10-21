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
def stable_archive(path, maximum):
    with path.open("rb") as handle:
        before = os.fstat(handle.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ArchiveError("input_changed", "Container is no longer a regular file")
        if before.st_size > maximum:
            raise ArchiveError("input_limit", "Container exceeds the input byte budget")
        digest = _digest(handle)
        with zipfile.ZipFile(handle) as archive:
            yield archive, _entries(archive), digest
        with path.open("rb") as current:
            if (
                _identity(before) != _identity(os.fstat(handle.fileno()))
                or _identity(before) != _identity(os.fstat(current.fileno()))
                or digest != _digest(handle)
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


def capabilities(archive, entries, kind, module, budget):
    selected = select(entries, kind, module)
    active = {name: (archive, entries[name]) for name in entries}
    nested = ExitStack()
    nested_cost = 0
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
            inner = nested.enter_context(zipfile.ZipFile(io.BytesIO(raw)))
            inner_entries = _entries(inner)
            prefix = jar_name + "!/"
            if any(prefix + name in active for name in inner_entries):
                raise ArchiveError(
                    "ambiguous_entry", "Nested provenance collides with an entry name"
                )
            if kind == "aar" and jar_name == "classes.jar":
                selected += [prefix + name for name in select(inner_entries, "jar", None)]
            active.update({prefix + name: (inner, info) for name, info in inner_entries.items()})
            if len(active) > 100_000:
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
    metadata, rows, nested, _, _, _ = capabilities(
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


def snapshot(settings, path, root, budget, module):
    paths, origins = [], []
    kind = path.suffix.lower()[1:]
    with stable_archive(path, settings.max_apk_bytes) as (archive, entries, digest):
        metadata, _, nested, active, selected, used = capabilities(
            archive, entries, kind, module, budget
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
            for index, name in enumerate(selected):
                reader, info = active[name]
                if info.flag_bits & 1 or info.is_dir():
                    raise ArchiveError(
                        "invalid_entry", "DEX entry must be an unencrypted regular file"
                    )
                target = root / f"import-{index}.dex"
                copied = 0
                with reader.open(info) as source, target.open("wb") as output:
                    while block := source.read(min(1024**2, budget - used + 1)):
                        used += len(block)
                        copied += len(block)
                        if used > budget or copied > info.file_size:
                            raise ArchiveError(
                                "container_limit", "Expanded bytes exceed declared budget"
                            )
                        output.write(block)
                if copied != info.file_size:
                    raise ArchiveError(
                        "invalid_entry", "DEX entry size differs from its declaration"
                    )
                paths.append(target)
                origins.append(name)
        finally:
            if nested is not None:
                nested.close()
    return paths, origins, {**metadata, "artifact_path": str(path), "artifact_sha256": digest}
