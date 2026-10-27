"""Checked explicit type operands without a whole-artifact relationship index."""

import struct

from .native_dex import TYPE_OPS, InvalidDex, dex_entries, page_result
from .native_scan import scanner
from .worker_errors import DroidAscError


def query_types(settings, bundle, query, *, emit=None):
    try:
        return page_result(_types(settings, bundle, query, emit=emit), query, settings)
    except (InvalidDex, struct.error, UnicodeError) as exc:
        raise DroidAscError("Invalid DEX type instruction scan: " + str(exc)) from exc


def _types(settings, bundle, query, *, emit=None):
    needle = query["type_descriptor"]
    match = query.get("type_match", "exact")
    offset, limit = query.get("offset", 0), min(query.get("limit", 100), settings.max_page_size)
    items, total = [], 0
    methods = instructions = without_code = 0
    for entry, dex in dex_entries(bundle):
        targets = set()
        if dex.tables[1][0] > 65536:
            raise InvalidDex("DEX type pool exceeds 16-bit index range")
        for index in range(dex.tables[1][0]):
            descriptor = dex.type(index)
            if descriptor == needle if match == "exact" else needle in descriptor:
                targets.add(index)
        scan = scanner(dex, targets, 3, True)
        for _, cls in dex.classes():
            for method_index, _, code in dex.ordered_methods(dex.raw_members(cls)[1]):
                methods += 1
                without_code += not code
                # Resolve declaration metadata even when no operand matches this method.
                method = dex.item(4, method_index)
                dex.item(0, dex.u32(method + 4))
                dex.item(2, dex.u16(method + 2))
                caller = None
                for position, address, op, decoded in scan(code) if code else ():
                    instructions += decoded
                    if op not in TYPE_OPS:
                        continue
                    index = dex.u16(position + 2)
                    descriptor = dex.type(index)
                    if index not in targets:
                        continue
                    on_page = offset <= total < offset + limit
                    if on_page or (emit is not None and emit.enabled):
                        if caller is None:
                            caller = dex.method(method_index)
                        row = {
                            "caller": caller,
                            "dex_entry": entry,
                            "type_descriptor": descriptor,
                            "instruction_offset": address,
                            "offset_unit": "code_units_from_method_start",
                            "opcode": TYPE_OPS[op],
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
        "backend": "native-dex-type-instructions",
        "backend_version": "1",
        "items": items,
        "total": total,
        "type_descriptor": needle,
        "type_relation": "operand",
        "type_match": match,
        "reference_semantics": "explicit_type_operand",
        "match_semantics": "case_sensitive_" + match + "_of_type_descriptor",
        "scan_scope": "supplied_dex_methods",
        "scanned_methods": methods,
        "scanned_instructions": instructions,
        "methods_without_code": without_code,
        "scan_errors": 0,
        "instruction_scan_complete": True,
        "runtime_target_resolution": "not_performed",
        "limitations": [
            "member_type_relations",
            "catch_types",
            "declarations",
            "annotations",
            "reflection",
            "jni",
            "runtime_loaded_code",
        ],
    }
