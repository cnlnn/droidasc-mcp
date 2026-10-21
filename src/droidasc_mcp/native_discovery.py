"""Declaration/string discovery from DEX pools, without a decompiler process."""

from .native_dex import dex_entries, page_result, utf16_key
from .native_page import SortedPage


def query_discovery(settings, bundle, query, workspace=None):
    offset = query.get("offset", 0)
    limit = min(query.get("limit", 100), settings.max_page_size)
    with SortedPage(settings, offset, limit, workspace) as page:
        return _query_discovery(settings, bundle, query, page)


def _query_discovery(settings, bundle, query, page):
    operation = query["operation"]
    sensitive = query.get("case_sensitive", True)
    needle = query.get("value") or ""
    if not sensitive:
        needle = needle.lower()
    strings = operation == "search_strings"
    names = query.get("member_match") == "name"
    for entry, dex in dex_entries(bundle):
        if strings:
            for index in range(dex.tables[0][0]):
                value = dex.string(index)
                if needle in (value if sensitive else value.lower()):
                    page.add(
                        (utf16_key(entry), b"", index),
                        {"dex_entry": entry, "string_index": index, "value": value},
                    )
            continue
        for owner, cls in dex.classes():
            if query.get("class_name") and query["class_name"] != owner:
                continue
            if operation == "search_classes":
                if query.get("prefix") and not owner.startswith(query["prefix"]):
                    continue
                if needle in (owner if sensitive else owner.lower()):
                    page.add((utf16_key(owner), b"", 0), {"class_name": owner, "dex_entry": entry})
                continue
            fields, methods = dex.members(cls)
            for descriptor, flags, *_ in fields if query["kind"] == "field" else methods:
                name = descriptor.split("->", 1)[1].split(
                    ":" if query["kind"] == "field" else "(", 1
                )[0]
                matched = name if names else descriptor
                if needle not in (matched if sensitive else matched.lower()):
                    continue
                row = {"kind": query["kind"], "descriptor": descriptor, "dex_entry": entry}
                if names:
                    row.update(class_name=owner, name=name, access_flags=flags)
                page.add((utf16_key(owner), utf16_key(descriptor), 0), row)
    result = {
        "status": "ok",
        "backend": "native-dex-discovery",
        "backend_version": "1",
        "instruction_scan_complete": False,
        "scan_errors": 0,
        "runtime_target_resolution": "not_performed",
        "match_semantics": ("case_sensitive" if sensitive else "case_insensitive")
        + "_literal_substring_of_"
        + (
            "string_value"
            if strings
            else "class_descriptor"
            if operation == "search_classes"
            else "member_name"
            if names
            else "full_descriptor"
        ),
        "scope": "string_pool_in_supplied_files" if strings else "declarations_in_supplied_files",
        "total": page.total,
        "items": page.items(),
    }
    return page_result(result, query, settings)
