"""Lightweight DEX disassembly and smali rendering.

The renderer deliberately depends on dadguard's DEX parser only. It does not
load the Java decompiler or the analysis graph, which keeps the APK extraction
path small and usable in installations without optional UI dependencies.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict

from dadguard.core.dex import (
    DBG_ADVANCE_LINE,
    DBG_ADVANCE_PC,
    DBG_END_LOCAL,
    DBG_LINE_BASE,
    DBG_LINE_RANGE,
    DBG_RESTART_LOCAL,
    DBG_SET_EPILOGUE_BEGIN,
    DBG_SET_FILE,
    DBG_SET_PROLOGUE_END,
    DBG_START_LOCAL,
    DBG_START_LOCAL_EXTENDED,
    DEX,
    DebugInfoItem,
    VALUE_ANNOTATION,
    VALUE_ARRAY,
    VALUE_BOOLEAN,
    VALUE_BYTE,
    VALUE_CHAR,
    VALUE_DOUBLE,
    VALUE_ENUM,
    VALUE_FIELD,
    VALUE_FLOAT,
    VALUE_INT,
    VALUE_LONG,
    VALUE_METHOD,
    VALUE_NULL,
    VALUE_SHORT,
    VALUE_STRING,
    VALUE_TYPE,
)


_NO_INDEX = 0xFFFFFFFF
_ANNOTATION_VISIBILITY = {
    0: "build",
    1: "runtime",
    2: "system",
}
_BRANCH_OFFSET_RE = re.compile(r"([+-]?[0-9a-fA-F]+)h$")


def _format_instruction(index: int, offset: int, instruction) -> str:
    """Format one instruction like Androguard's offset disassembly command."""
    return "{:<8d}({:08x}) {} {}".format(
        index,
        offset,
        instruction.get_name(),
        instruction.get_output(offset),
    ).rstrip()


def _safe_string(cm, index: int):
    if index is None or index < 0 or index == _NO_INDEX:
        return None
    try:
        return cm.get_string(index)
    except (IndexError, KeyError, TypeError):
        return None


def _safe_type(cm, index: int):
    if index is None or index < 0 or index == _NO_INDEX:
        return None
    try:
        return cm.get_type(index)
    except (IndexError, KeyError, TypeError):
        return None


def _quote(value) -> str:
    return json.dumps(str(value), ensure_ascii=True)


def _compact_descriptor(descriptor) -> str:
    return "".join(str(descriptor).split())


def _normalize_method_signature(signature: str) -> str:
    if not signature or "(" not in signature or ")" not in signature:
        raise ValueError(
            "method signature must include the name, parameter descriptor and return type"
        )
    name, rest = signature.split("(", 1)
    params, return_type = rest.split(")", 1)
    if not name or not return_type:
        raise ValueError(
            "method signature must include the name, parameter descriptor and return type"
        )
    return "{}({}){}".format(
        name,
        _compact_descriptor(params),
        _compact_descriptor(return_type),
    )


def _method_matches(method, signature: str) -> bool:
    return "{}{}".format(
        method.get_name(),
        _compact_descriptor(method.get_descriptor()),
    ) == signature


def _format_reference(value) -> str:
    """Render a field/method reference stored inside an encoded value."""
    try:
        owner = value.get_class_name()
        name = value.get_name()
        descriptor = _compact_descriptor(value.get_descriptor())
        if descriptor.startswith("("):
            return "{}->{}{}".format(owner, name, descriptor)
        return "{}->{}:{}".format(owner, name, descriptor)
    except (AttributeError, IndexError, KeyError, TypeError):
        return str(value)


def _format_encoded_value(encoded_value, cm) -> str:
    value_type = encoded_value.get_value_type()
    value = encoded_value.get_value()

    if value_type == VALUE_STRING:
        return _quote(value)
    if value_type == VALUE_TYPE:
        return str(value)
    if value_type in (VALUE_FIELD, VALUE_METHOD, VALUE_ENUM):
        return _format_reference(value)
    if value_type == VALUE_BOOLEAN:
        return "true" if value else "false"
    if value_type == VALUE_NULL:
        return "null"
    if value_type == VALUE_ARRAY:
        values = getattr(value, "get_values", lambda: [])()
        return "{{{}}}".format(
            ", ".join(_format_encoded_value(item, cm) for item in values)
        )
    if value_type == VALUE_ANNOTATION:
        annotation_type = _safe_type(cm, value.get_type_idx())
        elements = []
        for element in value.get_elements():
            name = _safe_string(cm, element.get_name_idx())
            if name is None:
                name = "unknown"
            elements.append(
                "{} = {}".format(
                    name,
                    _format_encoded_value(element.get_value(), cm),
                )
            )
        return "{} {{{}}}".format(
            annotation_type or "Lunknown/Annotation;",
            ", ".join(elements),
        )
    if value_type in (
        VALUE_BYTE,
        VALUE_SHORT,
        VALUE_CHAR,
        VALUE_INT,
        VALUE_LONG,
        VALUE_FLOAT,
        VALUE_DOUBLE,
    ):
        if isinstance(value, int) and value >= 0:
            return "0x{:x}".format(value)
        return str(value)
    return str(value)


