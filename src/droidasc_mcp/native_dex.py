"""Bounded, instruction-boundary DEX queries without a JVM or decompiler.

Layout and widths follow the Android DEX/bytecode specification. No private ASC
APIs are imported; ASC remains the disassembler. Only one DEX is resident.
"""

import re
import struct
import zipfile
from collections import Counter
from functools import lru_cache

from .worker_errors import DroidAscError

try:
    from ._dexscan import members as _native_members
except ImportError:
    _native_members = None


class InvalidDex(ValueError):
    pass


def utf16_key(text):
    return text.encode("utf-16-be", "surrogatepass")


def decode_mutf8(raw, length):
    raw = raw.replace(b"\xc0\x80", b"\0")
    try:
        text = raw.decode("utf-8", "surrogatepass")
        if len(text) == length and max(text, default="\0") < "\ud800":
            return text
        units = text.encode("utf-16-le", "surrogatepass")
        if len(units) != length * 2 or re.search(b"[\xf0-\xff]", raw):
            raise InvalidDex("Invalid DEX modified UTF-8 length")
        return units.decode("utf-16-le", "surrogatepass")
    except UnicodeError as exc:
        raise InvalidDex("Invalid DEX modified UTF-8") from exc


# Standard (not quickened/odex) opcode widths, in 16-bit code units.
WIDTHS = bytearray(256)
for start, stop, width in (
    (0x00, 0x12, 1),
    (0x12, 0x13, 1),
    (0x13, 0x18, 2),
    (0x18, 0x19, 5),
    (0x19, 0x1B, 2),
    (0x1B, 0x1C, 3),
    (0x1C, 0x1D, 2),
    (0x1D, 0x1F, 1),
    (0x1F, 0x21, 2),
    (0x21, 0x22, 1),
    (0x22, 0x24, 2),
    (0x24, 0x27, 3),
    (0x27, 0x29, 1),
    (0x29, 0x2A, 2),
    (0x2A, 0x2D, 3),
    (0x2D, 0x3E, 2),
    (0x44, 0x6E, 2),
    (0x6E, 0x73, 3),
    (0x74, 0x79, 3),
    (0x7B, 0x90, 1),
    (0x90, 0xB0, 2),
    (0xB0, 0xD0, 1),
    (0xD0, 0xE3, 2),
    (0xFA, 0xFC, 4),
    (0xFC, 0xFE, 3),
    (0xFE, 0x100, 2),
):
    WIDTHS[start:stop] = bytes([width]) * (stop - start)
for op, width in {2: 2, 3: 3, 5: 2, 6: 3, 8: 2, 9: 3, 0x14: 3, 0x17: 3}.items():
    WIDTHS[op] = width
WIDTHS = bytes(WIDTHS)
FIELD_NAMES = tuple(
    prefix + suffix
    for prefix in ("iget", "iput", "sget", "sput")
    for suffix in ("", "-wide", "-object", "-boolean", "-byte", "-char", "-short")
)
METHOD_NAMES = dict(
    enumerate(
        ("invoke-virtual", "invoke-super", "invoke-direct", "invoke-static", "invoke-interface"),
        0x6E,
    )
)
METHOD_NAMES.update({op + 6: name + "/range" for op, name in list(METHOD_NAMES.items())})
METHOD_NAMES.update({0xFA: "invoke-polymorphic", 0xFB: "invoke-polymorphic/range"})
DYNAMIC_NAMES = {
    **METHOD_NAMES,
    0xFC: "invoke-custom",
    0xFD: "invoke-custom/range",
    0xFE: "const-method-handle",
}


