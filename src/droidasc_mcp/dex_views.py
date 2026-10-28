"""Private ZIP logical views over one original physical DEX container."""

import hashlib
import re
import struct
import zipfile

from .archive_errors import ArchiveError
from .native_dex import InvalidDex

VIEW_FIELD = 0xDA41
ENTRY_NAME = re.compile(r"classes(?:[2-9]|[1-5][0-9]|6[0-4])?\.dex")


def view_extra(entry, header_offset):
    if not ENTRY_NAME.fullmatch(entry) or type(header_offset) is not int or header_offset < 0:
        raise InvalidDex("Invalid private logical DEX view")
    payload = struct.pack("<BI", 1, header_offset) + entry.encode("ascii")
    return struct.pack("<HH", VIEW_FIELD, len(payload)) + payload


def view_selector(info):
    position, selected = 0, None
    extra = info.extra
    while position < len(extra):
        if len(extra) - position < 4:
            raise InvalidDex("Truncated private DEX snapshot extra field")
        kind, size = struct.unpack_from("<HH", extra, position)
        position += 4
        end = position + size
        if end > len(extra):
            raise InvalidDex("Truncated private DEX snapshot extra field")
        if kind == VIEW_FIELD:
            if selected is not None or size < 6 or extra[position] != 1:
                raise InvalidDex("Invalid private logical DEX view")
            header = struct.unpack_from("<I", extra, position + 1)[0]
            try:
                entry = extra[position + 5 : end].decode("ascii")
            except UnicodeError as exc:
                raise InvalidDex("Invalid private logical DEX backing entry") from exc
            if not ENTRY_NAME.fullmatch(entry):
                raise InvalidDex("Invalid private logical DEX backing entry")
            selected = entry, header
        position = end
    return selected


def resolve_view(archive, info):
    selector = view_selector(info)
    if selector is None:
        return info, 0
    entry, header = selector
    if entry == info.filename:
        if header != 0 or info.file_size < 120:
            raise InvalidDex("Invalid physical DEX snapshot entry")
        return info, 0
    if info.file_size or not header:
        raise InvalidDex("Logical DEX aliases require an empty entry and a later header")
    # Validate the alias's local header as well as the actual backing member.
    with archive.open(info):
        pass
    try:
        backing = archive.getinfo(entry)
    except KeyError as exc:
        raise InvalidDex("Logical DEX backing entry is missing") from exc
    if view_selector(backing) != (entry, 0) or backing.file_size < 120:
        raise InvalidDex("Logical DEX views require one direct physical backing entry")
    return backing, header


def source_view(bundle, entry, workspace, budget, *, java_settings=None):
    """Upstream header-first source handoff, after reading a checked physical view."""
    from .native_snapshot import query_dex

    with zipfile.ZipFile(bundle) as archive:
        selected = archive.getinfo(entry)
        backing, header = resolve_view(archive, selected)
        if header == 0 and java_settings is None:
            return bundle, {}
        minimum = backing.file_size * (7 if java_settings is not None else 1) + 4096
        if type(budget) is not int or minimum > budget:
            raise ArchiveError(
                "session_capacity", "Source view exceeds reserved session disk space"
            )
        target = workspace / "source-view.apk"
        digest = hashlib.sha256()
        if java_settings is not None:
            from .dex_container import expand

            original = workspace / "source-original.dex"
            with archive.open(backing) as stream, original.open("wb") as output:
                while block := stream.read(256 * 1024):
                    output.write(block)
            normalization = workspace / "source-normalization"
            normalization.mkdir()
            normalized = expand(
                java_settings,
                original,
                normalization,
                selected_offsets=[header],
                library_home=java_settings.dexlib_home or java_settings.jadx_home,
            )[0][0]
            with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as output:
                output.write(normalized, entry)
            with normalized.open("rb") as stream:
                while block := stream.read(256 * 1024):
                    digest.update(block)
            if sum(path.stat().st_size for path in workspace.rglob("*") if path.is_file()) > budget:
                raise ArchiveError(
                    "session_capacity", "Source view exceeds reserved session disk space"
                )
            return target, {
                "source_view": {
                    "kind": "dexlib2_reencoded_standalone_040",
                    "dex_entry": entry,
                    "logical_header_offset": header,
                    "view_sha256": digest.hexdigest(),
                }
            }
        with (
            query_dex(bundle, archive, selected) as dex,
            memoryview(dex.data) as data,
            zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as output,
            output.open(entry, "w") as stream,
        ):
            # Copy only the selected header; every other physical address is retained.
            with data[header : header + 120] as block:
                stream.write(block)
                digest.update(block)
            for start in range(120, len(data), 256 * 1024):
                with data[start : start + 256 * 1024] as block:
                    stream.write(block)
                    digest.update(block)
        if target.stat().st_size > budget:
            raise ArchiveError(
                "session_capacity", "Source view exceeds reserved session disk space"
            )
    return target, {
        "source_view": {
            "kind": "selected_header_at_zero_physical_offsets",
            "dex_entry": entry,
            "logical_header_offset": header,
            "view_sha256": digest.hexdigest(),
        }
    }


def legacy_view(settings, bundle, workspace, budget):
    """Retain the pre-native public ASC reference adapter's standalone inputs."""
    from .dex_container import expand

    target = workspace / "legacy-view.apk"
    sources, total = [], 0
    with zipfile.ZipFile(bundle) as archive, zipfile.ZipFile(target, "w") as output:
        physical_size = sum(info.file_size for info in archive.infolist())
        if type(budget) is not int or physical_size * 7 + 4096 > budget:
            raise ArchiveError(
                "session_capacity", "Reference view exceeds reserved session disk space"
            )
        number = 0
        for info in archive.infolist():
            resolve_view(archive, info)
            selector = view_selector(info)
            if selector is not None and selector[0] != info.filename:
                continue
            job = workspace / f"legacy-{number}"
            job.mkdir()
            original = job / "original.dex"
            with archive.open(info) as stream, original.open("wb") as copied:
                while block := stream.read(256 * 1024):
                    copied.write(block)
            normalization = job / "normalized"
            normalization.mkdir()
            for source, provenance in expand(settings, original, normalization):
                total += source.stat().st_size
                if total > settings.max_apk_bytes:
                    raise ArchiveError(
                        "input_limit", "Combined normalized DEX size exceeds configured size limit"
                    )
                number += 1
                entry = "classes.dex" if number == 1 else f"classes{number}.dex"
                output.write(source, entry)
                if provenance:
                    sources.append({"dex_entry": entry, **provenance})
        if sum(path.stat().st_size for path in workspace.rglob("*") if path.is_file()) > budget:
            raise ArchiveError(
                "session_capacity", "Reference view exceeds reserved session disk space"
            )
    return target, {
        "compatibility_view": {
            "kind": "standalone_040_legacy_asc",
            "requires_java": True,
            "sources": sources,
        }
    }
