"""Structural views and ASC's DAD instruction rendering, without a JVM."""

import struct

from .native_dex import dex_entries, page_result, utf16_key
from .native_index import split_types
from .native_page import SortedPage
from .worker_errors import DroidAscError


def method_row(descriptor, flags, code):
    local = descriptor.split("->", 1)[1]
    name, proto = local.split("(", 1)
    args, result = proto.split(")", 1)
    return {
        "descriptor": descriptor,
        "name": name,
        "parameter_types": list(split_types(args)),
        "return_type": result,
        "access_flags": flags,
        "has_code": bool(code),
    }


class Packers(dict):
    def __missing__(self, key):
        value = self[key] = struct.Struct("<" + key)
        return value


class MethodReference:
    def __init__(self, descriptor):
        self.owner, local = descriptor.split("->", 1)
        self.name, proto = local.split("(", 1)
        self.proto = "(" + proto

    def get_class_name(self):
        return self.owner

    def get_name(self):
        return self.name

    def get_real_descriptor(self):
        return self.proto


class References:
    """Small reference-provider protocol for the public DAD instruction decoder."""

    def __init__(self, dex):
        self.dex = dex
        self.packer = Packers()

    def get_string(self, index):
        return self.dex.string(index)

    def get_type(self, index):
        return self.dex.type(index)

    def get_method_ref(self, index):
        return MethodReference(self.dex.method(index))

    def get_field(self, index):
        owner, local = self.dex.field(index).split("->", 1)
        name, typ = local.split(":", 1)
        return owner, typ, name

    def get_proto(self, index):
        args, result = self.dex.proto(index).split(")", 1)
        return args + ")", result


def render(dex, refs, position, address, op, *, budget=256 * 1024):
    from dadguard.core.dex import Operand, get_instruction

    payload = op == 0 and dex.data[position + 1]
    if payload:
        size = dex.u16(position + 2)
        if payload == 3:
            count = dex.u32(position + 4)
            if count * (2 * size + 6) + 64 > budget:
                raise DroidAscError("Payload rendering exceeds output budget; narrow the query")
            values = [
                hex(int.from_bytes(dex.data[start : start + size], "little", signed=True))
                for start in range(position + 8, position + 8 + size * count, size)
            ]
            return "array-payload", f"array-payload {size} {{" + ", ".join(values) + "}"
        if size * 32 + 64 > budget:
            raise DroidAscError("Payload rendering exceeds output budget; narrow the query")
        if payload == 1:
            first = struct.unpack_from("<i", dex.data, position + 4)[0]
            keys = range(first, first + size)
            targets = position + 8
            name = "packed-switch-payload"
        else:
            keys = struct.unpack_from(f"<{size}i", dex.data, position + 4)
            targets = position + 4 + size * 4
            name = "sparse-switch-payload"
        values = [
            f"{hex(key)} -> {struct.unpack_from('<i', dex.data, targets + i * 4)[0]:+d}"
            for i, key in enumerate(keys)
        ]
        return name, name + " {" + ", ".join(values) + "}"
    instruction = get_instruction(refs, op, dex.data[position : position + 10])
    name = instruction.get_name()
    if op in {0xFC, 0xFD, 0xFE, 0xFF}:
        # DAD's generic kind renderer does not resolve these reference kinds.
        kind = "method_handle" if op == 0xFE else "prototype" if op == 0xFF else "call_site"
        operand = (
            dex.proto(dex.u16(position + 2))
            if op == 0xFF
            else f"{kind}@0x{dex.u16(position + 2):x}"
        )
        return name, name + " " + instruction.get_output(address * 2).replace("None", operand)
    # DAD's two-reference formats expose get_output but no operand decoder.
    operands = None if op in {0xFA, 0xFB} else instruction.get_operands(address * 2)
    if operands and all(row[0] in {Operand.REGISTER, Operand.LITERAL} for row in operands):
        values = [
            f"v{value}" if kind == Operand.REGISTER else hex(value) for kind, value in operands
        ]
        return name, name + " " + ", ".join(values)
    return name, (name + " " + instruction.get_output(address * 2)).rstrip()


def query_structure(settings, bundle, query, workspace=None):
    offset = query.get("offset", 0)
    limit = min(query.get("limit", 100), settings.max_page_size)
    with SortedPage(settings, offset, limit, workspace) as page:
        return _query_structure(settings, bundle, query, page)