class Dex:
    def __init__(self, data):
        self.data = data
        if len(data) < 112 or data[:4] != b"dex\n" or data[7] != 0:
            raise InvalidDex("Invalid standard DEX header")
        self.version = int(data[4:7])
        if self.version not in {35, 37, 38, 39, 40}:
            raise InvalidDex("Unsupported DEX version")
        if self.u32(32) != len(data) or self.u32(36) != 112 or self.u32(40) != 0x12345678:
            raise InvalidDex("Invalid DEX size or byte order")
        self.tables = []
        for position, width in ((56, 4), (64, 4), (72, 12), (80, 8), (88, 8), (96, 32)):
            count, offset = self.u32(position), self.u32(position + 4)
            if position in {80, 88} and count > 65536:
                raise InvalidDex("DEX member pool exceeds 16-bit index range")
            if count and offset < 112:
                raise InvalidDex("DEX table overlaps header")
            self.check(offset, count * width)
            self.tables.append((count, offset, width))
        # Instance-local caches are discarded with this DEX, never retained globally.
        self.string = lru_cache(maxsize=65536)(self._string)
        self.type = lru_cache(maxsize=None)(self._type)
        self.proto = lru_cache(maxsize=None)(self._proto)
        self.method = lru_cache(maxsize=65536)(self._method)
        self.field = lru_cache(maxsize=65536)(self._field)

    def close(self):
        for cache in (self.string, self.type, self.proto, self.method, self.field):
            cache.cache_clear()
        self.data = b""

    def check(self, offset, size):
        if offset < 0 or size < 0 or offset + size > len(self.data):
            raise InvalidDex("DEX range out of bounds")

    def u16(self, offset):
        self.check(offset, 2)
        return struct.unpack_from("<H", self.data, offset)[0]

    def u32(self, offset):
        self.check(offset, 4)
        return struct.unpack_from("<I", self.data, offset)[0]

    def leb(self, offset):
        if offset < 0:
            raise InvalidDex("Negative DEX offset")
        value = 0
        for shift in range(0, 35, 7):
            try:
                byte = self.data[offset]
            except IndexError as exc:
                raise InvalidDex("Truncated DEX uleb128") from exc
            offset += 1
            if shift == 28 and byte > 15:
                raise InvalidDex("Invalid DEX uleb128")
            value |= (byte & 127) << shift
            if byte < 128:
                return value, offset
        raise InvalidDex("Unterminated DEX uleb128")

    def item(self, table, index):
        count, offset, width = self.tables[table]
        if not 0 <= index < count:
            raise InvalidDex("DEX pool index out of bounds")
        return offset + index * width

    def _string(self, index):
        offset = self.u32(self.item(0, index))
        length, offset = self.leb(offset)
        end = self.data.find(b"\0", offset)
        if end < 0:
            raise InvalidDex("Unterminated DEX string")
        return decode_mutf8(self.data[offset:end], length)

    def _type(self, index):
        return self.string(self.u32(self.item(1, index)))

    def types(self, offset):
        if not offset:
            return ()
        count = self.u32(offset)
        self.check(offset + 4, count * 2)
        return tuple(self.type(self.u16(offset + 4 + i * 2)) for i in range(count))

    def _proto(self, index):
        offset = self.item(2, index)
        self.string(self.u32(offset))
        return (
            "(" + "".join(self.types(self.u32(offset + 8))) + ")" + self.type(self.u32(offset + 4))
        )

    def _method(self, index):
        offset = self.item(4, index)
        return (
            self.type(self.u16(offset))
            + "->"
            + self.string(self.u32(offset + 4))
            + self.proto(self.u16(offset + 2))
        )

    def _field(self, index):
        offset = self.item(3, index)
        return (
            self.type(self.u16(offset))
            + "->"
            + self.string(self.u32(offset + 4))
            + ":"
            + self.type(self.u16(offset + 2))
        )

    def classes(self, *, accelerator=True, ordered=True):
        raw = None
        checked = False
        if accelerator:
            try:
                from . import _dexscan
            except ImportError:
                pass
            else:
                checked = hasattr(_dexscan, "checked_classes")
                native_classes = _dexscan.checked_classes if checked else _dexscan.classes
                try:
                    raw = native_classes(
                        self.data,
                        self.tables[5][1],
                        self.tables[5][0],
                        self.tables[1][1],
                        self.tables[1][0],
                        self.tables[0][1],
                        self.tables[0][0],
                    )
                except ValueError as exc:
                    raise InvalidDex(str(exc)) from exc
        if checked:
            result, deferred, seen = raw
            # The native cursor has already checked every ASCII identity and
            # duplicate. Only Unicode rows need the strict independent decoder.
            for index in deferred:
                _, offset = result[index]
                name = self.type(self.u32(offset))
                if name in seen:
                    raise InvalidDex("Duplicate class definition")
                seen.add(name)
                result[index] = name, offset
            return sorted(result, key=lambda row: utf16_key(row[0])) if ordered else result
        if raw is None:
            raw = [(None, self.item(5, i)) for i in range(self.tables[5][0])]
        result = []
        seen = set()
        for name, offset in raw:
            if name is None:
                name = self.type(self.u32(offset))
            if name in seen:
                raise InvalidDex("Duplicate class definition")
            seen.add(name)
            result.append((name, offset))
        return sorted(result, key=lambda row: utf16_key(row[0])) if ordered else result

    def members(self, cls):
        fields, methods = self.raw_members(cls)
        self.method_indices = {self.method(index): index for index, _, _ in methods}
        return (
            sorted(
                ((self.field(index), flags, index) for index, flags in fields),
                key=lambda row: utf16_key(row[0]),
            ),
            sorted(
                ((self.method(index), flags, code) for index, flags, code in methods),
                key=lambda row: utf16_key(row[0]),
            ),
        )

    def raw_members(self, cls, *, accelerator=True):
        offset = self.u32(cls + 24)
        if not offset:
            return [], []
        if accelerator and _native_members is not None:
            try:
                return _native_members(self.data, offset, self.tables[3][0], self.tables[4][0])
            except ValueError as exc:
                raise InvalidDex(str(exc)) from exc
        sizes = []
        for _ in range(4):
            size, offset = self.leb(offset)
            sizes.append(size)
        if sum(sizes) > self.tables[3][0] + self.tables[4][0]:
            raise InvalidDex("Invalid class data count")
        fields, methods = [], []
        seen = set()
        for group, count in enumerate(sizes):
            index = 0
            for _ in range(count):
                diff, offset = self.leb(offset)
                index += diff
                flags, offset = self.leb(offset)
                self.item(3 if group < 2 else 4, index)
                key = (group < 2, index)
                if key in seen:
                    raise InvalidDex("Duplicate member definition")
                seen.add(key)
                if group < 2:
                    fields.append((index, flags))
                else:
                    code, offset = self.leb(offset)
                    methods.append((index, flags, code))
        return fields, methods

    def ordered_methods(self, methods):
        """DEX string IDs already have UTF-16 order; decode only overloaded prototypes."""
        groups = {}
        for index, flags, code in methods:
            position = self.item(4, index)
            name = self.u32(position + 4)
            self.item(0, name)
            self.item(2, self.u16(position + 2))
            groups.setdefault(name, []).append((index, flags, code))
        for name in sorted(
            groups,
            key=lambda index: (self.string(index) + "(").encode("utf-16-be", "surrogatepass"),
        ):
            rows = groups[name]
            if len(rows) > 1:
                rows.sort(
                    key=lambda row: self.proto(self.u16(self.item(4, row[0]) + 2)).encode(
                        "utf-16-be", "surrogatepass"
                    )
                )
            yield from rows

    def matching_types(self, owner, *, fuzzy=False, case_sensitive=True, accelerator=True):
        matches = set()
        deferred = range(self.tables[1][0])
        if accelerator and owner.isascii():
            try:
                from ._dexscan import matching_types as native_types
            except ImportError:
                pass
            else:
                try:
                    selected, deferred = native_types(
                        self.data,
                        self.tables[1][1],
                        self.tables[1][0],
                        self.tables[0][1],
                        self.tables[0][0],
                        owner.encode("ascii"),
                        fuzzy,
                        case_sensitive,
                    )
                    matches.update(selected)
                except ValueError as exc:
                    raise InvalidDex(str(exc)) from exc
        if not case_sensitive:
            owner = owner.lower()
        for index in deferred:
            candidate = self.type(index)
            if not case_sensitive:
                candidate = candidate.lower()
            if owner in candidate if fuzzy else owner == candidate:
                matches.add(index)
        return matches

    def owner_members(self, fields, owners, *, accelerator=True):
        table = 3 if fields else 4
        count, offset, _ = self.tables[table]
        if accelerator:
            try:
                from ._dexscan import owner_members as native_owners
            except ImportError:
                pass
            else:
                mask = bytearray(65536)
                for index in owners:
                    if 0 <= index < len(mask):
                        mask[index] = 1
                try:
                    return native_owners(self.data, offset, count, self.tables[1][0], bytes(mask))
                except ValueError as exc:
                    raise InvalidDex(str(exc)) from exc
        result = []
        for index in range(count):
            owner = self.u16(self.item(table, index))
            self.item(1, owner)
            if owner in owners:
                result.append(index)
        return result

    def matching_ids(self, requested, fields):
        owner = requested.split("->", 1)[0]
        owners = self.matching_types(owner)
        if not owners:
            return set()
        member = self.field if fields else self.method
        return {index for index in self.owner_members(fields, owners) if member(index) == requested}

    def instructions(self, code):
        if not code:
            return
        if code % 4:
            raise InvalidDex("Unaligned DEX code item")
        self.check(code, 16)
        start = code + 16
        end = start + self.u32(code + 12) * 2
        self.check(start, end - start)
        data, widths, position = self.data, WIDTHS, start
        while position < end:
            opcode = data[position]
            width = widths[opcode]
            if opcode >= 0xFA and self.version < (39 if opcode >= 0xFE else 38):
                raise InvalidDex("Opcode unavailable in this DEX version")
            if opcode == 0 and data[position + 1]:
                kind = data[position + 1]
                header = 8 if kind == 3 else 4
                if position % 4 or position + header > end:
                    raise InvalidDex("Invalid or truncated DEX payload header")
                size = self.u16(position + 2)
                if kind == 1:
                    width = 4 + 2 * size
                elif kind == 2:
                    width = 2 + 4 * size
                elif kind == 3:
                    if size not in {1, 2, 4, 8}:
                        raise InvalidDex("Invalid DEX array element width")
                    width = 4 + (size * self.u32(position + 4) + 1) // 2
                else:
                    raise InvalidDex("Unknown DEX payload")
            if not width or position + width * 2 > end:
                raise InvalidDex("Unknown, optimized or truncated DEX instruction")
            yield position, (position - start) // 2, opcode
            position += width * 2


