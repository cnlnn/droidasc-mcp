"""Bounded literal const-string use-site scans, without decompilation or an index."""

import struct

from .native_dex import InvalidDex, dex_entries, page_result
from .native_scan import class_selector, scanner, select_directory
from .worker_errors import DroidAscError


def string_mask(dex, needle, sensitive, *, accelerator=True):
    count, offset, _ = dex.tables[0]
    mask = bytearray((count + 7) // 8)
    deferred = range(count)
    if accelerator and needle.isascii():
        try:
            from ._dexscan import matching_strings
        except ImportError:
            pass
        else:
            try:
                selected, deferred = matching_strings(
                    dex.data, offset, count, needle.encode("ascii"), True, sensitive
                )
            except ValueError as exc:
                raise InvalidDex(str(exc)) from exc
            for index in selected:
                mask[index >> 3] |= 1 << (index & 7)
    if not sensitive:
        needle = needle.lower()
    for index in deferred:
        text = dex.string(index)
        if needle in (text if sensitive else text.lower()):
            mask[index >> 3] |= 1 << (index & 7)
    return bytes(mask)


def query_strings(settings, bundle, query, *, emit=None):
    try:
        return page_result(_strings(settings, bundle, query, emit=emit), query, settings)
    except (InvalidDex, struct.error, UnicodeError) as exc:
        raise DroidAscError("Invalid DEX string instruction scan: " + str(exc)) from exc


def _strings(settings, bundle, query, *, emit=None):
    needle = query["value"]
    sensitive = query.get("case_sensitive", True)
    offset, limit = query.get("offset", 0), min(query.get("limit", 100), settings.max_page_size)
    items, total = [], 0
    methods = instructions = without_code = 0
    for entry, dex in dex_entries(bundle):
        mask = string_mask(dex, needle, sensitive)
        scan = scanner(dex, mask, 2, True)
        select = class_selector(dex, mask, 2, "all")
        if select is not None:
            directory, _, count, decoded, _, without = select_directory(dex, select)
            methods += count
            instructions += decoded
            without_code += without
        else:
            directory = dex.classes()
        for _, cls in directory:
            definitions = cls if select is not None else dex.raw_members(cls)[1]
            for method_index, _, code in dex.ordered_methods(definitions):
                if select is None:
                    methods += 1
                    without_code += not code
                    method = dex.item(4, method_index)
                    dex.item(0, dex.u32(method + 4))
                    dex.item(2, dex.u16(method + 2))
                if not code:
                    continue
                caller = None
                for position, address, op, decoded in scan(code):
                    if select is None:
                        instructions += decoded
                    if op not in {0x1A, 0x1B}:
                        continue
                    index = dex.u16(position + 2) if op == 0x1A else dex.u32(position + 2)
                    dex.item(0, index)
                    if not mask[index >> 3] & (1 << (index & 7)):
                        continue
                    on_page = offset <= total < offset + limit
                    if on_page or (emit is not None and emit.enabled):
                        if caller is None:
                            caller = dex.method(method_index)
                        row = {
                            "caller": caller,
                            "dex_entry": entry,
                            "string_index": index,
                            "value": dex.string(index),
                            "instruction_offset": address,
                            "offset_unit": "code_units_from_method_start",
                            "opcode": "const-string" if op == 0x1A else "const-string/jumbo",
                        }
                        if emit is not None:
                            emit(row)
                        if on_page:
                            items.append(row)
                    total += 1
    if emit is not None:
        emit.scanned({})
    return {
        "status": "ok",
        "backend": "native-dex-string-instructions",
        "backend_version": "1",
        "items": items,
        "total": total,
        "reference_semantics": "const_string_operand",
        "match_semantics": ("case_sensitive" if sensitive else "case_insensitive")
        + "_literal_substring_of_string_value",
        "scan_scope": "supplied_dex_methods",
        "scanned_methods": methods,
        "scanned_instructions": instructions,
        "methods_without_code": without_code,
        "scan_errors": 0,
        "instruction_scan_complete": True,
        "runtime_target_resolution": "not_performed",
        "limitations": ["encoded_initial_values", "reflection", "jni", "runtime_loaded_code"],
    }
