"""Independent byte-level DEX 041 oracle with physical offsets in both logical files."""

import hashlib
import struct
import zlib


def dex041_container(names=("A", "B"), *, shared_strings=False, references=False):
    data = bytearray()
    headers = []
    for name in names:
        start = len(data)
        data.extend(bytes(120))
        strings = sorted(
            [
                f"Loracle/{name};",
                "Ljava/lang/Object;",
                "Ljava/lang/String;",
                "L",
                "hello",
                f"value-{name}",
            ]
            + (["field"] if references else [])
        )
        types = sorted(
            [
                strings.index(s)
                for s in (f"Loracle/{name};", "Ljava/lang/Object;", "Ljava/lang/String;")
            ]
        )

        def type_index(value, types=types, strings=strings):
            return types.index(strings.index(value))

        strings_off = len(data)
        data.extend(bytes(4 * len(strings)))
        types_off = len(data)
        data.extend(struct.pack("<3I", *types))
        proto_off = len(data)
        data.extend(struct.pack("<3I", strings.index("L"), type_index("Ljava/lang/String;"), 0))
        fields_off = len(data) if references else 0
        if references:
            data.extend(
                struct.pack(
                    "<HHI",
                    type_index(f"Loracle/{name};"),
                    type_index("Ljava/lang/String;"),
                    strings.index("field"),
                )
            )
        methods_off = len(data)
        data.extend(struct.pack("<HHI", type_index(f"Loracle/{name};"), 0, strings.index("hello")))
        classes_off = len(data)
        data.extend(bytes(32))
        code_off = len(data)
        code = [0x001A, strings.index(f"value-{name}")]
        if references:
            code += [0x011C, type_index("Ljava/lang/Object;"), 0x0162, 0, 0x0071, 0, 0]
        code += [0x0011]
        data.extend(struct.pack("<HHHHII", 2 if references else 1, 0, 0, 0, 0, len(code)))
        data.extend(struct.pack(f"<{len(code)}H", *code))
        data.extend(bytes((-len(data)) % 4))
        class_data_off = len(data)
        encoded = []
        value = code_off
        while value >= 128:
            encoded.append((value & 127) | 128)
            value >>= 7
        encoded.append(value)
        data.extend(
            bytes(
                [1, 0, 1, 0, 0, 9, 0, 9, *encoded] if references else [0, 0, 1, 0, 0, 9, *encoded]
            )
        )
        string_data_off = len(data)
        for index, text in enumerate(strings):
            struct.pack_into("<I", data, strings_off + index * 4, len(data))
            data.extend(bytes([len(text)]) + text.encode() + b"\0")
        data.extend(bytes((-len(data)) % 4))
        map_off = len(data)
        sections = [
            (0, 1, start),
            (1, 6, strings_off),
            (2, 3, types_off),
            (3, 1, proto_off),
            (5, 1, methods_off),
            (6, 1, classes_off),
            (0x2001, 1, code_off),
            (0x2000, 1, class_data_off),
            (0x2002, 6, string_data_off),
            (0x1000, 1, map_off),
        ]
        if references:
            sections.insert(4, (4, 1, fields_off))
            sections = [
                (kind, len(strings) if kind in (1, 0x2002) else count, offset)
                for kind, count, offset in sections
            ]
        data.extend(struct.pack("<I", len(sections)))
        for kind, count, offset in sections:
            data.extend(struct.pack("<HHII", kind, 0, count, offset))
        data[start : start + 8] = b"dex\n041\0"
        struct.pack_into("<5I", data, start + 32, len(data) - start, 120, 0x12345678, 0, 0)
        struct.pack_into("<I", data, start + 52, map_off)
        for field, count, offset in (
            (56, len(strings), strings_off),
            (64, 3, types_off),
            (72, 1, proto_off),
            (88, 1, methods_off),
            (96, 1, classes_off),
        ):
            struct.pack_into("<II", data, start + field, count, offset)
        if references:
            struct.pack_into("<II", data, start + 80, 1, fields_off)
        struct.pack_into(
            "<8I",
            data,
            classes_off,
            type_index(f"Loracle/{name};"),
            1,
            type_index("Ljava/lang/Object;"),
            0,
            0xFFFFFFFF,
            0,
            class_data_off,
            0,
        )
        headers.append(start)
    if shared_strings and len(headers) == 2:
        first, second = headers
        first_table = struct.unpack_from("<I", data, first + 60)[0]
        second_table = struct.unpack_from("<I", data, second + 60)[0]
        # These three entries are identical in the independently sorted pools.
        for index in (0, 1, 2):
            data[second_table + index * 4 : second_table + (index + 1) * 4] = data[
                first_table + index * 4 : first_table + (index + 1) * 4
            ]
    for start in headers:
        size = struct.unpack_from("<I", data, start + 32)[0]
        struct.pack_into("<II", data, start + 112, len(data), start)
        data[start + 12 : start + 32] = hashlib.sha1(data[start + 32 : start + size]).digest()
        struct.pack_into("<I", data, start + 8, zlib.adler32(data[start + 12 : start + size]))
    return bytes(data)
