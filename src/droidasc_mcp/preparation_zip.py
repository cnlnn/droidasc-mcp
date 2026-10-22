"""Streaming central-directory inventory for DEX preparation, not resource browsing.

Member decompression, local-header matching and CRC checking stay in stdlib zipfile.
Only code/container ZipInfos are retained; every other name still participates in
the same safety, duplicate, inventory and next-local-header checks.
"""

from __future__ import annotations

import bisect
import struct
import zipfile
from itertools import pairwise
from zlib import crc32

from .archive_errors import ArchiveError
from .archive_worker import MAX_ENTRIES, validate_entry

_HEADER = struct.Struct(zipfile.structCentralDir)
_KEEP = (".dex", ".class", ".jar", ".apk")
# Security fixes were backported at different patch versions. Detect capabilities,
# not Python minor versions; no zipfile module/class is monkeypatched.
_EXTRA_CRC = zipfile.ZipInfo._decodeExtra.__code__.co_argcount > 1
_ZIP64_LOCATION = "_ECD_LOCATION" in zipfile._EndRecData64.__code__.co_names


class PreparationZipFile(zipfile.ZipFile):
    """Read-only preparation adapter; ``inventory`` includes omitted resource names.

    The isolated _RealGetContents override is the only custom directory path. Public
    ZipFile.open(ZipInfo) and ZipExtFile retain the standard member-reader behavior.
    infolist/getinfo intentionally expose only the code/container members retained here.
    Resource operations must continue using a normal ZipFile.
    """

    def __init__(self, handle):
        self.inventory = {}
        super().__init__(handle, "r")

    def _RealGetContents(self):
        source = self.fp
        try:
            end = zipfile._EndRecData(source)
        except OSError as exc:
            raise zipfile.BadZipFile("File is not a zip file") from exc
        if not end:
            raise zipfile.BadZipFile("File is not a zip file")
        size = end[zipfile._ECD_SIZE]
        offset = end[zipfile._ECD_OFFSET]
        concat = end[zipfile._ECD_LOCATION] - size - offset
        if end[zipfile._ECD_SIGNATURE] == zipfile.stringEndArchive64 and not _ZIP64_LOCATION:
            concat -= zipfile.sizeEndCentDir64 + zipfile.sizeEndCentDir64Locator
        self._comment = end[zipfile._ECD_COMMENT]
        self.start_dir = offset + concat
        if self.start_dir < 0:
            raise zipfile.BadZipFile("Bad offset for central directory")
        source.seek(self.start_dir)
        consumed, local_offsets = 0, []
        while consumed < size:
            if len(self.inventory) >= MAX_ENTRIES:
                raise ArchiveError("entry_limit", "Archive has too many entries")
            if size - consumed < _HEADER.size:
                raise zipfile.BadZipFile("Truncated central directory")
            raw = source.read(_HEADER.size)
            if len(raw) != _HEADER.size:
                raise zipfile.BadZipFile("Truncated central directory")
            row = _HEADER.unpack(raw)
            if row[0] != zipfile.stringCentralDir:
                raise zipfile.BadZipFile("Bad magic number for central directory")
            name_size, extra_size, comment_size = row[12:15]
            variable_size = name_size + extra_size + comment_size
            consumed += _HEADER.size + variable_size
            if consumed > size:
                raise zipfile.BadZipFile("Central directory member exceeds directory bounds")
            raw = source.read(variable_size)
            if len(raw) != variable_size:
                raise zipfile.BadZipFile("Truncated central directory member")
            name = raw[:name_size]
            encoding = "utf-8" if row[5] & 0x800 else "cp437"
            info = zipfile.ZipInfo(name.decode(encoding))
            info.extra = raw[name_size : name_size + extra_size]
            info.comment = raw[name_size + extra_size :]
            info.header_offset = row[18]
            (
                info.create_version,
                info.create_system,
                info.extract_version,
                info.reserved,
                info.flag_bits,
                info.compress_type,
                time,
                date,
                info.CRC,
                info.compress_size,
                info.file_size,
            ) = row[1:12]
            if info.extract_version > zipfile.MAX_EXTRACT_VERSION:
                raise NotImplementedError(f"zip file version {info.extract_version / 10:.1f}")
            info.volume, info.internal_attr, info.external_attr = row[15:18]
            info._raw_time = time
            info.date_time = (
                (date >> 9) + 1980,
                (date >> 5) & 15,
                date & 31,
                time >> 11,
                (time >> 5) & 63,
                (time & 31) * 2,
            )
            if _EXTRA_CRC:
                info._decodeExtra(crc32(name))
            else:
                info._decodeExtra()
            validate_entry(info)
            if info.filename in self.inventory:
                raise ArchiveError("duplicate_entry", "Archive contains duplicate entry names")
            info.header_offset += concat
            if not 0 <= info.header_offset < self.start_dir:
                raise zipfile.BadZipFile("Local header is outside member bounds")
            local_offsets.append(info.header_offset)
            keep = info.filename.lower().endswith(_KEEP)
            self.inventory[info.filename] = info if keep else None
            if keep:
                self.filelist.append(info)
                self.NameToInfo[info.filename] = info
        local_offsets.sort()
        if any(left == right for left, right in pairwise(local_offsets)):
            raise zipfile.BadZipFile("Overlapped local headers")
        for info in self.filelist:
            position = bisect.bisect_right(local_offsets, info.header_offset)
            info._end_offset = (
                local_offsets[position] if position < len(local_offsets) else self.start_dir
            )
