"""ASC source-token links, paged in source lines with code-point span provenance."""

import hashlib
import zipfile
from contextlib import redirect_stdout

from .worker_errors import DroidAscError


def query_source_metadata(settings, bundle, entry, query):
    from droidasc.asc_client.asc_handler import AscHandler

    from .dex_worker import BoundedText

    with zipfile.ZipFile(bundle) as archive:
        data = archive.read(entry)
    with BoundedText(65536) as logs, redirect_stdout(logs):
        source, references = AscHandler().getclass_with_metadata(data, query["class_name"])
    if len(source.encode()) > settings.max_output_bytes:
        raise DroidAscError("Decompiled metadata source exceeds configured stream limit")
    lines = source.splitlines(keepends=True)
    offset, limit = query["offset"], min(query["limit"], settings.max_page_size)
    start = sum(map(len, lines[:offset]))
    shown = "".join(lines[offset : offset + limit])
    end = start + len(shown)
    fields = ("start", "end", "kind", "declaring_class", "name", "descriptor", "declaration")
    items = [dict(zip(fields, row, strict=True)) for row in references if start <= row[0] < end]
    more = offset + limit < len(lines)
    return {
        "status": "ok",
        "backend": "droidasc-source-metadata",
        "class_name": query["class_name"],
        "dex_entry": entry,
        "source": shown,
        "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "source_start": start,
        "source_end": end,
        "span_unit": "unicode_code_points",
        "member_references": items,
        "reference_semantics": "decompiler_token_links_not_instruction_xrefs",
        "total": len(lines),
        "offset": offset,
        "limit": limit,
        "has_more": more,
        "truncated": more,
        "next_offset": offset + limit if more else None,
    }
