"""Original standalone DEX bytes through the bounded entry workflow."""

import os

from .archive_errors import ArchiveError
from .archive_worker import KINDS, _content_options, _content_page, _page_bounds, page, safe_name


def query_entry(handle, name, query, max_page_size):
    operation = query["operation"]
    if operation in {"manifest_summary", "manifest_xml", "signing_inventory", "artifact_inventory"}:
        return {"status": "not_applicable", "code": "unsupported_capability"}
    if operation not in {"list_entries", "read_entry"}:
        raise ArchiveError("invalid_query", "Unknown entry operation")
    size = os.fstat(handle.fileno()).st_size
    entry = {
        "path": name,
        "kind": "dex",
        "size_bytes": size,
        "compressed_size_bytes": size,
        "encrypted": False,
        "abi": None,
    }
    common = {"format_validation": "not_performed"}
    if operation == "list_entries":
        offset, limit = _page_bounds(query, max_page_size)
        kind, prefix = query.get("kind"), query.get("prefix")
        if kind is not None and kind not in KINDS:
            raise ArchiveError("invalid_query", "Unknown entry kind")
        if prefix is not None and not isinstance(prefix, str):
            raise ArchiveError("invalid_query", "prefix must be a literal string")
        selected = kind in {None, "dex"} and (prefix is None or name.startswith(prefix))
        return {"status": "ok", **common, **page([entry] if selected else [], offset, limit)}
    requested = query.get("entry_path")
    if not isinstance(requested, str):
        raise ArchiveError("invalid_query", "entry_path is required")
    safe_name(requested)
    if requested != name:
        return {"status": "not_applicable", "code": "entry_not_found", "entry_path": requested}
    max_bytes, offset, _ = _content_options(query)
    handle.seek(min(offset, size))
    data = handle.read(max_bytes + 1)
    if len(data) != min(max_bytes + 1, max(0, size - offset)):
        raise ArchiveError("input_changed", "DEX changed during entry read; retry")
    return {
        **common,
        **entry,
        "decoded": False,
        "decoding_status": "not_applicable",
        **_content_page(data[:max_bytes], offset, len(data) > max_bytes),
    }