def _annotation_items(cm, annotations_off: int):
    if not annotations_off:
        return []
    try:
        annotation_set = cm.get_annotation_set_item(annotations_off)
        if annotation_set is None:
            return []
        result = []
        for annotation_off in annotation_set.get_annotation_off_item():
            item = annotation_off.get_annotation_item()
            if item is not None:
                result.append(item)
        return result
    except (AttributeError, IndexError, KeyError, TypeError):
        return []


def _annotation_lines(cm, annotation_items, indent: str = "    ") -> list[str]:
    lines = []
    for item in annotation_items:
        annotation = item.get_annotation()
        annotation_type = _safe_type(cm, annotation.get_type_idx())
        if annotation_type is None:
            annotation_type = "Lunknown/Annotation;"
        visibility = _ANNOTATION_VISIBILITY.get(item.get_visibility(), "runtime")
        lines.append("{}.annotation {} {}".format(indent, visibility, annotation_type))
        for element in annotation.get_elements():
            name = _safe_string(cm, element.get_name_idx()) or "unknown"
            lines.append(
                "{}    {} = {}".format(
                    indent,
                    name,
                    _format_encoded_value(element.get_value(), cm),
                )
            )
        lines.append("{}.end annotation".format(indent))
    return lines


def _annotation_data(cls):
    """Load annotation directory data only for the class being rendered."""
    directory = getattr(cls, "annotations_directory_item", None)
    if directory is None and cls.get_annotations_off():
        try:
            directory = cls.CM.get_annotations_directory_item(
                cls.get_annotations_off()
            )
            cls.annotations_directory_item = directory
        except (AttributeError, IndexError, KeyError, TypeError):
            directory = None

    data = {
        "class": [],
        "fields": defaultdict(list),
        "methods": defaultdict(list),
        "parameters": {},
    }
    if directory is None:
        return data

    data["class"] = _annotation_items(
        cls.CM, directory.get_class_annotations_off()
    )
    for item in directory.get_field_annotations():
        data["fields"][item.get_field_idx()] = _annotation_items(
            cls.CM, item.get_annotations_off()
        )
    for item in directory.get_method_annotations():
        data["methods"][item.get_method_idx()] = _annotation_items(
            cls.CM, item.get_annotations_off()
        )
    for item in directory.get_parameter_annotations():
        data["parameters"][item.get_method_idx()] = item.get_annotations_off()
    return data


def _parameter_annotation_lines(cm, annotations_off: int) -> list[str]:
    if not annotations_off:
        return []
    try:
        ref_list = cm.get_obj_by_offset(annotations_off)
        refs = ref_list.get_list()
    except (AttributeError, IndexError, KeyError, TypeError):
        return []

    lines = []
    for parameter, ref in enumerate(refs):
        items = _annotation_items(cm, ref.get_annotations_off())
        if not items:
            continue
        lines.append("    .param p{}".format(parameter))
        lines.extend(_annotation_lines(cm, items, "        "))
        lines.append("    .end param")
    return lines


