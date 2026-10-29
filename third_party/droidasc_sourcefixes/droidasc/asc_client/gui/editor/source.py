_IDENT_START_EXTRA = "_$"
_IDENT_EXTRA = "_$"
_BLOCK_PREFIXES = (
    "if ", "if(", "for ", "for(", "while ", "while(", "switch ", "switch(",
    "catch ", "catch(", "else", "try", "do",
)
_JAVA_KEYWORDS = {
    "abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class",
    "const", "continue", "default", "do", "double", "else", "enum", "extends", "final",
    "finally", "float", "for", "goto", "if", "implements", "import", "instanceof", "int",
    "interface", "long", "native", "new", "package", "private", "protected", "public",
    "return", "short", "static", "strictfp", "super", "switch", "synchronized", "this",
    "throw", "throws", "transient", "try", "void", "volatile", "while", "true", "false",
    "null",
}


def _is_ident_start(ch : str):
    return ch.isalpha() or ch in _IDENT_START_EXTRA


def _is_ident(ch : str):
    return ch.isalnum() or ch in _IDENT_EXTRA


def _iter_java_code(text : str, start : int = 0, end = None):
    # Yield identifiers and structural symbols only. Rename/brace matching must
    # never treat text inside comments or literals as executable Java.
    if end is None:
        end = len(text)
    i = start
    while i < end:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < end else ""
        if ch == "/" and nxt == "/":
            newline = text.find("\n", i + 2, end)
            i = end if newline < 0 else newline + 1
            continue
        if ch == "/" and nxt == "*":
            close = text.find("*/", i + 2, end)
            i = end if close < 0 else close + 2
            continue
        if ch in "\"'":
            quote = ch
            i += 1
            while i < end:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                i += 1
            continue
        if _is_ident_start(ch):
            token_start = i
            i += 1
            while i < end and _is_ident(text[i]):
                i += 1
            yield "identifier", token_start, i
            continue
        yield "symbol", i, i + 1
        i += 1


def java_highlight_spans(text : str):
    # Highlighting needs the ranges which _iter_java_code deliberately skips,
    # so it uses a separate single-pass scanner with the same escape rules.
    spans = {
        "java_keyword": [],
        "java_comment": [],
        "java_string": [],
        "java_annotation": [],
    }
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        if ch == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                start = i
                i += 2
                while i < n and text[i] != "\n":
                    i += 1
                spans["java_comment"].append((start, i))
                continue
            if nxt == "*":
                start = i
                i += 2
                while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                    i += 1
                i = min(i + 2, n)
                spans["java_comment"].append((start, i))
                continue
        if ch in "\"'":
            quote = ch
            start = i
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == quote:
                    i += 1
                    break
                i += 1
            spans["java_string"].append((start, i))
            continue
        if ch == "@":
            start = i
            i += 1
            while i < n and (text[i].isalnum() or text[i] in "._$"):
                i += 1
            spans["java_annotation"].append((start, i))
            continue
        if ch.isalpha() or ch == "_":
            start = i
            i += 1
            while i < n and (text[i].isalnum() or text[i] in "_$"):
                i += 1
            if text[start:i] in _JAVA_KEYWORDS:
                spans["java_keyword"].append((start, i))
            continue
        i += 1
    return spans


def offset_spans_to_indexes(text : str, spans):
    # Tk indexes are line.column strings. Build newline offsets once, then map
    # every highlight endpoint with binary search instead of rescanning text.
    line_starts = [0]
    pos = 0
    while True:
        pos = text.find("\n", pos)
        if pos < 0:
            break
        pos += 1
        line_starts.append(pos)

    def to_index(offset : int):
        left = 0
        right = len(line_starts)
        while left < right:
            mid = (left + right) >> 1
            if line_starts[mid] <= offset:
                left = mid + 1
            else:
                right = mid
        line_idx = left - 1
        return f"{line_idx + 1}.{offset - line_starts[line_idx]}"

    return {
        tag_name: [(to_index(start), to_index(end)) for start, end in tag_spans]
        for tag_name, tag_spans in spans.items()
    }


def index_to_offset(text : str, index : str):
    line_s, col_s = str(index).split(".", 1)
    line_no = int(line_s)
    col = int(col_s)
    if line_no <= 1:
        return min(col, len(text))
    off = 0
    cur_line = 1
    while cur_line < line_no and off < len(text):
        nl = text.find("\n", off)
        if nl < 0:
            return len(text)
        off = nl + 1
        cur_line += 1
    return min(off + col, len(text))