def _query_structure(settings, bundle, query, page):
    operation, owner = query["operation"], query.get("class_name")
    requested = query.get("method_descriptor")
    offset, limit = query.get("offset", 0), min(query.get("limit", 100), settings.max_page_size)
    result = {
        "status": "ok",
        "backend": "native-dex-structure",
        "backend_version": "1",
        "runtime_target_resolution": "not_performed",
        "scope": "supplied_dex_definitions_only",
    }
    items, total, scanned, without = [], 0, 0, 0
    found_class = found_method = False

    def add(row):
        nonlocal total
        if offset <= total < offset + limit:
            items.append(row)
        total += 1

    if operation == "get_class_hierarchy":
        classes = {}
        for entry, dex in dex_entries(bundle):
            for name, cls in dex.classes():
                parent = dex.u32(cls + 8)
                classes[name] = (
                    entry,
                    None if parent == 0xFFFFFFFF else dex.type(parent),
                    dex.types(dex.u32(cls + 12)),
                )
        if owner not in classes:
            return {"status": "error", "code": "class_not_found"}
        entry, current, interfaces = classes[owner]
        result.update(class_name=owner, dex_entry=entry)
        seen, depth = {owner}, 0
        while current is not None and current not in seen:
            seen.add(current)
            depth += 1
            add(
                {
                    "relation": "superclass",
                    "type_descriptor": current,
                    "depth": depth,
                    "definition_resolution": "supplied" if current in classes else "external",
                }
            )
            current = classes[current][1] if current in classes else None
        result["hierarchy_cycle_detected"] = current is not None
        for interface in sorted(interfaces, key=utf16_key):
            add({"relation": "interface", "type_descriptor": interface})
        for name in sorted(classes, key=lambda text: text.encode("utf-16-be", "surrogatepass")):
            if classes[name][1] == owner:
                add({"relation": "direct_subclass", "type_descriptor": name})
            if owner in classes[name][2]:
                add({"relation": "direct_implementor", "type_descriptor": name})
    else:
        for entry, dex in dex_entries(bundle):
            refs = (
                References(dex)
                if operation in {"disassemble_method", "search_method_bodies"}
                else None
            )
            for name, cls in dex.classes():
                if owner and name != owner:
                    continue
                found_class = True
                fields, methods = dex.members(cls)
                if operation in {"get_class_outline", "list_methods"}:
                    result.update(class_name=name, dex_entry=entry)
                    if operation == "get_class_outline":
                        parent = dex.u32(cls + 8)
                        result.update(
                            access_flags=dex.u32(cls + 4),
                            superclass=None if parent == 0xFFFFFFFF else dex.type(parent),
                            field_count=len(fields),
                            method_count=len(methods),
                        )
                        for typ in sorted(dex.types(dex.u32(cls + 12)), key=utf16_key):
                            add({"kind": "interface", "type_descriptor": typ})
                        for descriptor, flags, _ in fields:
                            local, typ = descriptor.split("->", 1)[1].split(":", 1)
                            add(
                                {
                                    "kind": "field",
                                    "descriptor": descriptor,
                                    "name": local,
                                    "type_descriptor": typ,
                                    "access_flags": flags,
                                    "storage": "static" if flags & 8 else "instance",
                                }
                            )
                    for descriptor, flags, code in methods:
                        row = method_row(descriptor, flags, code)
                        if operation == "get_class_outline":
                            row.update(
                                kind="method",
                                dispatch_kind="direct"
                                if flags & 10 or row["name"] == "<init>"
                                else "virtual",
                            )
                        add(row)
                    continue
                for descriptor, _flags, code in methods:
                    if requested and descriptor != requested:
                        continue
                    found_method = True
                    if not code:
                        without += 1
                        continue
                    for position, address, op in dex.instructions(code):
                        scanned += 1
                        if operation == "get_string_constants":
                            if op not in {0x1A, 0x1B}:
                                continue
                            index = dex.u16(position + 2) if op == 0x1A else dex.u32(position + 2)
                            row = {"value": dex.string(index)}
                            opcode = "const-string" if op == 0x1A else "const-string/jumbo"
                        else:
                            opcode, text = render(
                                dex, refs, position, address, op, budget=settings.max_output_bytes
                            )
                            needle = query.get("value") or ""
                            sensitive = query.get("case_sensitive", False)
                            if operation == "search_method_bodies" and (
                                needle if sensitive else needle.lower()
                            ) not in (text if sensitive else text.lower()):
                                continue
                            row = {"instruction": text}
                        row.update(
                            class_name=name,
                            method_descriptor=descriptor,
                            dex_entry=entry,
                            opcode=opcode,
                            instruction_offset=address,
                            offset_unit="16_bit_code_units",
                        )
                        page.add((utf16_key(name), utf16_key(descriptor), address), row)
        if owner and not found_class:
            return {"status": "error", "code": "class_not_found"}
        if requested and not found_method:
            return {"status": "error", "code": "method_not_found"}
        if operation not in {"get_class_outline", "list_methods"}:
            items, total = page.items(), page.total
            result.update(
                scanned_instructions=scanned,
                methods_without_code=without,
                instruction_scan_complete=True,
                scan_errors=0,
                match_semantics="exact_method_identity"
                if operation == "disassemble_method"
                else "const_string_operands_only"
                if operation == "get_string_constants"
                else (
                    "case_sensitive" if query.get("case_sensitive", False) else "case_insensitive"
                )
                + "_literal_dad_instruction_text",
            )
    return page_result({**result, "items": items, "total": total}, query, settings)
