"""Streaming native DEX records for atomic SQLite indexes."""

from .native_dex import (
    DYNAMIC_NAMES,
    FIELD_NAMES,
    METHOD_NAMES,
    TYPE_OPS,
    InvalidDex,
    dex_entries,
    utf16_key,
)


def records(bundle, calls_only=False):
    edges = 0
    for entry, dex in dex_entries(bundle):
        from .native_scan import scanner

        scan = scanner(dex, set(), False, False) if calls_only else None

        def definition(kind, descriptor, entry=entry):
            return {
                "record": "definition",
                "kind": kind,
                "descriptor": descriptor,
                "dex_entry": entry,
            }

        def edge(kind, source, target, relation, data, entry=entry):
            nonlocal edges
            edges += 1
            return {
                "record": "edge",
                "kind": kind,
                "source": source,
                "target": target,
                "relation": relation,
                "data": {**data, "dex_entry": entry},
            }

        def types(source, target, relation, detail, address=None):
            if target is not None and target != "V" and not calls_only:
                yield edge(
                    "type",
                    source,
                    target,
                    relation,
                    {"detail": detail, "instruction_offset": address},
                )

        def proto(source, prototype, relation, detail, address=None):
            args, result = prototype[1:].split(")", 1)
            yield from types(source, result, relation, detail + ":return", address)
            for index, parameter in enumerate(split_types(args)):
                yield from types(
                    source, parameter, relation, detail + f":parameter:{index}", address
                )

        def member_types(source, descriptor, field, relation, detail, address=None):
            owner, local = descriptor.split("->", 1)
            yield from types(source, owner, relation, detail + ":owner", address)
            if field:
                yield from types(
                    source, local.split(":", 1)[1], relation, detail + ":field_type", address
                )
            else:
                yield from proto(source, local[local.index("(") :], relation, detail, address)

        def value(offset, path, depth=0, dex=dex):
            if depth > 128:
                raise InvalidDex("Annotation nesting exceeds limit")
            dex.check(offset, 1)
            header = dex.data[offset]
            kind, width = header & 31, (header >> 5) + 1
            offset += 1
            result = []
            if kind in {0x1C, 0x1D}:
                if width != 1:
                    raise InvalidDex("Invalid encoded container value")
                count, offset = dex.leb(offset)
                if kind == 0x1D:
                    annotation_type = dex.type(count)
                    result.append(("type", annotation_type, path + ":type"))
                    count, offset = dex.leb(offset)
                if count > len(dex.data) - offset:
                    raise InvalidDex("Invalid encoded value count")
                for index in range(count):
                    if kind == 0x1D:
                        name, offset = dex.leb(offset)
                        nested = path + "." + dex.string(name)
                    else:
                        nested = path + f"[{index}]"
                    offset, values = value(offset, nested, depth + 1)
                    result.extend(values)
            elif kind in {0x1E, 0x1F}:
                if header >> 5 > (1 if kind == 0x1F else 0):
                    raise InvalidDex("Invalid encoded null/boolean")
            else:
                maxima = {
                    0: 1,
                    2: 2,
                    3: 2,
                    4: 4,
                    6: 8,
                    0x10: 4,
                    0x11: 8,
                    0x15: 4,
                    0x16: 4,
                    0x17: 4,
                    0x18: 4,
                    0x19: 4,
                    0x1A: 4,
                    0x1B: 4,
                }
                if kind not in maxima or width > maxima[kind]:
                    raise InvalidDex("Invalid encoded value")
                dex.check(offset, width)
                index = int.from_bytes(dex.data[offset : offset + width], "little")
                offset += width
                if kind == 0x18:
                    result.append(("type", dex.type(index), path))
                elif kind in {0x19, 0x1B}:
                    result.append(("field", dex.field(index), path))
                elif kind == 0x1A:
                    result.append(("method", dex.method(index), path))
                elif kind == 0x15:
                    result.append(("proto", dex.proto(index), path))
                elif kind == 0x17:
                    dex.string(index)
            return offset, result

        def annotations(source, offset, location, dex=dex):
            if not offset or calls_only:
                return
            count = dex.u32(offset)
            dex.check(offset + 4, count * 4)
            sets = []
            for index in range(count):
                item = dex.u32(offset + 4 + index * 4)
                dex.check(item, 1)
                typ, body = dex.leb(item + 1)
                sets.append((dex.type(typ), body))
            for typ, body in sorted(sets, key=lambda item: utf16_key(item[0])):
                path = location + ":" + typ
                yield from types(source, typ, "annotation", path + ":type")
                size, body = dex.leb(body)
                values = []
                if size > len(dex.data) - body:
                    raise InvalidDex("Invalid annotation size")
                for _ in range(size):
                    name, body = dex.leb(body)
                    body, nested = value(body, path + "." + dex.string(name))
                    values.extend(nested)
                # DEX annotation elements are ordered by name_idx; arrays retain numeric order.
                for kind, descriptor, detail in values:
                    if kind == "type":
                        yield from types(source, descriptor, "annotation", detail)
                    elif kind == "proto":
                        yield from proto(source, descriptor, "annotation", detail)
                    else:
                        yield from member_types(
                            source, descriptor, kind == "field", "annotation", detail
                        )

        for owner, cls in dex.classes():
            if not calls_only:
                yield definition("type", owner)
                parent = dex.u32(cls + 8)
                if parent != 0xFFFFFFFF:
                    yield from types(owner, dex.type(parent), "declaration", "superclass")
                for interface in dex.types(dex.u32(cls + 12)):
                    yield from types(owner, interface, "declaration", "interface")
            directory = dex.u32(cls + 20)
            field_annotations, method_annotations, parameter_annotations = {}, {}, {}
            if directory and not calls_only:
                yield from annotations(owner, dex.u32(directory), "class")
                counts = [dex.u32(directory + 4 + i * 4) for i in range(3)]
                position = directory + 16
                for table, count in zip(
                    (field_annotations, method_annotations, parameter_annotations),
                    counts,
                    strict=True,
                ):
                    dex.check(position, count * 8)
                    for _ in range(count):
                        table[dex.u32(position)] = dex.u32(position + 4)
                        position += 8
            if calls_only:
                _, raw_methods = dex.raw_members(cls)
                fields = []
                methods = (
                    (dex.method(index), flags, code)
                    for index, flags, code in dex.ordered_methods(raw_methods)
                )
            else:
                fields, methods = dex.members(cls)
            for name, _, index in fields:
                if not calls_only:
                    yield definition("field", name)
                    yield from types(name, name.split(":", 1)[1], "declaration", "field_type")
                    yield from annotations(name, field_annotations.get(index), "field")
            for source, _, code in methods:
                yield definition("method", source)
                if not calls_only:
                    local = source.split("->", 1)[1]
                    args, result = local[local.index("(") + 1 :].split(")", 1)
                    yield from types(source, result, "declaration", "return")
                    method_index = dex.method_indices[source]
                    yield from annotations(source, method_annotations.get(method_index), "method")
                    parameters = parameter_annotations.get(method_index)
                    if parameters:
                        count = dex.u32(parameters)
                        dex.check(parameters + 4, count * 4)
                    for index, typ in enumerate(split_types(args)):
                        yield from types(source, typ, "declaration", f"parameter:{index}")
                        if parameters and index < count:
                            yield from annotations(
                                source, dex.u32(parameters + 4 + index * 4), f"parameter:{index}"
                            )
                count = 0
                if code:
                    if not calls_only:
                        for typ, address in catch_types(dex, code):
                            yield from types(source, typ, "instruction", "catch", address)
                    walk = (
                        scan(code)
                        if calls_only
                        else ((p, a, op, 1) for p, a, op in dex.instructions(code))
                    )
                    for position, address, op, skipped in walk:
                        count += skipped
                        if op == -1:
                            continue
                        row = {"instruction_offset": address, "opcode": ""}
                        if op in METHOD_NAMES:
                            target = dex.method(dex.u16(position + 2))
                            row["opcode"] = METHOD_NAMES[op]
                            if op in {0xFA, 0xFB}:
                                prototype = dex.proto(dex.u16(position + 6))
                                row["call_site_prototype"] = prototype
                            yield edge("method", source, target, "instruction", row)
                            yield from member_types(
                                source, target, False, "instruction", row["opcode"], address
                            )
                            if op in {0xFA, 0xFB}:
                                yield from proto(
                                    source,
                                    prototype,
                                    "instruction",
                                    row["opcode"] + ":prototype",
                                    address,
                                )
                        elif 0x52 <= op <= 0x6D and not calls_only:
                            target = dex.field(dex.u16(position + 2))
                            opcode = FIELD_NAMES[op - 0x52]
                            access = "read" if 0x52 <= op <= 0x58 or 0x60 <= op <= 0x66 else "write"
                            row.update(
                                opcode=opcode, storage="static" if op >= 0x60 else "instance"
                            )
                            yield edge("field", source, target, access, row)
                            yield from member_types(
                                source, target, True, "instruction", opcode, address
                            )
                        elif op in TYPE_OPS and not calls_only:
                            yield from types(
                                source,
                                dex.type(dex.u16(position + 2)),
                                "instruction",
                                TYPE_OPS[op],
                                address,
                            )
                        elif op == 0xFF and not calls_only:
                            yield from proto(
                                source,
                                dex.proto(dex.u16(position + 2)),
                                "instruction",
                                "const-method-type",
                                address,
                            )
                        if op in {0xFA, 0xFB, 0xFC, 0xFD, 0xFE}:
                            yield {
                                "record": "dynamic",
                                "source": source,
                                "data": {
                                    "caller": source,
                                    "dex_entry": entry,
                                    "instruction_offset": address,
                                    "opcode": DYNAMIC_NAMES[op],
                                    "reason": "dynamic_target_not_resolved",
                                },
                            }
                yield {
                    "record": "method",
                    "source": source,
                    "instructions": count,
                    "without_code": int(not code),
                }
    yield {"record": "complete", "schema": 1, "edges": edges}