def _debug_lines(method) -> dict[int, list[str]]:
    """Decode DEX debug opcodes into smali directives by code-unit address."""
    code = method.get_code()
    if code is None or not code.get_debug_info_off():
        return {}
    try:
        cm = method.CM
        try:
            debug = code.get_debug()
        except AttributeError:
            # dadguard's ClassManager keeps the DEX object in ``buff`` while
            # the actual seekable stream is owned by DEX.raw.
            raw = getattr(getattr(cm, "vm", None), "raw", None)
            if raw is None:
                return {}
            current = raw.tell()
            try:
                raw.seek(code.get_debug_info_off())
                debug = DebugInfoItem(raw, cm)
            finally:
                raw.seek(current)
        address = 0
        line = debug.get_line_start()
        events = defaultdict(list)
        for bytecode in debug.get_bytecodes():
            op = bytecode.get_op_value()
            values = [value for value, _ in bytecode.format]
            if op == DBG_ADVANCE_PC:
                address += values[0]
            elif op == DBG_ADVANCE_LINE:
                line += values[0]
            elif op == DBG_START_LOCAL:
                register = values[0]
                name = _safe_string(cm, values[1])
                value_type = _safe_type(cm, values[2])
                directive = "    .local v{}".format(register)
                if name is not None:
                    directive += ", {}".format(_quote(name))
                if value_type is not None:
                    directive += ":{}".format(value_type)
                events[address * 2].append(directive)
            elif op == DBG_START_LOCAL_EXTENDED:
                register = values[0]
                name = _safe_string(cm, values[1])
                value_type = _safe_type(cm, values[2])
                signature = _safe_string(cm, values[3])
                directive = "    .local v{}".format(register)
                if name is not None:
                    directive += ", {}".format(_quote(name))
                if value_type is not None:
                    directive += ":{}".format(value_type)
                if signature is not None:
                    directive += "    # {}".format(signature)
                events[address * 2].append(directive)
            elif op == DBG_END_LOCAL:
                events[address * 2].append(
                    "    .end local v{}".format(values[0])
                )
            elif op == DBG_RESTART_LOCAL:
                events[address * 2].append(
                    "    .restart local v{}".format(values[0])
                )
            elif op in (
                DBG_SET_PROLOGUE_END,
                DBG_SET_EPILOGUE_BEGIN,
                DBG_SET_FILE,
            ):
                continue
            elif op >= 0x0A:
                adjusted = op - 0x0A
                address += adjusted // DBG_LINE_RANGE
                line += DBG_LINE_BASE + adjusted % DBG_LINE_RANGE
                events[address * 2].append("    .line {}".format(line))
        return events
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        # Optional debug metadata must not make otherwise valid bytecode
        # impossible to inspect.
        return {}