def token_at_offset(text : str, offset : int):
    if not text:
        return None
    offset = max(0, min(offset, len(text) - 1))
    if not _is_ident(text[offset]):
        # Tk places the cursor after the clicked character at token boundaries.
        # Accept that trailing edge, but never cross arbitrary punctuation.
        if offset > 0 and _is_ident(text[offset - 1]):
            offset -= 1
        else:
            return None
    start = offset
    while start > 0 and _is_ident(text[start - 1]):
        start -= 1
    end = offset + 1
    while end < len(text) and _is_ident(text[end]):
        end += 1
    token = text[start:end]
    if not token or not _is_ident_start(token[0]):
        return None
    return start, end, token


def is_identifier(text : str):
    if not text or not _is_ident_start(text[0]):
        return False
    return all(_is_ident(ch) for ch in text[1:])


def find_method_range(text : str, offset : int):
    offset = max(0, min(offset, len(text)))
    # Decompiled Java commonly puts "{" on the next line. Check the current
    # signature first, then walk outward through enclosing braces.
    signature_range = _method_range_from_signature_line(text, offset)
    if signature_range is not None:
        return signature_range

    brace = text.rfind("{", 0, offset + 1)
    while brace >= 0:
        line_start, prefix = _prefix_before_brace(text, brace)
        if _looks_like_method_prefix(prefix):
            end = _matching_brace(text, brace)
            if end is not None and brace <= offset <= end:
                return line_start, end + 1
        brace = text.rfind("{", 0, brace)
    return None


def _prefix_before_brace(text : str, brace : int):
    line_start = text.rfind("\n", 0, brace) + 1
    prefix = text[line_start:brace].strip()
    if prefix:
        return line_start, prefix

    prev_end = line_start - 1
    if prev_end < 0 or text[prev_end:prev_end + 1] != "\n":
        return line_start, prefix
    prev_start = text.rfind("\n", 0, prev_end) + 1
    return prev_start, text[prev_start:prev_end].strip()


def _method_range_from_signature_line(text : str, offset : int):
    line_start = text.rfind("\n", 0, offset) + 1
    line_end_pos = text.find("\n", offset)
    if line_end_pos < 0:
        line_end_pos = len(text)
    current_line = text[line_start:line_end_pos]
    if "(" not in current_line or ")" not in current_line:
        return None

    search_end = min(len(text), line_end_pos + 1)
    open_brace = text.find("{", line_start, search_end)
    if open_brace < 0:
        # Dadguard formats some declarations as a signature line followed by a
        # line containing only "{". Do not accept other intervening text.
        next_line_end = text.find("\n", line_end_pos + 1)
        if next_line_end < 0:
            next_line_end = len(text)
        between = text[line_end_pos + 1:next_line_end].strip()
        if between != "{":
            return None
        open_brace = text.find("{", line_end_pos + 1, next_line_end + 1)

    prefix = text[line_start:open_brace].strip()
    if not _looks_like_method_prefix(prefix):
        return None
    end = _matching_brace(text, open_brace)
    if end is None:
        return None
    return line_start, end + 1


def _looks_like_method_prefix(prefix : str):
    if not prefix or prefix.startswith(_BLOCK_PREFIXES):
        return False
    if "(" not in prefix or ")" not in prefix:
        return False
    if prefix.endswith(("=", ".", ",")):
        return False
    return True


def _matching_brace(text : str, open_pos : int):
    depth = 0
    # Reuse the lexical scanner so braces in strings and comments do not close
    # the method early.
    for kind, start, _end in _iter_java_code(text, open_pos):
        if kind != "symbol":
            continue
        if text[start] == "{":
            depth += 1
        elif text[start] == "}":
            depth -= 1
            if depth == 0:
                return start
    return None


def _identifier_spans(text : str, start : int, end : int, name : str):
    return [
        (token_start, token_end)
        for kind, token_start, token_end in _iter_java_code(text, start, end)
        if kind == "identifier" and text[token_start:token_end] == name
    ]


def rename_identifier_in_range(
    text : str, start : int, end : int, old : str, new : str,
):
    spans = _identifier_spans(text, start, end, old)
    if not spans:
        return text, 0

    # Rebuild once from left to right; repeated str.replace would also modify
    # comments, literals, larger identifiers, and text outside the method.
    out = [text[:start]]
    last = start
    for token_start, token_end in spans:
        out.append(text[last:token_start])
        out.append(new)
        last = token_end
    out.append(text[last:])
    return "".join(out), len(spans)


def remap_ranges_after_replacements(ranges, spans, replacement_length : int):
    def remap(point):
        shift = 0
        # Spans are sorted. A point shifts only for replacements ending before
        # it; points inside the current replaced token keep their local range.
        for start, end in spans:
            if point < end:
                break
            shift += replacement_length - (end - start)
        return point + shift

    return [
        (remap(item[0]), remap(item[1]), *item[2:])
        for item in ranges
    ]


def member_reference_at_offset(references, offset : int):
    return next(
        (item for item in references if item[0] <= offset < item[1]),
        None,
    )