def split_types(value):
    position = 0
    while position < len(value):
        start = position
        while position < len(value) and value[position] == "[":
            position += 1
        if position == len(value):
            raise InvalidDex("Invalid descriptor")
        if value[position] == "L":
            end = value.find(";", position)
            if end < 0:
                raise InvalidDex("Invalid descriptor")
            position = end + 1
        else:
            if value[position] not in "ZBCSIJFD":
                raise InvalidDex("Invalid descriptor")
            position += 1
        yield value[start:position]


def catch_types(dex, code):
    count = dex.u16(code + 6)
    if not count:
        return
    units = dex.u32(code + 12)
    tries = code + 16 + 2 * (units + units % 2)
    dex.check(tries, count * 8)
    handlers = tries + count * 8
    size, position = dex.leb(handlers)
    decoded = {}
    for _ in range(size):
        offset = position - handlers
        number, position = signed_leb(dex, position)
        result = []
        for _ in range(abs(number)):
            typ, position = dex.leb(position)
            address, position = dex.leb(position)
            result.append((dex.type(typ), address))
        if number <= 0:
            _, position = dex.leb(position)
        decoded[offset] = result
    for index in range(count):
        offset = dex.u16(tries + index * 8 + 6)
        if offset not in decoded:
            raise InvalidDex("Invalid catch handler offset")
        yield from decoded[offset]


