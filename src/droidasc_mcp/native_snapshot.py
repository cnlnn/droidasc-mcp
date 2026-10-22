"""Bounded read-only query windows over private immutable stored DEX members."""

import mmap
import os
import zipfile
import zlib
from contextlib import contextmanager, suppress

from .native_dex import Dex, InvalidDex
from .native_directory import stored_member_offset


@contextmanager
def query_dex(bundle, archive, info, *, mapped=True):
    native = False
    if mapped:
        with suppress(ImportError):
            from ._dexscan import buffer_inputs

            native = bool(buffer_inputs)
    if not native or info.compress_type != zipfile.ZIP_STORED:
        dex = Dex(archive.read(info))
        try:
            yield dex
        finally:
            dex.close()
        return
    # Retain zipfile's overlap, local-name and supported-feature checks before
    # mapping; the complete entry CRC is checked below without an owned copy.
    with archive.open(info):
        pass
    with bundle.open("rb") as stream:
        base = stored_member_offset(stream, info)
        size = info.file_size
        if size < 112 or base < 0 or base + size > os.fstat(stream.fileno()).st_size:
            raise InvalidDex("Invalid stored DEX snapshot range")
        aligned = base // mmap.ALLOCATIONGRANULARITY * mmap.ALLOCATIONGRANULARITY
        padding = base - aligned
        with (
            mmap.mmap(
                stream.fileno(), padding + size, access=mmap.ACCESS_READ, offset=aligned
            ) as region,
            memoryview(region)[padding:] as data,
        ):
            if zlib.crc32(data) != info.CRC:
                raise InvalidDex("Stored DEX snapshot CRC mismatch")

            def find(needle, start):
                position = region.find(needle, padding + start, padding + size)
                return position - padding if position >= 0 else -1

            dex = Dex(data, find=find)
            try:
                yield dex
            finally:
                dex.close()