def find_member_declaration(
    references, member_type : str, member_name : str, descriptor : str,
):
    declarations = [
        item for item in references
        if item[2] == member_type and item[4] == member_name and item[6]
    ]
    exact = next(
        (item for item in declarations if item[5] == descriptor),
        None,
    )
    if exact is not None:
        return exact
    if not descriptor and declarations:
        return declarations[0]
    return None


def find_search_reference(
    source : str, references, method_name : str, method_descriptor : str,
    target_type : str, target_class : str, target_name : str,
    target_descriptor : str, occurrence : int = 0,
):
    declaration = find_member_declaration(
        references,
        "method",
        method_name,
        method_descriptor,
    )
    if declaration is None:
        declaration = find_member_declaration(
            references,
            "method",
            method_name,
            "",
        )
    if declaration is None:
        return None
    method_range = find_method_range(source, declaration[0])
    if method_range is None:
        return None

    def matches(item):
        # Search rows identify the containing method plus an occurrence number.
        # Filter metadata inside that exact method before applying occurrence.
        if not (method_range[0] <= item[0] < method_range[1]) or item[6]:
            return False
        if item[2] != target_type:
            return False
        if target_type == "string":
            return item[4] == target_name
        if target_type == "class":
            return item[3] == target_class
        return (
            item[3] == target_class
            and item[4] == target_name
            and (not target_descriptor or item[5] == target_descriptor)
        )

    matches_in_method = [item for item in references if matches(item)]
    if occurrence < 0 or occurrence >= len(matches_in_method):
        return None
    return matches_in_method[occurrence]


def linkable_member_spans(references, available_classes):
    return [
        (item[0], item[1])
        for item in references
        if item[3] in available_classes
    ]


def identifier_occurrences_in_range(
    text : str, start : int, end : int, name : str,
):
    return _identifier_spans(text, start, end, name)


def decode_java_unicode_escapes(text : str):
    if "\\u" not in text:
        return text

    out = []
    pending_high = None
    pending_high_raw = None
    i = 0
    n = len(text)
    # Java accepts repeated "u" markers and encodes non-BMP characters as two
    # UTF-16 escapes. Preserve malformed/replacement escapes verbatim.
    while i < n:
        ch = text[i]
        if ch != "\\" or i + 1 >= n or text[i + 1] != "u":
            if pending_high is not None:
                out.append(pending_high_raw)
                pending_high = None
                pending_high_raw = None
            out.append(ch)
            i += 1
            continue

        escape_start = i
        j = i + 1
        while j < n and text[j] == "u":
            j += 1
        if j + 4 > n:
            if pending_high is not None:
                out.append(pending_high_raw)
                pending_high = None
                pending_high_raw = None
            out.append(ch)
            i += 1
            continue

        hex_part = text[j:j + 4]
        try:
            code_unit = int(hex_part, 16)
        except ValueError:
            if pending_high is not None:
                out.append(pending_high_raw)
                pending_high = None
                pending_high_raw = None
            out.append(ch)
            i += 1
            continue

        i = j + 4
        raw_escape = text[escape_start:i]
        if code_unit == 0xFFFD:
            if pending_high is not None:
                out.append(pending_high_raw)
                pending_high = None
                pending_high_raw = None
            out.append(raw_escape)
            continue
        if 0xD800 <= code_unit <= 0xDBFF:
            if pending_high is not None:
                out.append(pending_high_raw)
            pending_high = code_unit
            pending_high_raw = raw_escape
            continue

        if pending_high is not None:
            if 0xDC00 <= code_unit <= 0xDFFF:
                code_point = (
                    0x10000
                    + ((pending_high - 0xD800) << 10)
                    + (code_unit - 0xDC00)
                )
                out.append(chr(code_point))
                pending_high = None
                pending_high_raw = None
                continue
            out.append(pending_high_raw)
            pending_high = None
            pending_high_raw = None

        if 0xDC00 <= code_unit <= 0xDFFF:
            out.append(raw_escape)
            continue
        out.append(chr(code_unit))

    if pending_high is not None:
        out.append(pending_high_raw)
    return "".join(out)


def decode_java_unicode_escapes_with_ranges(text : str, ranges):
    if not ranges or "\\u" not in text:
        return decode_java_unicode_escapes(text), list(ranges)

    # Decode only prefixes ending at metadata boundaries to build an old->new
    # offset map without allocating a mapping entry for every source character.
    points = sorted({point for item in ranges for point in item[:2]})
    mapped = {}
    source_pos = 0
    decoded_pos = 0
    for point in points:
        decoded_pos += len(decode_java_unicode_escapes(text[source_pos:point]))
        mapped[point] = decoded_pos
        source_pos = point

    decoded = decode_java_unicode_escapes(text)
    adjusted = [
        (mapped[item[0]], mapped[item[1]], *item[2:])
        for item in ranges
    ]
    return decoded, adjusted