def signed_leb(dex, position):
    value = 0
    for shift in range(0, 35, 7):
        dex.check(position, 1)
        byte = dex.data[position]
        position += 1
        value |= (byte & 127) << shift
        if not byte & 128:
            if byte & 64:
                value -= 1 << (shift + 7)
            if not -(2**31) <= value < 2**31:
                raise InvalidDex("Invalid signed LEB128")
            return value, position
    raise InvalidDex("Invalid signed LEB128")


def build(settings, bundle, target, workspace, identity, calls_only=False):
    import json
    import os
    import sqlite3
    import zlib
    from contextlib import closing
    from functools import lru_cache

    from .xref_index import _pack_edge

    temporary = workspace / "native-index.partial.sqlite"
    with closing(sqlite3.connect(temporary)) as db:
        db.execute("PRAGMA page_size=4096")
        db.execute(f"PRAGMA max_page_count={max(1, settings.max_xref_index_bytes // 4096)}")
        db.execute("PRAGMA journal_mode=OFF")
        db.execute("PRAGMA synchronous=OFF")
        db.execute("PRAGMA temp_store=MEMORY")
        db.executescript("""
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE symbols (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
            CREATE TABLE definitions (kind TEXT, name INTEGER UNIQUE, entry TEXT,
                                      PRIMARY KEY(kind,name));
            CREATE TABLE edges (id INTEGER PRIMARY KEY, kind TEXT, target INTEGER,
                                source INTEGER, relation TEXT, data BLOB);
            CREATE TABLE methods (source INTEGER PRIMARY KEY, instructions INTEGER,
                                  without_code INTEGER);
            CREATE TABLE dynamic (id INTEGER PRIMARY KEY, source INTEGER, data BLOB);
        """)

        @lru_cache(maxsize=131072)
        def symbol(name):
            db.execute("INSERT OR IGNORE INTO symbols(name) VALUES (?)", (name,))
            return db.execute("SELECT id FROM symbols WHERE name=?", (name,)).fetchone()[0]

        complete = False
        edges = 0
        for row in records(bundle, calls_only):
            kind = row["record"]
            if kind == "definition":
                db.execute(
                    "INSERT INTO definitions VALUES (?,?,?)",
                    (row["kind"], symbol(row["descriptor"]), row["dex_entry"]),
                )
            elif kind == "edge":
                db.execute(
                    "INSERT INTO edges VALUES (NULL,?,?,?,?,?)",
                    (
                        row["kind"],
                        symbol(row["target"]),
                        symbol(row["source"]),
                        row["relation"],
                        _pack_edge(row["kind"], row["data"]),
                    ),
                )
                edges += 1
            elif kind == "method":
                db.execute(
                    "INSERT INTO methods VALUES (?,?,?)",
                    (symbol(row["source"]), row["instructions"], row["without_code"]),
                )
            elif kind == "dynamic":
                data = zlib.compress(
                    json.dumps(row["data"], separators=(",", ":")).encode(), level=1
                )
                db.execute("INSERT INTO dynamic VALUES (NULL,?,?)", (symbol(row["source"]), data))
            elif kind == "complete":
                complete = row["schema"] == 1 and row["edges"] == edges
            else:
                raise InvalidDex("Unknown native index record")
        if not complete:
            raise InvalidDex("Incomplete native index")
        symbol.cache_clear()
        db.executemany("INSERT INTO metadata VALUES (?,?)", identity.items())
        db.execute("CREATE INDEX incoming ON edges(kind,target,relation)")
        db.execute("CREATE INDEX outgoing ON edges(kind,source)")
        db.execute("CREATE INDEX dynamic_source ON dynamic(source)")
        db.commit()
    if temporary.stat().st_size > settings.max_xref_index_bytes:
        raise InvalidDex("Index exceeds configured disk budget")
    os.replace(temporary, target)
