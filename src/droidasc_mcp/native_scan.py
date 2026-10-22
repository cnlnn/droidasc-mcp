"""C-regex token runs with exact DEX boundaries, not heuristic byte hits.

Every byte of a code item must be covered by a valid instruction or a checked
payload. The simple cursor remains an independent differential-test path.
"""

import re
import struct

from .native_dex import METHOD_NAMES, WIDTHS, InvalidDex

ANY = b"[\\s\\S]"


def alternatives(values):
    return b"(?:" + b"|".join(re.escape(value) for value in values) + b")"


def pool_ids(count):
    """Little-endian 16-bit operands strictly below a pool's size."""
    if count >= 65536:
        return ANY + b"{2}"
    high, low = divmod(count, 256)
    choices = []
    if high:
        choices.append(ANY + b"[" + re.escape(bytes(range(high))) + b"]")
    if low:
        choices.append(b"[" + re.escape(bytes(range(low))) + b"]" + re.escape(bytes([high])))
    return b"(?:" + b"|".join(choices) + b")" if choices else b"(?!)"


def method_selector(dex, targets, fields, access):
    try:
        from ._dexscan import select_methods as native_select
    except ImportError:
        return None
    mask = bytearray(65536)
    for index in targets:
        mask[index] = 1
    mask = bytes(mask)

    def select(methods):
        try:
            return native_select(
                dex.data,
                methods,
                dex.version,
                WIDTHS,
                mask,
                int(fields),
                dex.tables[3 if fields else 4][0],
                dex.tables[4][1],
                dex.tables[0][0],
                dex.tables[2][0],
                {"all": 0, "read": 1, "write": 2}[access],
            )
        except ValueError as exc:
            raise InvalidDex(str(exc)) from exc

    return select


def class_selector(dex, targets, fields, access, *, callers=None):
    try:
        from . import _dexscan
    except ImportError:
        return None
    mask = bytearray(65536)
    for index in targets:
        mask[index] = 1
    mask = bytes(mask)
    arguments = (
        dex.version,
        WIDTHS,
        mask,
        int(fields),
        dex.tables[3][0],
        dex.tables[4][0],
        dex.tables[4][1],
        dex.tables[0][0],
        dex.tables[2][0],
        {"all": 0, "read": 1, "write": 2}[access],
    )
    if callers is not None:
        caller_mask = bytearray(65536)
        for index in callers:
            caller_mask[index] = 1
        arguments += (bytes(caller_mask),)

    def select(cls):
        try:
            return _dexscan.select_class(dex.data, cls, *arguments)
        except ValueError as exc:
            raise InvalidDex(str(exc)) from exc

    if hasattr(_dexscan, "select_classes"):

        def directory(classes):
            try:
                return _dexscan.select_classes(dex.data, classes, *arguments)
            except ValueError as exc:
                raise InvalidDex(str(exc)) from exc

        select.directory = directory

    return select


def select_directory(dex, select):
    from .native_dex import utf16_key

    if (bulk := getattr(select, "directory", None)) is not None:
        selected, *metrics = bulk(dex.classes(ordered=False))
        selected.sort(key=lambda row: utf16_key(row[0]))
        return selected, *metrics
    selected, declared = [], []
    methods = instructions = dynamic = without = 0
    for owner, cls in dex.classes(ordered=False):
        matches, definitions, count, decoded, unresolved, absent = select(cls)
        methods += count
        instructions += decoded
        dynamic += unresolved
        without += absent
        declared.extend(definitions)
        if matches:
            selected.append((owner, matches))
    selected.sort(key=lambda row: utf16_key(row[0]))
    return selected, declared, methods, instructions, dynamic, without