def _branch_target(offset: int, instruction):
    name = instruction.get_name()
    if not (
        name == "goto"
        or name.startswith("goto/")
        or name.startswith("if-")
        or name in ("packed-switch", "sparse-switch", "fill-array-data")
    ):
        return None
    get_ref_off = getattr(instruction, "get_ref_off", None)
    if get_ref_off is None:
        return None
    try:
        # Branch references are measured in 16-bit code units, while
        # get_instructions_idx() exposes byte offsets.
        return ((offset // 2) + get_ref_off()) * 2
    except (AttributeError, TypeError, ValueError):
        return None


def _label_name_for_branch(instruction, counters) -> str:
    name = instruction.get_name()
    if name == "goto" or name.startswith("goto/"):
        prefix = "goto"
    elif name.startswith("if-"):
        prefix = "cond"
    else:
        prefix = "label"
    value = counters[prefix]
    counters[prefix] += 1
    return "{}_{}".format(prefix, value)


def _replace_branch_operand(output: str, label: str) -> str:
    match = _BRANCH_OFFSET_RE.search(output)
    if match is None:
        return output
    return "{}:{}".format(output[: match.start()], label)


def _exception_data(method, instructions):
    code = method.get_code()
    if code is None or not code.get_tries_size():
        return {}, {}, {}

    labels = defaultdict(list)
    directives = defaultdict(list)
    handler_labels = {}
    try_items = []
    handlers = code.get_handlers()
    handler_by_offset = {}
    if handlers is not None:
        base = handlers.get_off()
        for handler in handlers.get_list():
            handler_by_offset[handler.get_off() - base] = handler

    for index, try_item in enumerate(code.get_tries()):
        start = try_item.get_start_addr() * 2
        end = (try_item.get_start_addr() + try_item.get_insn_count()) * 2
        start_label = "try_start_{}".format(index)
        end_label = "try_end_{}".format(index)
        labels[start].append(start_label)
        labels[end].append(end_label)
        handler = handler_by_offset.get(try_item.get_handler_off())
        if handler is None:
            continue

        catches = []
        for pair in handler.get_handlers():
            address = pair.get_addr() * 2
            if address not in handler_labels:
                handler_labels[address] = "catch_{}".format(len(handler_labels))
                labels[address].append(handler_labels[address])
            catches.append(
                (
                    ".catch",
                    _safe_type(method.CM, pair.get_type_idx())
                    or "Ljava/lang/Throwable;",
                    handler_labels[address],
                )
            )
        if handler.get_size() <= 0:
            address = handler.get_catch_all_addr() * 2
            if address not in handler_labels:
                handler_labels[address] = "catchall_{}".format(
                    len(handler_labels)
                )
                labels[address].append(handler_labels[address])
            catches.append((".catchall", None, handler_labels[address]))

        for directive, value, catch_label in catches:
            if directive == ".catch":
                directives[end].append(
                    "    {} {} {{:{} .. :{}}} :{}".format(
                        directive,
                        value,
                        start_label,
                        end_label,
                        catch_label,
                    )
                )
            else:
                directives[end].append(
                    "    {} {{:{} .. :{}}} :{}".format(
                        directive,
                        start_label,
                        end_label,
                        catch_label,
                    )
                )
        try_items.append((start, end))

    instruction_offsets = {offset for offset, _ in instructions}
    for start, end in try_items:
        if start not in instruction_offsets:
            labels[start].append("try_start_invalid_{:x}".format(start))
        if end not in instruction_offsets and end != instructions[-1][0] + instructions[-1][1].get_length():
            labels[end].append("try_end_invalid_{:x}".format(end))
    return labels, directives, handler_labels


def _smali_instructions(
    method,
    debug: bool = False,
    debuginfo: bool = False,
):
    instructions = list(method.get_instructions_idx())
    if not instructions:
        return []

    labels = defaultdict(list)
    branch_counters = defaultdict(int)
    for offset, instruction in instructions:
        target = _branch_target(offset, instruction)
        if target is not None and not labels[target]:
            labels[target].append(
                _label_name_for_branch(instruction, branch_counters)
            )

    exception_labels, exception_directives, _ = _exception_data(
        method, instructions
    )
    for offset, names in exception_labels.items():
        labels[offset].extend(name for name in names if name not in labels[offset])

    debug_events = _debug_lines(method) if debuginfo else {}
    lines = []
    for offset, instruction in instructions:
        regular_labels = [
            label
            for label in labels.get(offset, [])
            if not label.startswith("catch")
        ]
        catch_labels = [
            label
            for label in labels.get(offset, [])
            if label.startswith("catch")
        ]
        for label in regular_labels:
            lines.append("    :{}".format(label))
        lines.extend(exception_directives.get(offset, []))
        for label in catch_labels:
            lines.append("    :{}".format(label))
        lines.extend(debug_events.get(offset, []))
        output = instruction.get_output(offset)
        target = _branch_target(offset, instruction)
        if target is not None and labels.get(target):
            output = _replace_branch_operand(output, labels[target][0])
        if debug:
            lines.append(
                "    # {:08x}  {}".format(offset, instruction.disasm())
            )
        lines.append("    {} {}".format(instruction.get_name(), output).rstrip())

    end_offset = instructions[-1][0] + instructions[-1][1].get_length()
    regular_labels = [
        label
        for label in labels.get(end_offset, [])
        if not label.startswith("catch")
    ]
    catch_labels = [
        label
        for label in labels.get(end_offset, [])
        if label.startswith("catch")
    ]
    for label in regular_labels:
        lines.append("    :{}".format(label))
    lines.extend(exception_directives.get(end_offset, []))
    for label in catch_labels:
        lines.append("    :{}".format(label))
    return lines


def _format_field(cm, field, annotations) -> list[str]:
    lines = _annotation_lines(
        cm, annotations.get(field.get_field_idx(), []), "    "
    )
    flags = field.get_access_flags_string()
    prefix = ".field"
    if flags:
        prefix += " " + flags
    value = ""
    init_value = field.get_init_value()
    if init_value is not None:
        value = " = {}".format(_format_encoded_value(init_value, cm))
    lines.append(
        "    {} {}:{}{}".format(
            prefix,
            field.get_name(),
            field.get_descriptor(),
            value,
        )
    )
    return lines


def _format_method(
    cls,
    method,
    annotation_data,
    debug: bool = False,
    debuginfo: bool = False,
) -> list[str]:
    descriptor = _compact_descriptor(method.get_descriptor())
    lines = [
        "## METHOD: {} {} {}".format(
            method.get_access_flags_string(),
            method.get_name(),
            descriptor,
        )
    ]
    flags = method.get_access_flags_string()
    if method.get_name() in ("<init>", "<clinit>") and "constructor" not in flags:
        flags = "{} constructor".format(flags).strip()
    declaration = ".method"
    if flags:
        declaration += " " + flags
    declaration += " {}{}".format(method.get_name(), descriptor)
    lines.append(declaration)

    code = method.get_code()
    if code is not None:
        lines.append("    .locals {}".format(
            max(0, code.get_registers_size() - code.get_ins_size())
        ))
        lines.extend(
            _annotation_lines(
                cls.CM,
                annotation_data["methods"].get(method.get_method_idx(), []),
                "    ",
            )
        )
        lines.extend(
            _parameter_annotation_lines(
                cls.CM,
                annotation_data["parameters"].get(method.get_method_idx(), 0),
            )
        )
        lines.extend(
            _smali_instructions(
                method,
                debug=debug,
                debuginfo=debuginfo,
            )
        )
    else:
        lines.extend(
            _annotation_lines(
                cls.CM,
                annotation_data["methods"].get(method.get_method_idx(), []),
                "    ",
            )
        )
    lines.append(".end method")
    return lines


def _format_class(
    cls,
    debug: bool = False,
    debuginfo: bool = False,
    method_signature: str | None = None,
) -> list[str]:
    lines = ["# CLASS: {}".format(cls.get_name())]
    flags = cls.get_access_flags_string()
    declaration = ".class"
    if flags:
        declaration += " " + flags
    lines.append("{} {}".format(declaration, cls.get_name()))
    superclass = cls.get_superclassname()
    if superclass:
        lines.append(".super {}".format(superclass))
    source_idx = cls.get_source_file_idx()
    source = _safe_string(cls.CM, source_idx)
    if source is not None:
        lines.append(".source {}".format(_quote(source)))
    if cls.get_interfaces():
        lines.append("")
        lines.append("# interfaces")
        for interface in cls.get_interfaces():
            lines.append(".implements {}".format(interface))

    annotation_data = _annotation_data(cls)
    lines.extend(_annotation_lines(cls.CM, annotation_data["class"], ""))

    fields = cls.get_fields() if method_signature is None else []
    if fields:
        lines.append("")
        lines.append("# fields")
        for field in fields:
            lines.extend(_format_field(cls.CM, field, annotation_data["fields"]))

    methods = cls.get_methods()
    if method_signature is not None:
        methods = [
            method for method in methods
            if _method_matches(method, method_signature)
        ]
    if methods:
        lines.append("")
        lines.append("# direct/virtual methods")
        for method in methods:
            lines.extend(
                _format_method(
                    cls,
                    method,
                    annotation_data,
                    debug=debug,
                    debuginfo=debuginfo,
                )
            )
            lines.append("")
    return lines


def format_dex_disassembly(
    dex: DEX,
    offset: int = 0,
    size: int = 0,
    debug: bool = False,
    debuginfo: bool = False,
    method_signature: str | None = None,
) -> str:
    """Return smali-like output for a DEX, or offset disassembly for a range."""
    if offset < 0 or size < 0:
        raise ValueError("offset and size must be non-negative")

    if size == 0 and offset == 0:
        if method_signature is not None:
            method_signature = _normalize_method_signature(method_signature)
            if not any(
                _method_matches(method, method_signature)
                for cls in dex.get_classes()
                for method in cls.get_methods()
            ):
                raise ValueError(
                    "method not found or signature is not defined in the target DEX: "
                    + method_signature
                )
        lines = []
        for cls in dex.get_classes():
            lines.extend(
                _format_class(
                    cls,
                    debug=debug,
                    debuginfo=debuginfo,
                    method_signature=method_signature,
                )
            )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    if size == 0:
        current = dex.raw.tell()
        try:
            dex.raw.seek(0, 2)
            size = dex.raw.tell() - offset
        finally:
            dex.raw.seek(current)

    lines = []
    instruction_offset = offset
    for index, instruction in enumerate(dex.disassemble(offset, size)):
        lines.append(_format_instruction(index, instruction_offset, instruction))
        instruction_offset += instruction.get_length()
    return "\n".join(lines)


def disassemble_dex_bytes(
    dex_bytes: bytes | bytearray | memoryview,
    offset: int = 0,
    size: int = 0,
    verify_checksum: bool = True,
    debug: bool = False,
    debuginfo: bool = False,
    method_signature: str | None = None,
) -> str:
    """Parse DEX bytes and return their textual disassembly."""
    return format_dex_disassembly(
        DEX(bytes(dex_bytes), verify_checksum=verify_checksum),
        offset,
        size,
        debug=debug,
        debuginfo=debuginfo,
        method_signature=method_signature,
    )


def disassemble_dex_file(
    dex_path: str,
    offset: int = 0,
    size: int = 0,
    verify_checksum: bool = True,
    debug: bool = False,
    debuginfo: bool = False,
    method_signature: str | None = None,
) -> str:
    """Read a DEX file and return its textual disassembly."""
    with open(dex_path, "rb") as fp:
        return disassemble_dex_bytes(
            fp.read(),
            offset,
            size,
            verify_checksum=verify_checksum,
            debug=debug,
            debuginfo=debuginfo,
            method_signature=method_signature,
        )