def dex_entries(bundle):
    with zipfile.ZipFile(bundle) as archive:
        for entry in sorted(archive.namelist()):
            if not entry.endswith(".dex"):
                continue
            dex = Dex(archive.read(entry))
            try:
                yield entry, dex
            finally:
                dex.close()


def class_inventory(bundle):
    owners = {}
    for entry, dex in dex_entries(bundle):
        for name, _ in dex.classes():
            if name in owners:
                raise InvalidDex("Duplicate class definition across DEX files")
            owners[name] = entry
    return owners


def page_result(result, query, settings):
    offset = query.get("offset", 0)
    limit = min(query.get("limit", settings.max_page_size), settings.max_page_size)
    more = offset + len(result.get("items", [])) < result.get("total", 0)
    return {
        **result,
        "offset": offset,
        "limit": limit,
        "has_more": more,
        "truncated": more,
        "next_offset": offset + limit if more else None,
    }


def query_references(settings, bundle, query):
    try:
        return page_result(_references(bundle, query, settings), query, settings)
    except (InvalidDex, struct.error, UnicodeError) as exc:
        raise DroidAscError("Invalid DEX instruction scan: " + str(exc)) from exc


def _references(bundle, query, settings):
    operation = query["operation"]
    fuzzy = operation == "search_refs"
    fields = query.get("kind") == "field" if fuzzy else operation == "find_field_refs"
    requested = query.get("field_descriptor" if fields else "method_descriptor")
    incoming = operation != "get_method_calls"
    access = query.get("field_access", "all")
    offset, limit = query.get("offset", 0), min(query.get("limit", 100), settings.max_page_size)
    items, dynamic = [], []
    totals = Counter()
    definitions = {}
    methods = instructions = without_code = dynamic_count = total = 0
    for entry, dex in dex_entries(bundle):
        member = dex.field if fields else dex.method
        targets = set()
        if fuzzy:
            owner_query = query.get("class_name")
            owners = (
                dex.matching_types(
                    owner_query,
                    fuzzy=query.get("fuzzy_class", False),
                    case_sensitive=query.get("case_sensitive", True),
                )
                if owner_query
                else None
            )
            candidates = (
                dex.owner_members(fields, owners)
                if owners is not None
                else range(dex.tables[3 if fields else 4][0])
            )
            for i in candidates:
                text = member(i)
                _, local = text.split("->", 1)
                target_descriptor = query.get("target_descriptor")
                if (
                    target_descriptor
                    and (local.split(":", 1)[1] if fields else local[local.index("(") :])
                    != target_descriptor
                ):
                    continue
                mode = query.get("member_match", "descriptor")
                name = local.split(":" if fields else "(", 1)[0]
                candidate = (
                    name
                    if mode in {"name", "exact_name"}
                    else local[local.index("(") :]
                    if mode == "prototype" and not fields
                    else text
                )
                value = query.get("value") or ""
                if not query.get("case_sensitive", True):
                    candidate, value = candidate.lower(), value.lower()
                if not value or (
                    candidate == value if mode == "exact_name" else value in candidate
                ):
                    targets.add(i)
        elif incoming:
            # Resolve IDs once, then compare integers at exact instruction boundaries.
            targets = dex.matching_ids(requested, fields)
        from .native_scan import class_selector, method_selector, scanner, select_directory

        scan = scanner(dex, targets, fields, incoming)
        fused = class_selector(dex, targets, fields, access) if incoming else None
        select = (
            method_selector(dex, targets, fields, access) if incoming and fused is None else None
        )
        if fused is not None:
            directory, declared, count, decoded, dynamic_sites, without = select_directory(
                dex, fused
            )
            methods += count
            instructions += decoded
            dynamic_count += dynamic_sites
            without_code += without
            for index in declared:
                definitions[member(index)] = entry
        else:
            directory = dex.classes()
        for owner, cls in directory:
            if fused is not None:
                method_defs = dex.ordered_methods(cls)
            elif incoming:
                field_defs, raw_methods = dex.raw_members(cls)
                if fields:
                    for index, _ in field_defs:
                        if index in targets:
                            definitions[member(index)] = entry
                # Preserve exact output order without decoding every caller identity.
                # Sparse queries scan once, then revisit only matching code items.
                bulk = select(raw_methods) if select is not None else None
                if bulk is not None:
                    selected, count, dynamic_sites, without = bulk
                    instructions += count
                    dynamic_count += dynamic_sites
                    without_code += without
                    methods += len(raw_methods)
                else:
                    selected = []
                for index, flags, code in raw_methods if bulk is None else ():
                    position = dex.item(4, index)
                    dex.item(0, dex.u32(position + 4))
                    dex.item(2, dex.u16(position + 2))
                    methods += 1
                    if not code:
                        without_code += 1
                        continue
                    wanted = False
                    for position, _, op, count in scan(code):
                        instructions += count
                        if 0x52 <= op <= 0x6D if fields else op in METHOD_NAMES:
                            operand = dex.u16(position + 2)
                            dex.item(3 if fields else 4, operand)
                            read = 0x52 <= op <= 0x58 or 0x60 <= op <= 0x66
                            if operand in targets and (
                                not fields
                                or access == "all"
                                or access == ("read" if read else "write")
                            ):
                                wanted = True
                        if op in {0xFA, 0xFB, 0xFC, 0xFD, 0xFE}:
                            dynamic_count += 1
                            wanted |= len(dynamic) < 20
                    if wanted:
                        selected.append((index, flags, code))
                method_defs = dex.ordered_methods(selected)
                for index, _, _ in raw_methods:
                    if not fields and index in targets:
                        definitions[member(index)] = entry
            else:
                if not requested.startswith(owner + "->"):
                    continue
                _, raw_methods = dex.raw_members(cls)
                method_defs = dex.ordered_methods(raw_methods)
            if not incoming and not requested.startswith(owner + "->"):
                continue
            for method_index, _flags, code in method_defs:
                caller = dex.method(method_index) if not incoming else None
                if not incoming and caller != requested:
                    continue
                if not incoming:
                    definitions[caller] = entry
                methods += not incoming
                if not code:
                    without_code += not incoming
                    continue
                for position, address, op, count in scan(code):
                    if not incoming:
                        instructions += count
                    is_field = 0x52 <= op <= 0x6D
                    is_method = op in METHOD_NAMES
                    callee = None
                    if (fields and is_field) or (not fields and is_method):
                        index = dex.u16(position + 2)
                        dex.item(3 if fields else 4, index)
                        if not incoming or index in targets:
                            callee = member(index)
                    if callee is not None:
                        if caller is None:
                            caller = dex.method(method_index)
                        opcode = FIELD_NAMES[op - 0x52] if fields else METHOD_NAMES[op]
                        field_access = (
                            "read" if 0x52 <= op <= 0x58 or 0x60 <= op <= 0x66 else "write"
                        )
                        if not fields or access in {"all", field_access}:
                            totals[callee] += 1
                            if offset <= total < offset + limit:
                                row = {
                                    "caller": caller,
                                    "field_descriptor" if fields else "callee": callee,
                                    "dex_entry": entry,
                                    "instruction_offset": address,
                                    "offset_unit": "code_units_from_method_start",
                                    "opcode": opcode,
                                }
                                if fields:
                                    row.update(
                                        access=field_access,
                                        storage="static" if op >= 0x60 else "instance",
                                    )
                                if op in {0xFA, 0xFB}:
                                    row["call_site_prototype"] = dex.proto(dex.u16(position + 6))
                                items.append(row)
                            total += 1
                    if op in {0xFA, 0xFB, 0xFC, 0xFD, 0xFE}:
                        dynamic_count += not incoming
                        if len(dynamic) < 20:
                            if caller is None:
                                caller = dex.method(method_index)
                            dynamic.append(
                                {
                                    "caller": caller,
                                    "dex_entry": entry,
                                    "instruction_offset": address,
                                    "opcode": DYNAMIC_NAMES[op],
                                    "reason": "dynamic_target_not_resolved",
                                }
                            )
    if not incoming and totals:
        wanted_owners = {name.split("->", 1)[0] for name in totals}
        for entry, dex in dex_entries(bundle):
            for owner, cls in dex.classes():
                if owner in wanted_owners:
                    _, methods_in_class = dex.raw_members(cls)
                    for index, _, _ in methods_in_class:
                        name = dex.method(index)
                        if name in totals:
                            definitions[name] = entry
    for row in items:
        target = row["field_descriptor" if fields else "callee"]
        row["target_dex_entry"] = definitions.get(target)
        row["target_resolution"] = (
            "defined_in_input" if target in definitions else "not_defined_in_input"
        )
    base = {
        "status": "ok",
        "backend": "native-dex-instructions",
        "backend_version": "1",
        "items": items,
        "total": total,
        "reference_semantics": "declared_field_operand" if fields else "declared_method_operand",
        "scan_scope": "supplied_dex_methods" if incoming else "selected_method",
        "scanned_methods": methods,
        "scanned_instructions": instructions,
        "methods_without_code": without_code,
        "scan_errors": 0,
        "unresolved_matches": sum(
            count for name, count in totals.items() if name not in definitions
        ),
        "dynamic_sites": dynamic_count,
        "unresolved_sites": dynamic,
        "unresolved_sites_truncated": dynamic_count > len(dynamic),
        "instruction_scan_complete": True,
        "runtime_target_resolution": "not_performed",
        "limitations": [
            "inherited_field_resolution",
            "reflection",
            "jni",
            "runtime_loaded_code",
            "encoded_initial_values",
            "method_handle_targets",
        ]
        if fields
        else ["virtual_dispatch", "reflection", "jni", "runtime_loaded_code"],
    }
    if not fuzzy:
        base["field_descriptor" if fields else "method_descriptor"] = requested
    else:
        base.update(kind=query["kind"], matched_targets=len(totals))
    if fields:
        base["field_access"] = access
    if not incoming and requested not in definitions:
        return {
            "status": "error",
            "code": "method_not_found",
            "method_descriptor": requested,
            "backend": base["backend"],
            "backend_version": base["backend_version"],
        }
    return base
