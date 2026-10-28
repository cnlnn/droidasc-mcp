"""Strict DEX 041 container validation and supervised logical-file normalization."""

import hashlib
import os
import shutil
import struct
import zlib

from .archive_errors import ArchiveError as DexInputError
from .worker_errors import DroidAscError


def logical_offsets(data, *, integrity=False):
    """Checked upstream logical-offset traversal, retaining physical addresses."""
    offsets, cursor = [], 0
    while cursor < len(data):
        if len(offsets) >= 64:
            raise DexInputError("dex_count_limit", "Select at most 64 logical DEX files")
        header = data[cursor : cursor + 120]
        if len(header) != 120 or bytes(header[:8]) != b"dex\n041\0":
            raise DexInputError("invalid_dex_container", "Incomplete DEX 041 logical header")
        size, header_size, endian = struct.unpack_from("<III", header, 32)
        container_size, header_offset = struct.unpack_from("<II", header, 112)
        if (
            header_size != 120
            or endian != 0x12345678
            or container_size != len(data)
            or header_offset != cursor
            or size < 120
            or size % 4
            or cursor + size > len(data)
        ):
            raise DexInputError("invalid_dex_container", "Inconsistent DEX 041 container bounds")
        for start, width in ((56, 4), (64, 4), (72, 12), (80, 8), (88, 8), (96, 32)):
            count, offset = struct.unpack_from("<II", header, start)
            if (count and (offset < 120 or offset % 4 or offset + count * width > len(data))) or (
                not count and offset
            ):
                raise DexInputError("invalid_table", "DEX 041 ID table is outside container bounds")
        if integrity:
            with memoryview(data)[cursor : cursor + size] as logical:
                if (
                    hashlib.sha1(logical[32:]).digest() != header[12:32]
                    or zlib.adler32(logical[12:]) != struct.unpack_from("<I", header, 8)[0]
                ):
                    raise DexInputError(
                        "integrity_mismatch", "DEX 041 logical checksum/signature mismatch"
                    )
        offsets.append(cursor)
        cursor += size
    if not offsets:
        raise DexInputError("invalid_dex_container", "Incomplete DEX 041 logical header")
    return offsets


def read_container(settings, source):
    from .dex_worker import _identity

    before = source.stat()
    if before.st_size > settings.max_apk_bytes:
        raise DexInputError("input_limit", "DEX container exceeds the input byte limit")
    with source.open("rb") as stream:
        if stream.read(8) != b"dex\n041\0":
            return None
        stream.seek(0)
        data = stream.read(before.st_size + 1)
    if len(data) != before.st_size or _identity(before) != _identity(source.stat()):
        raise DexInputError("input_changed", "DEX container changed during import")
    offsets = logical_offsets(data, integrity=True)
    return data, offsets


def expand(settings, source, workspace, *, selected_offsets=None, library_home=None):
    container = read_container(settings, source)
    if container is None:
        return [(source, None)]
    data, offsets = container
    if selected_offsets is not None:
        if not selected_offsets or any(offset not in offsets for offset in selected_offsets):
            raise DexInputError(
                "invalid_dex_container", "Invalid logical DEX normalization selector"
            )
        offsets = selected_offsets
    digest = hashlib.sha256(data).hexdigest()
    snapshot = workspace / "container.dex"
    snapshot.write_bytes(data)
    from .method_backend import _execute_java

    paths = []
    normalized_bytes = 0
    normalization_budget = min(settings.max_apk_bytes, len(data) * 2)
    for number, offset in enumerate(offsets):
        job = workspace / f"logical-{number}"
        job.mkdir()
        target = job / "normalized.dex"
        java = settings.java_executable or shutil.which("java")
        home = library_home or settings.dexlib_home
        jars = sorted((home / "lib").glob("*.jar")) if home else []
        if not java or not jars:
            raise DexInputError(
                "backend_unavailable",
                "DEX 041 requires standalone dexlib2 "
                "and Java 17+: configure DROIDASC_MCP_DEXLIB_HOME; JADX is not used",
            )
        from pathlib import Path

        temporary = job / "jvm"
        temporary.mkdir()
        command = [
            str(java),
            "-Xmx512m",
            "-Xss512k",
            "-XX:+UseSerialGC",
            "-XX:CompressedClassSpaceSize=64m",
            "-XX:ReservedCodeCacheSize=64m",
            "-XX:-CreateCoredumpOnCrash",
            f"-XX:ErrorFile={os.devnull}",
            f"-Djava.io.tmpdir={temporary}",
            f"-Duser.home={temporary}",
            "-Dfile.encoding=UTF-8",
            "--class-path",
            os.pathsep.join(map(str, jars)),
            str(Path(__file__).with_name("DexContainerBridge.java")),
        ]
        result = _execute_java(
            settings,
            command
            + [
                str(snapshot),
                str(offset),
                str(target),
                str(normalization_budget - normalized_bytes),
            ],
            job,
            0,
            1,
        )
        if result["status"] != "ok" or not target.is_file():
            raise DroidAscError("Could not normalize logical DEX 041")
        normalized_bytes += target.stat().st_size
        if normalized_bytes > normalization_budget:
            raise DexInputError("input_limit", "Normalized logical DEX files exceed the byte limit")
        paths.append(
            (
                target,
                {
                    "original_dex_version": "041",
                    "container_sha256": digest,
                    "container_size_bytes": len(data),
                    "logical_header_offset": offset,
                    "normalization": "dexlib2_reencoded_standalone_040",
                },
            )
        )
    return paths
