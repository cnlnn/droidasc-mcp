"""ASC source-token links, paged in source lines with code-point span provenance."""

import hashlib
import zipfile
from contextlib import redirect_stdout, suppress

from .worker_errors import DroidAscError


def query_source_metadata(settings, bundle, entry, query, *, snapshot_root=None):
    from droidasc.asc_client.asc_handler import AscHandler

    from .dex_worker import BoundedText

    with zipfile.ZipFile(bundle) as archive:
        data = archive.read(entry)
    with BoundedText(65536) as logs, redirect_stdout(logs):
        source, references = AscHandler().getclass_with_metadata(data, query["class_name"])
    encoded = source.encode()
    if len(encoded) > settings.max_output_bytes:
        raise DroidAscError("Decompiled metadata source exceeds configured stream limit")
    lines = source.splitlines(keepends=True)
    offset, limit = query["offset"], min(query["limit"], settings.max_page_size)
    page = source_page(lines, references, offset=offset, limit=limit)
    if snapshot_root is not None:
        export_snapshot(snapshot_root, encoded, references, settings.max_output_bytes)
    return {
        "status": "ok",
        "backend": "droidasc-source-metadata",
        "class_name": query["class_name"],
        "dex_entry": entry,
        "source_sha256": hashlib.sha256(encoded).hexdigest(),
        "span_unit": "unicode_code_points",
        "reference_semantics": "decompiler_token_links_not_instruction_xrefs",
        **page,
    }


def source_page(lines, references, *, offset, limit):
    start = sum(map(len, lines[:offset]))
    shown = "".join(lines[offset : offset + limit])
    end = start + len(shown)
    fields = ("start", "end", "kind", "declaring_class", "name", "descriptor", "declaration")
    items = [dict(zip(fields, row, strict=True)) for row in references if start <= row[0] < end]
    more = offset + limit < len(lines)
    return {
        "source": shown,
        "source_start": start,
        "source_end": end,
        "member_references": items,
        "total": len(lines),
        "offset": offset,
        "limit": limit,
        "has_more": more,
        "truncated": more,
        "next_offset": offset + limit if more else None,
    }


def export_snapshot(root, source, references, budget):
    from .dex_worker import DexInputError, write_json_bounded

    partial = root / "source.partial"
    refs = root / "source-refs.partial"
    try:
        write_json_bounded(refs, references, budget - len(source))
        with partial.open("xb") as stream:
            stream.write(source)
        refs.replace(root / "source-refs.json")
        partial.replace(root / "source.txt")
    except (DexInputError, OSError):
        for path in (partial, refs, root / "source.txt", root / "source-refs.json"):
            with suppress(OSError):
                path.unlink()
