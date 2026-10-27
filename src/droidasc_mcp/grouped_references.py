"""Collect caller groups from bounded reference chunks or fallback worker pages."""

import json
from time import monotonic

from .reference_cursor import ReferenceCursor
from .reference_groups import ReferenceGroups
from .reference_spool import PAGE_FIELDS
from .runner import _check_cancelled
from .worker_errors import DroidAscError, response_limit


def grouped_reference_page(settings, key, secret, query, execute, identity):
    deadline = monotonic() + settings.timeout_seconds

    def check():
        _check_cancelled()
        if monotonic() >= deadline:
            raise DroidAscError("Grouped reference collection timed out")

    query = dict(query)
    cursor = query.pop("cursor", None)
    query.pop("reference_format")
    codec = ReferenceCursor(secret, query, identity)
    try:
        offset = codec.decode(cursor) if cursor is not None else 0
    except ValueError as exc:
        return {"status": "error", "code": "invalid_cursor", "message": str(exc)}
    maximum = min(256 * 1024, settings.max_output_bytes) - 1
    limit = min(query.get("limit", 200), settings.max_page_size)
    page = ReferenceGroups()
    base, header, expected, position = None, None, None, offset
    while True:
        check()
        result = execute({**query, "offset": position, "limit": settings.max_page_size})
        if result.get("status") != "ok":
            return result
        metadata = {k: v for k, v in result.items() if k not in PAGE_FIELDS}
        if base is None:
            expected = metadata
            base = {
                **metadata,
                "session_id": key,
                "reference_format": "grouped",
                "limit_unit": "caller_groups",
                "total_unit": "reference_sites",
                "offset": offset,
                "limit": limit,
                "response_byte_limit": maximum,
            }
            header = (
                len(
                    json.dumps(
                        {
                            **base,
                            "groups": [],
                            "returned_sites": 0,
                            "has_more": True,
                            "truncated": True,
                            "next_offset": 0,
                            "next_cursor": "",
                            "page_limited_by": "response_bytes",
                        }
                    ).encode()
                )
                - 2
            )
        elif metadata != expected:
            return {
                "status": "error",
                "code": "reference_changed",
                "message": "Reference metadata changed during collection",
            }
        total = base["total"]
        rows = result["items"]
        if (
            result["offset"] != position
            or position + len(rows) > total
            or not rows
            and position < total
        ):
            return {
                "status": "error",
                "code": "reference_changed",
                "message": "Reference page does not match its continuation",
            }
        for row in rows:
            check()
            end, count = position + 1, page.sites + 1
            overhead = header + len(str(count)) - 1
            if end < total:
                overhead += len(str(end)) - 1 + codec.size(end)
            else:
                overhead += 7 - len(', "page_limited_by": "response_bytes"')
            if not page.offer(row, maximum - overhead, limit):
                break
            position = end
        if page.limited_by or position >= total:
            break
    if not page.sites and offset < total:
        return response_limit()
    more = position < total
    response = {
        **base,
        "groups": page.finish(),
        "returned_sites": page.sites,
        "has_more": more,
        "truncated": more,
        "next_offset": position if more else None,
        "next_cursor": codec.encode(position) if more else None,
    }
    if more:
        response["page_limited_by"] = page.limited_by
    return response if len(json.dumps(response).encode()) <= maximum else response_limit()
