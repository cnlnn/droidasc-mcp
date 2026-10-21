"""Supervised, bounded APK inventory and resource reads without extraction."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import stat
import struct
import sys
import zipfile
from pathlib import Path

from .config import Settings

MAX_ENTRIES = 100_000
MAX_READ_BYTES = 128 * 1024
MAX_XML_BYTES = 4 * 1024 * 1024
MAX_RESPONSE_BYTES = 256 * 1024
KINDS = {"manifest", "resource", "asset", "native", "dex", "metadata", "other"}


class ArchiveError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class _DecoderWarnings(logging.Handler):
    def __init__(self):
        super().__init__(logging.WARNING)
        self.reported = False

    def emit(self, record):
        self.reported = True


def safe_name(name):
    parts = name.removesuffix("/").split("/")
    if (
        not name
        or "\\" in name
        or any(ord(char) < 32 for char in name)
        or any(part in {"", ".", ".."} for part in parts)
        or re.match(r"^[A-Za-z]:", name)
    ):
        raise ArchiveError("unsafe_entry", "Archive entry is not a safe relative ZIP path")
    return name


def entry_kind(name):
    if name == "AndroidManifest.xml":
        return "manifest"
    if name.startswith("assets/"):
        return "asset"
    if name.startswith("res/") or name == "resources.arsc":
        return "resource"
    if name.startswith("lib/") and name.endswith(".so") and len(name.split("/")) == 3:
        return "native"
    if re.fullmatch(r"classes(?:\d+)?\.dex", name):
        return "dex"
    return "metadata" if name.startswith("META-INF/") else "other"


def entry_row(info):
    kind = entry_kind(info.filename)
    return {
        "path": info.filename,
        "kind": kind,
        "size_bytes": info.file_size,
        "compressed_size_bytes": info.compress_size,
        "crc32": f"{info.CRC:08x}",
        "encrypted": bool(info.flag_bits & 1),
        "abi": info.filename.split("/")[1] if kind == "native" else None,
    }


def page(rows, offset, limit):
    items = rows[offset : offset + limit]
    more = offset + len(items) < len(rows)
    return {
        "items": items,
        "total": len(rows),
        "offset": offset,
        "limit": limit,
        "has_more": more,
        "next_offset": offset + len(items) if more else None,
    }


def _digest(handle):
    handle.seek(0)
    digest = hashlib.sha256()
    for block in iter(lambda: handle.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _entries(archive):
    infos = archive.infolist()
    if len(infos) > MAX_ENTRIES:
        raise ArchiveError("entry_limit", "Archive has too many entries")
    entries = {}
    for info in infos:
        safe_name(info.filename)
        if info.orig_filename != info.filename:
            raise ArchiveError("unsafe_entry", "Archive entry name contains a NUL byte")
        if info.filename in entries:
            raise ArchiveError("duplicate_entry", "Archive contains duplicate entry names")
        mode = stat.S_IFMT(info.external_attr >> 16)
        if mode not in {0, stat.S_IFREG, stat.S_IFDIR}:
            raise ArchiveError("special_entry", "Archive contains a non-regular entry")
        entries[info.filename] = info
    return entries


def _read(archive, info, budget):
    if info.is_dir():
        raise ArchiveError("entry_is_directory", "Select a file entry")
    if info.flag_bits & 1:
        raise ArchiveError("encrypted_entry", "Encrypted archive entries are unsupported")
    with archive.open(info) as stream:
        data = stream.read(budget + 1)
    complete = len(data) <= budget and len(data) == info.file_size
    return data[:budget], complete


def _check_binary_xml(data):
    """Check chunk bounds and balanced tag IDs before a repairing XML decoder runs."""
    offset, roots, stack = 8, 0, []
    while offset < len(data):
        if offset + 8 > len(data):
            raise ArchiveError("invalid_xml", "Binary XML has a truncated chunk header")
        kind, header, size = struct.unpack_from("<HHI", data, offset)
        if header < 8 or size < header or offset + size > len(data):
            raise ArchiveError("invalid_xml", "Binary XML chunk exceeds its document bounds")
        if kind in {0x0102, 0x0103}:
            minimum = 20 if kind == 0x0102 else 8
            if header != 16 or size < header + minimum:
                raise ArchiveError("invalid_xml", "Binary XML tag chunk is incomplete")
            tag = struct.unpack_from("<II", data, offset + header)
            if kind == 0x0102:
                if not stack:
                    roots += 1
                stack.append(tag)
                if len(stack) > 256:
                    raise ArchiveError("xml_limit", "Binary XML exceeds the nesting budget")
            elif not stack or stack.pop() != tag:
                raise ArchiveError("invalid_xml", "Binary XML closing tag does not match")
        offset += size
    if stack or roots != 1:
        raise ArchiveError("invalid_xml", "Binary XML has no single complete element tree")


def xml_document(data):
    """Decode complete Android binary XML or parse text XML with DTDs disabled."""
    from lxml import etree

    binary = data[:4] == b"\x03\x00\x08\x00"
    warnings = []
    if binary:
        if len(data) < 8 or int.from_bytes(data[4:8], "little") != len(data):
            raise ArchiveError("invalid_xml", "Binary XML length does not match the entry")
        _check_binary_xml(data)
        from axml.axml import AXMLPrinter
        from axml.utils.exceptions import NoDecoderFoundError, ResParserError

        logger, reported = logging.getLogger("axml"), _DecoderWarnings()
        logger.addHandler(reported)
        try:
            printer = AXMLPrinter(data)
            if not printer.is_valid():
                raise ArchiveError("invalid_xml", "Binary XML is malformed")
            if printer.is_packed():
                warnings.append("decoder_reported_packing_or_format_warning")
            data = printer.get_xml(pretty=False)
            if not isinstance(data, bytes):
                raise ArchiveError("invalid_xml", "Binary XML has no complete document")
        except (
            ValueError,
            IndexError,
            KeyError,
            TypeError,
            struct.error,
            ArithmeticError,
            AssertionError,
            NoDecoderFoundError,
            ResParserError,
        ) as exc:
            raise ArchiveError("invalid_xml", "Binary XML could not be decoded") from exc
        finally:
            logger.removeHandler(reported)
        if reported.reported:
            warnings.append("decoder_logged_warning_or_error")
    if len(data) > MAX_XML_BYTES:
        raise ArchiveError("xml_limit", "Decoded XML exceeds the byte budget")
    try:
        parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
        root = etree.fromstring(data, parser)
        if root.getroottree().docinfo.doctype:
            raise ArchiveError("invalid_xml", "DTD-bearing XML is unsupported")
        if sum(1 for _ in root.iter()) > 20_000:
            raise ArchiveError("xml_limit", "XML exceeds the node budget")
        return root, "android_binary_xml" if binary else "text_xml", warnings
    except etree.XMLSyntaxError as exc:
        raise ArchiveError("invalid_xml", "Entry is not well-formed XML") from exc


def _content(archive, info, query):
    max_bytes = query.get("max_bytes", 16 * 1024)
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_READ_BYTES:
        raise ArchiveError("invalid_query", "max_bytes must be between 1 and 131072")
    decode_xml = query.get("decode_xml", True)
    if type(decode_xml) is not bool:
        raise ArchiveError("invalid_query", "decode_xml must be a boolean")
    is_xml = info.filename.lower().endswith(".xml") and decode_xml
    # XML needs a complete bounded document; raw reads need only the requested prefix.
    budget = MAX_XML_BYTES if is_xml and info.file_size <= MAX_XML_BYTES else max_bytes
    data, complete = _read(archive, info, budget)
    result = {**entry_row(info), "crc_verified": complete, "decoded": False}
    if is_xml:
        if not complete or info.file_size > MAX_XML_BYTES:
            result["decoding_status"] = "input_limit"
        else:
            try:
                from lxml import etree

                root, xml_format, warnings = xml_document(data)
                decoded = etree.tostring(root, encoding="utf-8", pretty_print=True)
                if len(decoded) > MAX_XML_BYTES:
                    raise ArchiveError("xml_limit", "Serialized XML exceeds the byte budget")
                data = decoded
                result.update(
                    decoded=True,
                    decoding_status="ok_with_warnings" if warnings else "ok",
                    decoding_warnings=warnings,
                    xml_format=xml_format,
                )
            except ArchiveError as exc:
                result["decoding_status"] = exc.code
    else:
        result["decoding_status"] = "not_requested"
    truncated = not complete or len(data) > max_bytes
    data = data[:max_bytes]
    try:
        content, encoding = data.decode("utf-8"), "utf-8"
        # UTF-8 control bytes are binary data too, not useful MCP text.
        if any(ord(c) < 32 and c not in "\n\r\t" for c in content):
            raise UnicodeDecodeError("utf-8", data, 0, 1, "binary control byte")
    except UnicodeDecodeError:
        content, encoding = base64.b64encode(data).decode("ascii"), "base64"
    return {
        **result,
        "content": content,
        "encoding": encoding,
        "returned_bytes": len(data),
        "truncated": truncated,
        "content_complete": not truncated,
        "status": "partial" if truncated else "ok",
    }


def _query(archive, entries, query, max_page_size):
    operation = query["operation"]
    if operation not in {"list_entries", "read_entry", "manifest_summary"}:
        raise ArchiveError("invalid_query", "Unknown archive operation")
    if operation in {"list_entries", "manifest_summary"}:
        offset, limit = query.get("offset", 0), query.get("limit", 100)
        if type(offset) is not int or offset < 0 or type(limit) is not int:
            raise ArchiveError("invalid_query", "offset and limit must be integers")
        if not 1 <= limit <= max_page_size:
            raise ArchiveError("invalid_query", "limit exceeds the configured page budget")
    if operation == "list_entries":
        kind, prefix = query.get("kind"), query.get("prefix")
        if kind is not None and kind not in KINDS:
            raise ArchiveError("invalid_query", "Unknown APK entry kind")
        if prefix is not None and not isinstance(prefix, str):
            raise ArchiveError("invalid_query", "prefix must be a literal string")
        rows = [
            entry_row(info)
            for name, info in sorted(entries.items())
            if not info.is_dir()
            and (kind is None or entry_kind(name) == kind)
            and (prefix is None or name.startswith(prefix))
        ]
        return {"status": "ok", **page(rows, offset, limit)}
    name = "AndroidManifest.xml" if operation == "manifest_summary" else query.get("entry_path")
    if not isinstance(name, str):
        raise ArchiveError("invalid_query", "entry_path is required")
    safe_name(name)
    if name not in entries:
        return {"status": "not_applicable", "code": "entry_not_found", "entry_path": name}
    info = entries[name]
    if operation == "read_entry":
        return _content(archive, info, query)
    if operation == "manifest_summary":
        if info.file_size > MAX_XML_BYTES:
            raise ArchiveError("xml_limit", "Manifest exceeds the input byte budget")
        data, complete = _read(archive, info, MAX_XML_BYTES)
        if not complete:
            raise ArchiveError("invalid_xml", "Manifest entry is incomplete")
        root, xml_format, warnings = xml_document(data)
        from .manifest import summarize

        return {
            "status": "ok",
            "entry": entry_row(info),
            "xml_format": xml_format,
            "decoding_warnings": warnings,
            **summarize(root, offset, limit),
        }
    raise ArchiveError("invalid_query", "Unknown archive operation")


def analyze(request):
    try:
        settings = Settings(
            allowed_roots=tuple(Path(p) for p in request["allowed_roots"]),
            max_apk_bytes=request["max_input_bytes"],
        )
        apk = settings.validate_apk(request["apk_path"])
        with apk.open("rb") as handle:
            before = os.fstat(handle.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > request["max_input_bytes"]:
                raise ArchiveError("input_changed", "APK size or file type changed before analysis")
            source_hash = _digest(handle)
            with zipfile.ZipFile(handle) as archive:
                result = _query(
                    archive, _entries(archive), request["query"], request["max_page_size"]
                )
            # Windows stat(path) and fstat(fd) can expose different ctime semantics.
            # Reopen the path so both identity checks use the same handle-based API.
            with apk.open("rb") as current:
                if (
                    _identity(before) != _identity(os.fstat(handle.fileno()))
                    or _identity(before) != _identity(os.fstat(current.fileno()))
                    or source_hash != _digest(handle)
                ):
                    raise ArchiveError("input_changed", "APK changed during analysis; retry")
        return {
            "apk_path": str(apk),
            "apk_sha256": source_hash,
            "apk_size_bytes": before.st_size,
            **result,
        }
    except ArchiveError as exc:
        return {"status": "error", "code": exc.code, "message": str(exc)}
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError) as exc:
        return {"status": "error", "code": "invalid_archive", "message": str(exc)}


def main():
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    result = analyze(request)
    encoded = json.dumps(result)
    if len(encoded.encode()) > min(request["max_output_bytes"], MAX_RESPONSE_BYTES):
        encoded = json.dumps(
            {"status": "error", "code": "response_limit", "message": "Reduce limit or max_bytes"}
        )
    print(encoded)


if __name__ == "__main__":
    main()
