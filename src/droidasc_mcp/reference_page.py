"""Byte-bounded reference prefixes with exact continuation offsets."""

import json

from .worker_errors import response_limit

OPERATIONS = {"find_method_refs", "find_field_refs", "get_method_calls", "search_refs"}


def _size(value):
    return len(json.dumps(value).encode())


def reference_page(result, maximum, *, check=lambda: None):
    if result.get("status") != "ok" or not {"offset", "limit", "items", "total"} <= result.keys():
        return result
    # The supervised worker writes one trailing newline to stdout.
    maximum = min(256 * 1024, maximum) - 1
    check()
    offset, items, total = result["offset"], result["items"], result["total"]
    if not items and offset < total:
        return response_limit()
    limited = offset + len(items) < total and len(items) < result["limit"]
    if limited:
        result = {
            **result,
            "page_limited_by": "response_bytes",
            "response_byte_limit": maximum,
        }
    result_size = _size(result)
    if result_size <= maximum:
        return result
    if "query_cache" in result:
        without_cache = {k: v for k, v in result.items() if k != "query_cache"}
        # There are other required fields: removing the cache field removes its
        # key/value and one comma+space, exactly the singleton object's size.
        cache_size = _size({"query_cache": result["query_cache"]})
        if result_size - cache_size <= maximum:
            return without_cache
    base = {
        **result,
        "items": [],
        "has_more": True,
        "truncated": True,
        "next_offset": offset + 1,
        "page_limited_by": "response_bytes",
        "response_byte_limit": maximum,
    }
    header = _size(base) - len(str(offset + 1))
    used, count = 0, 0
    for index, row in enumerate(items, 1):
        check()
        used += _size(row) + (2 if index > 1 else 0)
        if header + used + len(str(offset + index)) > maximum:
            break
        count = index
    check()
    if not count:
        return response_limit()
    return {**base, "items": items[:count], "next_offset": offset + count}
