import mmap
import struct
import zlib


_U16_FROM = struct.Struct("<H").unpack_from
_U32_FROM = struct.Struct("<I").unpack_from
_CD_SIG = b"PK\x01\x02"
_LH_SIG = b"PK\x03\x04"
_EOCD_SIG = b"PK\x05\x06"
_DEX_SUFFIX = b".dex"
_SLASH = ord("/")
_DEFLATE_CHUNK = 1 << 19


def _find_eocd(mm : mmap.mmap) -> int:
    # EOCD can only be followed by a 65535-byte ZIP comment and its 22-byte
    # fixed header, so searching the whole APK is unnecessary.
    search_start = max(0, len(mm) - 65536 - 22)
    return mm.rfind(_EOCD_SIG, search_start)


def _parse_cd_dex_entries(mm : mmap.mmap):
    eocd_idx = _find_eocd(mm)
    if eocd_idx < 0:
        raise ValueError("EOCD not found")

    cd_size = _U32_FROM(mm, eocd_idx + 12)[0]
    cd_off = _U32_FROM(mm, eocd_idx + 16)[0]
    cd_end = cd_off + cd_size
    entries = []
    seen_names = set()
    pos = cd_off

    # APKs normally name DEX files classes*.dex. Searching those bytes avoids
    # walking every resource entry in a large central directory.
    while True:
        pos = mm.find(b"classes", pos, cd_end)
        if pos < 0:
            break
        header_off = pos - 46
        pos += 7
        if header_off < cd_off or mm[header_off:header_off + 4] != _CD_SIG:
            continue

        name_len = _U16_FROM(mm, header_off + 28)[0]
        name_start = pos - 7
        name_end = name_start + name_len
        if name_end > cd_end:
            continue

        name_bytes = mm[name_start:name_end]
        if (
            not name_bytes.endswith(_DEX_SUFFIX)
            or _SLASH in name_bytes
            or name_bytes in seen_names
        ):
            continue

        seen_names.add(name_bytes)
        # name, uncompressed size, compressed size, local-header offset,
        # compression method. Keep this tuple compact: it crosses processes.
        entries.append((
            name_bytes.decode("utf-8", errors="ignore"),
            _U32_FROM(mm, header_off + 24)[0],
            _U32_FROM(mm, header_off + 20)[0],
            _U32_FROM(mm, header_off + 42)[0],
            _U16_FROM(mm, header_off + 10)[0],
        ))

    if entries:
        return entries

    # Fall back to a complete central-directory walk for valid but unusual ZIP
    # layouts where the name search cannot recover an entry header.
    ptr = cd_off
    while ptr + 46 <= cd_end:
        if mm[ptr:ptr + 4] != _CD_SIG:
            break

        name_len = _U16_FROM(mm, ptr + 28)[0]
        extra_len = _U16_FROM(mm, ptr + 30)[0]
        comment_len = _U16_FROM(mm, ptr + 32)[0]
        name_start = ptr + 46
        name_end = name_start + name_len
        name_bytes = mm[name_start:name_end]
        if name_bytes.endswith(_DEX_SUFFIX) and _SLASH not in name_bytes:
            entries.append((
                name_bytes.decode("utf-8", errors="ignore"),
                _U32_FROM(mm, ptr + 24)[0],
                _U32_FROM(mm, ptr + 20)[0],
                _U32_FROM(mm, ptr + 42)[0],
                _U16_FROM(mm, ptr + 10)[0],
            ))

        ptr = name_end + extra_len + comment_len

    return entries


def _inflate_deflate_chunks(comp_view, stop_event):
    if stop_event is None:
        # A single call is about 4% faster when cancellation is unnecessary.
        return zlib.decompress(comp_view, -15)
    decomp = zlib.decompressobj(-15)
    out = bytearray()
    pos = 0
    total = len(comp_view)
    while pos < total:
        if stop_event.is_set():
            return None
        end = min(pos + _DEFLATE_CHUNK, total)
        out.extend(decomp.decompress(comp_view[pos:end]))
        pos = end
    out.extend(decomp.flush())
    if stop_event.is_set():
        return None
    return bytes(out)


def _inflate_dex_prefix(mm : mmap.mmap, entry, prefix_need, stop_event = None):
    """Inflate only the prefix required by ``prefix_need``.

    Returns ``(data, complete)``. ``complete`` is true for stored entries;
    ``None`` means the caller should fall back to the existing full inflate
    path because the prefix is not safe or no longer worth streaming.
    """
    _name, uncomp_size, comp_size, local_header_off, comp_method = entry
    if mm[local_header_off:local_header_off + 4] != _LH_SIG:
        raise ValueError("bad local header signature")

    name_len = _U16_FROM(mm, local_header_off + 26)[0]
    extra_len = _U16_FROM(mm, local_header_off + 28)[0]
    data_off = local_header_off + 30 + name_len + extra_len
    comp_view = memoryview(mm)[data_off:data_off + comp_size]

    if comp_method == 0:
        return bytes(comp_view), True
    if comp_method != 8:
        raise ValueError(f"unsupported compression method: {comp_method}")

    decomp = zlib.decompressobj(-15)
    out = bytearray()
    compressed_pos = 0
    pending = b""
    while True:
        if stop_event is not None and stop_event.is_set():
            return None
        try:
            target = min(int(prefix_need(out, uncomp_size)), uncomp_size)
        except (IndexError, TypeError, ValueError, struct.error):
            return None
        if target >= uncomp_size:
            return None
        if len(out) >= target:
            return bytes(out), False

        if pending:
            chunk = pending
            pending = b""
        else:
            if compressed_pos >= len(comp_view):
                # The stream ended before the requested prefix. Let the
                # existing full path perform its normal size/error handling.
                return None
            end = min(compressed_pos + _DEFLATE_CHUNK, len(comp_view))
            chunk = comp_view[compressed_pos:end]
            compressed_pos = end

        max_output = max(1, target - len(out))
        produced = decomp.decompress(chunk, max_output)
        out.extend(produced)
        pending = decomp.unconsumed_tail
        if not produced and not pending and compressed_pos >= len(comp_view):
            return None


def _inflate_dex(mm : mmap.mmap, entry, stop_event = None):
    _name, uncomp_size, comp_size, local_header_off, comp_method = entry
    if mm[local_header_off:local_header_off + 4] != _LH_SIG:
        raise ValueError("bad local header signature")

    name_len = _U16_FROM(mm, local_header_off + 26)[0]
    extra_len = _U16_FROM(mm, local_header_off + 28)[0]
    # File data starts after the variable local filename and extra fields, not
    # at the corresponding central-directory record.
    data_off = local_header_off + 30 + name_len + extra_len
    comp_view = memoryview(mm)[data_off:data_off + comp_size]

    if comp_method == 0:
        data = bytes(comp_view)
    elif comp_method == 8:
        data = _inflate_deflate_chunks(comp_view, stop_event)
        if data is None:
            return None
    else:
        raise ValueError(f"unsupported compression method: {comp_method}")

    if uncomp_size and len(data) != uncomp_size:
        raise ValueError(f"size mismatch: expect {uncomp_size}, got {len(data)}")
    return data