def scanner(dex, targets, fields, incoming, *, accelerator=True):
    if accelerator:
        try:
            from ._dexscan import scan as native_scan
        except ImportError:
            pass
        else:
            mask = bytearray(65536)
            for index in targets:
                if not 0 <= index < 65536:
                    raise InvalidDex("DEX reference index exceeds 16 bits")
                mask[index] = 1
            mask = bytes(mask)
            pool = dex.tables[3 if fields else 4][0]

            def accelerated(code):
                resume = 0
                while True:
                    try:
                        rows = native_scan(
                            dex.data,
                            code,
                            dex.version,
                            WIDTHS,
                            mask,
                            int(fields),
                            int(incoming),
                            pool,
                            resume,
                        )
                    except ValueError as exc:
                        raise InvalidDex(str(exc)) from exc
                    if rows and rows[-1][2] == -2:
                        resume = rows[-1][0]
                        yield from rows[:-1]
                    else:
                        yield from rows
                        return

            return accelerated
    widths = bytearray(WIDTHS)
    if dex.version < 38:
        widths[0xFA:] = bytes(6)
    elif dex.version < 39:
        widths[0xFE:] = bytes(2)
    tokens = [b"\\x00\\x00"]
    reference_ops = set(range(0x52, 0x6E) if fields else METHOD_NAMES)
    valid_ids = pool_ids(dex.tables[3 if fields else 4][0])
    for width in range(1, 6):
        opcodes = [
            bytes([op]) for op in range(1, 256) if widths[op] == width and op not in reference_ops
        ]
        if opcodes:
            tokens.append(alternatives(opcodes) + ANY + b"{%d}" % (width * 2 - 1))
        opcodes = [bytes([op]) for op in sorted(reference_ops) if widths[op] == width]
        if opcodes:
            tokens.append(alternatives(opcodes) + ANY + valid_ids + ANY + b"{%d}" % (width * 2 - 4))
    token = b"(?:" + b"|".join(tokens) + b")"
    count = re.compile(token)
    special = [b"\\x00[\\x01-\\x03]"]
    if targets or not incoming:
        ids = (
            alternatives([struct.pack("<H", index) for index in sorted(targets)])
            if incoming and len(targets) <= 64
            else ANY + b"{2}"
        )
        for width in (2, 3, 4):
            opcodes = [bytes([op]) for op in reference_ops if widths[op] == width]
            if opcodes:
                special.append(alternatives(opcodes) + ANY + ids + ANY + b"{%d}" % (width * 2 - 4))
    for width in (2, 3, 4):
        dynamic = [bytes([op]) for op in (0xFA, 0xFB, 0xFC, 0xFD, 0xFE) if widths[op] == width]
        if dynamic:
            special.append(alternatives(dynamic) + ANY + b"{%d}" % (width * 2 - 1))
    special = b"(?:" + b"|".join(special) + b")"
    candidates = re.compile(special)
    runs = re.compile(
        b"(?:(?!" + special + b")" + token + b")*" + b"(?:(?P<special>" + special + b")|(?P<end>$))"
    )

    def scan(code):
        dex.check(code, 16)
        if code % 4:
            raise InvalidDex("Unaligned DEX code item")
        data = dex.data
        start = code + 16
        end = start + dex.u32(code + 12) * 2
        dex.check(start, end - start)
        if candidates.search(data, start, end) is None:
            remainder, skipped = count.subn(b"", data[start:end])
            if remainder:
                raise InvalidDex("Unknown, optimized or truncated DEX instruction")
            yield end, (end - start) // 2, -1, skipped
            return
        position = start
        while position < end:
            match = runs.match(data, position, end)
            if match is None:
                raise InvalidDex("Unknown, optimized or truncated DEX instruction")
            stop = match.start("special") if match.group("special") is not None else end
            remainder, skipped = count.subn(b"", data[position:stop])
            if remainder:
                raise InvalidDex("Incomplete DEX instruction token run")
            if stop == end:
                yield end, (end - start) // 2, -1, skipped
                return
            op = data[stop]
            following = match.end()
            if op == 0:
                kind = data[stop + 1]
                header = 8 if kind == 3 else 4
                if stop % 4 or stop + header > end:
                    raise InvalidDex("Invalid or truncated DEX payload header")
                size = dex.u16(stop + 2)
                if kind == 1:
                    units = 4 + 2 * size
                elif kind == 2:
                    units = 2 + 4 * size
                else:
                    if size not in {1, 2, 4, 8}:
                        raise InvalidDex("Invalid DEX array element width")
                    units = 4 + (size * dex.u32(stop + 4) + 1) // 2
                following = stop + units * 2
                if following > end:
                    raise InvalidDex("Truncated or oversized DEX payload")
            yield stop, (stop - start) // 2, op, skipped + 1
            position = following

    return scan
