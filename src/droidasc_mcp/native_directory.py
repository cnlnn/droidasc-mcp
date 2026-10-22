"""Read class identities from immutable stored snapshots with bounded mapping windows."""

import os
import struct
import zipfile
from contextlib import suppress

from .native_dex import InvalidDex, decode_mutf8


def read_at(stream, base, size, offset, count):
    if offset < 0 or count < 0 or offset + count > size:
        raise InvalidDex("DEX directory read exceeds snapshot bounds")
    stream.seek(base + offset)
    data = stream.read(count)
    if len(data) != count:
        raise InvalidDex("Truncated DEX snapshot directory")
    return data


def deferred_name(stream, base, size, header, cls):
    def u32(offset):
        return struct.unpack("<I", read_at(stream, base, size, offset, 4))[0]

    type_table, string_table = (
        struct.unpack_from("<I", header, 68)[0],
        struct.unpack_from("<I", header, 60)[0],
    )
    string = u32(type_table + u32(cls) * 4)
    offset = u32(string_table + string * 4)
    length = 0
    for shift in range(0, 35, 7):
        value = read_at(stream, base, size, offset, 1)[0]
        offset += 1
        if shift == 28 and value > 15:
            raise InvalidDex("Invalid DEX string uleb128")
        length |= (value & 127) << shift
        if value < 128:
            break
    else:
        raise InvalidDex("Unterminated DEX string uleb128")
    raw = bytearray()
    while offset < size:
        block = read_at(stream, base, size, offset, min(512, size - offset))
        end = block.find(b"\0")
        raw.extend(block if end < 0 else block[:end])
        # Every valid MUTF8 code unit occupies at most three bytes.
        if len(raw) > length * 3:
            raise InvalidDex("Invalid DEX modified UTF-8 length")
        if end >= 0:
            return decode_mutf8(bytes(raw), length)
        offset += len(block)
    raise InvalidDex("Unterminated DEX string")


def stored_member_offset(stream, info):
    if (
        info.compress_type != zipfile.ZIP_STORED
        or info.flag_bits & 1
        or info.compress_size != info.file_size
    ):
        raise InvalidDex("Class directory requires an unencrypted stored snapshot")
    stream.seek(info.header_offset)
    local = stream.read(30)
    if len(local) != 30 or local[:4] != b"PK\x03\x04":
        raise InvalidDex("Invalid stored DEX local header")
    flags, method = struct.unpack_from("<HH", local, 6)
    different_flags = flags ^ info.flag_bits
    # Recent zipfile backports keep UTF-8 in live ZipInfo but clear it on the
    # wire for ASCII names. Every other flag must still agree exactly.
    if (
        different_flags and not (different_flags == 0x800 and info.filename.isascii())
    ) or method != info.compress_type:
        raise InvalidDex("Stored DEX local header disagrees with its inventory")
    name_size, extra_size = struct.unpack_from("<HH", local, 26)
    try:
        expected_name = info.filename.encode("utf-8" if flags & 0x800 else "cp437")
    except UnicodeEncodeError as exc:
        raise InvalidDex("Stored DEX local header has an invalid filename encoding") from exc
    if stream.read(name_size) != expected_name:
        raise InvalidDex("Stored DEX local header filename disagrees with its inventory")
    return info.header_offset + 30 + name_size + extra_size


def class_names(bundle, info, *, accelerator=True):
    """Read one closed member, including before the enclosing ZIP is finalized.

    The caller must flush the writer first. No view/handle survives this call,
    so Windows can grow the snapshot safely after these identities are returned.
    """
    native = None
    checked = False
    if accelerator:
        with suppress(ImportError):
            from . import _dexscan

            checked = hasattr(_dexscan, "mapped_checked_classes")
            native = _dexscan.mapped_checked_classes if checked else _dexscan.mapped_classes
    with bundle.open("rb") as stream:
        handle = stream.fileno()
        if os.name == "nt":
            import msvcrt

            handle = msvcrt.get_osfhandle(handle)
        base = stored_member_offset(stream, info)
        header = read_at(stream, base, info.file_size, 0, 112)
        if native is None:
            from .native_dex import Dex

            data = read_at(stream, base, info.file_size, 0, info.file_size)
            import zlib

            if zlib.crc32(data) != info.CRC:
                raise InvalidDex("Stored DEX snapshot CRC mismatch")
            dex = Dex(data)
            try:
                return [name for name, _ in dex.classes(accelerator=False, ordered=False)]
            finally:
                dex.close()
        seen = set()
        try:
            names = native(handle, base, info.file_size, info.CRC)
        except ValueError as exc:
            raise InvalidDex(str(exc)) from exc
        if checked:
            names, deferred, seen = names
        else:
            deferred = range(len(names))
        for index in deferred:
            name = names[index]
            if isinstance(name, int):
                name = deferred_name(stream, base, info.file_size, header, name)
                names[index] = name
            if name in seen:
                raise InvalidDex("Duplicate class definition")
            seen.add(name)
        return names


def class_entries(bundle, *, accelerator=True):
    with zipfile.ZipFile(bundle) as archive:
        for info in sorted(archive.infolist(), key=lambda row: row.filename):
            if not info.filename.endswith(".dex"):
                continue
            yield info.filename, class_names(bundle, info, accelerator=accelerator)
