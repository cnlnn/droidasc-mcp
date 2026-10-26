"""Compiled schema registration must preserve SDK contracts and strict validation."""

import json
from copy import deepcopy
from types import SimpleNamespace

import pydantic
import pytest
from mcp.server.mcpserver.tools.base import Tool
from pydantic import TypeAdapter, ValidationError

from droidasc_mcp import contracts


def output() -> contracts.DexResult:
    return {"status": "ok", "items": [{"instruction_offset": 12}]}


def test_compiled_descriptions_are_stable_across_python_docstring_dedenting():
    from droidasc_mcp.input_schemas import schema_document

    tool = SimpleNamespace(
        name="example",
        description="Summary.\n\n    Details.\n    ",
        parameters={"type": "object"},
        context_kwarg=None,
        is_async=True,
        resolved_params={},
        resolver_plans={},
    )
    indented = schema_document([tool])
    tool.description = "Summary.\n\nDetails.\n"
    assert schema_document([tool]) == indented
    assert indented["tools"]["example"]["description"] == "Summary.\n\nDetails."


def test_registry_reuses_schema_without_eager_output_adapter(monkeypatch):
    import mcp.server.mcpserver.utilities.func_metadata as metadata

    from droidasc_mcp.tool_registry import ToolRegistry, contract_schema

    expected = Tool.from_function(output)
    original = metadata.TypeAdapter
    calls = []

    def adapter(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(metadata, "TypeAdapter", adapter)
    registry = ToolRegistry()
    assert registry.tool(annotations=None)(output) is output
    tool = registry.tools[0]
    assert calls == []
    assert tool.output_schema == contract_schema(contracts.DexResult)
    assert tool.parameters == expected.parameters
    value = output() | {"future_diagnostic": {"x": 1}}
    assert tool.fn_metadata.convert_result(value).structured_content == value
    assert len(calls) == 1
    assert tool.fn_metadata.convert_result(value).structured_content == value
    assert len(calls) == 1
    with pytest.raises(ValidationError):
        tool.fn_metadata.convert_result({"status": "ok", "items": [{"instruction_offset": "12"}]})
    with pytest.raises(ValidationError):
        tool.fn_metadata.convert_result({"status": "success"})


def test_packaged_input_cache_avoids_eager_sdk_model_construction(monkeypatch):
    from droidasc_mcp.input_schemas import compiled_inputs
    from droidasc_mcp.server import build_server

    original = Tool.from_function
    calls = []
    compatible = bool(compiled_inputs())

    def construct(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(Tool, "from_function", construct)
    build_server()
    # The package's schema cache is deliberately version-bound. On dependency
    # upgrades the SDK must eagerly rebuild, rather than trusting a stale model.
    assert len(calls) == (0 if compatible else 18)


def test_packaged_input_schemas_match_original_sdk_tools_and_lazy_validation():
    from droidasc_mcp.input_schemas import DeferredInputMetadata, compiled_inputs
    from droidasc_mcp.server import build_server
    from droidasc_mcp.tool_registry import ToolRegistry

    registry = ToolRegistry()
    compatible = bool(compiled_inputs())
    build_server(registry=registry)
    for tool in registry.tools:
        expected = Tool.from_function(
            tool.fn, annotations=tool.annotations, structured_output=False
        )
        assert tool.parameters == expected.parameters
        assert tool.context_kwarg == expected.context_kwarg
        assert tool.is_async == expected.is_async
        assert tool.description == expected.description
        assert isinstance(tool.fn_metadata, DeferredInputMetadata) == compatible
        if compatible:
            assert tool.fn_metadata._input_metadata is None
    tool = next(tool for tool in registry.tools if tool.name == "asc_analyze_dex")
    expected = Tool.from_function(tool.fn, structured_output=False)
    arguments = {"dex_paths": '["/unopened/a.dex"]', "operation": "list_classes"}
    assert tool.fn_metadata.validate_arguments(
        arguments
    ) == expected.fn_metadata.validate_arguments(arguments)
    first = tool.fn_metadata._input_metadata if compatible else None
    if compatible:
        assert first is not None
    assert tool.fn_metadata.validate_arguments(arguments)["dex_paths"] == ["/unopened/a.dex"]
    if compatible:
        assert tool.fn_metadata._input_metadata is first
    with pytest.raises(ValidationError):
        tool.fn_metadata.validate_arguments({"dex_paths": [], "operation": "list_classes"})


@pytest.mark.parametrize(
    "fault", ["missing", "json", "source", "version", "sdk", "digest", "shape", "oversize"]
)
def test_invalid_input_cache_safely_uses_current_sdk_models(tmp_path, fault):
    from droidasc_mcp.input_schemas import INPUT_SCHEMA_PATH, DeferredInputMetadata, records_digest
    from droidasc_mcp.server import build_server
    from droidasc_mcp.tool_registry import ToolRegistry

    document = json.loads(INPUT_SCHEMA_PATH.read_text(encoding="utf-8"))
    if fault == "source":
        document["source_sha256"] = "0" * 64
    if fault == "version":
        document["pydantic_version"] = "0.invalid"
    if fault == "sdk":
        document["mcp_version"] = "0.invalid"
    if fault == "digest":
        document["records_sha256"] = "0" * 64
    if fault == "shape":
        document["tools"]["asc_ping"]["parameters"] = None
        document["records_sha256"] = records_digest(document["tools"])
    path = tmp_path / "inputs.json"
    if fault != "missing":
        path.write_text(
            "{"
            if fault == "json"
            else " " * (512 * 1024 + 1)
            if fault == "oversize"
            else json.dumps(document),
            encoding="utf-8",
        )
    registry = ToolRegistry(input_schema_path=path)
    build_server(registry=registry)
    assert len(registry.tools) == 18
    for tool in registry.tools:
        assert not isinstance(tool.fn_metadata, DeferredInputMetadata)
        assert tool.parameters == Tool.from_function(tool.fn, structured_output=False).parameters


def test_input_cache_source_binding_is_newline_independent(tmp_path, monkeypatch):
    from pathlib import Path

    from droidasc_mcp import input_schemas

    expected = input_schemas.source_digest()
    expected_records = input_schemas.compiled_inputs()
    root = Path(input_schemas.__file__).parent
    for name in ("server.py", "tool_registry.py", "input_schemas.py"):
        source = (root / name).read_text(encoding="utf-8")
        (tmp_path / name).write_bytes(source.replace("\n", "\r\n").encode())
    monkeypatch.setattr(input_schemas, "__file__", str(tmp_path / "input_schemas.py"))
    assert input_schemas.source_digest() == expected
    assert input_schemas.compiled_inputs() == expected_records


def test_packaged_schemas_match_all_current_contracts():
    from droidasc_mcp.tool_registry import (
        OUTPUT_TYPES,
        SCHEMA_PATH,
        compiled_schemas,
        contract_schema,
    )

    schemas = compiled_schemas()
    document = json.loads(SCHEMA_PATH.read_text())
    if document["pydantic_version"] != pydantic.__version__:
        assert schemas is None, "A cache from another Pydantic version must be rejected"
        return
    assert schemas is not None
    for name, contract in OUTPUT_TYPES.items():
        assert schemas[name] == contract_schema(contract)


def test_nullable_output_types_use_equivalent_primitive_arrays():
    import inspect

    from droidasc_mcp.tool_registry import schema_document

    row = schema_document()["schemas"]["DexResult"]["$defs"]["DexRow"]
    offset = row["properties"]["instruction_offset"]
    if "union_format" in inspect.signature(TypeAdapter.json_schema).parameters:
        assert offset["type"] == ["integer", "null"]
        assert "anyOf" not in offset
    else:
        assert offset["anyOf"] == [{"type": "integer"}, {"type": "null"}]


def test_compact_schema_preserves_every_nullable_leaf_and_constrained_union():
    from jsonschema import Draft202012Validator

    from droidasc_mcp.tool_registry import OUTPUT_TYPES, contract_schema

    values = [None, True, False, 0, 1, -1, 1.5, "", "12", [], ["x"], {}, {"a": 1}]
    checked = 0

    def compare(original, compact):
        nonlocal checked
        if isinstance(original, list):
            assert len(original) == len(compact)
            for before, after in zip(original, compact, strict=True):
                compare(before, after)
        elif isinstance(original, dict):
            alternatives = original.get("anyOf")
            primitive = alternatives and all(set(row) == {"type"} for row in alternatives)
            if primitive:
                before, after = Draft202012Validator(original), Draft202012Validator(compact)
                assert [before.is_valid(v) for v in values] == [after.is_valid(v) for v in values]
                if "anyOf" not in compact:
                    assert {k: v for k, v in original.items() if k != "anyOf"} == {
                        k: v for k, v in compact.items() if k != "type"
                    }
                checked += 1
            else:
                assert set(original) == set(compact)
                for key, value in original.items():
                    compare(value, compact[key])
        else:
            assert original == compact

    for contract in OUTPUT_TYPES.values():
        compact = contract_schema(contract)
        Draft202012Validator.check_schema(compact)
        original = TypeAdapter(contract).json_schema()
        if contract is contracts.DexResult:
            assert original["properties"]["items"]["items"] == {"$ref": "#/$defs/DexRow"}
            assert compact["properties"]["items"]["items"] == compact["$defs"]["DexRow"]
            original["properties"]["items"]["items"] = deepcopy(original["$defs"]["DexRow"])
        compare(original, compact)
    assert checked >= 30


def test_schema_generation_falls_back_for_older_pydantic(monkeypatch):
    from droidasc_mcp.tool_registry import contract_schema

    original = TypeAdapter.json_schema

    def older(self):
        return original(self)

    expected = original(TypeAdapter(contracts.DexResult))
    expected["properties"]["items"]["items"] = deepcopy(expected["$defs"]["DexRow"])
    monkeypatch.setattr(TypeAdapter, "json_schema", older)
    assert contract_schema(contracts.DexResult) == expected


def raw_contract_schema(contract):
    import inspect

    options = (
        {"union_format": "primitive_type_array"}
        if "union_format" in inspect.signature(TypeAdapter.json_schema).parameters
        else {}
    )
    return TypeAdapter(contract).json_schema(**options)


def test_only_hot_row_reference_is_inlined_without_changing_any_constraint():
    from droidasc_mcp.tool_registry import OUTPUT_TYPES, contract_schema

    for contract in OUTPUT_TYPES.values():
        original = raw_contract_schema(contract)
        expected = deepcopy(original)
        if contract is contracts.DexResult:
            expected["properties"]["items"]["items"] = deepcopy(expected["$defs"]["DexRow"])
        actual = contract_schema(contract)
        assert actual == expected
        if contract is contracts.DexResult:
            assert actual["$defs"] == original["$defs"]
            assert actual["properties"]["items"]["items"] is not actual["$defs"]["DexRow"]
            assert actual["properties"]["edges"] == original["properties"]["edges"]
            assert (
                actual["properties"]["unresolved_sites"]
                == original["properties"]["unresolved_sites"]
            )


def test_inlined_row_preserves_all_field_validation_and_invalid_instance_errors():
    from jsonschema import Draft202012Validator

    from droidasc_mcp.tool_registry import contract_schema

    original = raw_contract_schema(contracts.DexResult)
    before = Draft202012Validator(original)
    after = Draft202012Validator(contract_schema(contracts.DexResult))
    values = [
        None,
        True,
        False,
        0,
        -1,
        1.5,
        "",
        "read",
        "static",
        "\u00e9\U0001f680",
        [],
        ["x"],
        [1],
        {},
        {"a": 1},
    ]

    def errors(validator, instance):
        return [
            (list(error.absolute_path), error.validator, error.message)
            for error in validator.iter_errors(instance)
        ]

    checked = 0
    rejected = 0
    for field in original["$defs"]["DexRow"]["properties"]:
        for value in values:
            instance = {"status": "ok", "items": [{field: value}]}
            expected = errors(before, instance)
            assert errors(after, instance) == expected
            checked += 1
            rejected += bool(expected)
    for instance in (
        {},
        {"status": "success"},
        {"status": "ok", "items": None},
        {"status": "ok", "items": [None]},
        {"status": "ok", "items": ["bad"]},
        {"status": "ok", "items": [{"future_diagnostic": [None, {"x": 1}]}]},
        {"status": "partial", "items": []},
    ):
        assert errors(after, instance) == errors(before, instance)
    assert checked >= 500 and rejected >= 300


@pytest.mark.parametrize(
    "keyword",
    [
        "$ref",
        "$dynamicRef",
        "$recursiveRef",
        "$id",
        "$anchor",
        "$dynamicAnchor",
        "$recursiveAnchor",
        "$schema",
        "$defs",
        "definitions",
        "id",
    ],
)
@pytest.mark.parametrize("nested", [False, True])
def test_row_inlining_refuses_scope_or_reference_keywords(keyword, nested):
    from droidasc_mcp.tool_registry import _inline_reference_rows

    row = {"type": "object", "properties": {"value": {"type": "string"}}}
    target = row["properties"]["value"] if nested else row
    target[keyword] = "scoped-value"
    schema = {
        "$defs": {"DexRow": row},
        "properties": {"items": {"type": "array", "items": {"$ref": "#/$defs/DexRow"}}},
    }
    expected = deepcopy(schema)
    _inline_reference_rows(schema)
    assert schema == expected


@pytest.mark.parametrize(
    "item_schema",
    [
        {"$ref": "#/$defs/Other"},
        {"$ref": "#/$defs/DexRow", "description": "keep"},
        {"type": "object"},
    ],
)
def test_row_inlining_preserves_nonexact_references_and_siblings(item_schema):
    from droidasc_mcp.tool_registry import _inline_reference_rows

    schema = {
        "$defs": {"DexRow": {"type": "object"}},
        "properties": {"items": {"items": item_schema}},
    }
    expected = deepcopy(schema)
    _inline_reference_rows(schema)
    assert schema == expected


@pytest.mark.parametrize(
    "fault", ["missing", "json", "source", "version", "schema", "digest", "oversize"]
)
def test_invalid_or_stale_schema_cache_falls_back_to_current_contract(tmp_path, fault):
    from droidasc_mcp.tool_registry import ToolRegistry, contract_schema, schema_document

    path = tmp_path / "output_schemas.json"
    if fault != "missing":
        document = schema_document()
        if fault == "source":
            document["contracts_sha256"] = "0" * 64
        if fault == "version":
            document["pydantic_version"] = "0.invalid"
        if fault == "schema":
            document["schemas"].pop("DexResult")
        if fault == "digest":
            document["schemas_sha256"] = "0" * 64
        encoded = (
            "{"
            if fault == "json"
            else " " * (512 * 1024 + 1)
            if fault == "oversize"
            else json.dumps(document)
        )
        path.write_text(encoded, encoding="utf-8")
    registry = ToolRegistry(schema_path=path)
    registry.tool(annotations=None)(output)
    assert registry.tools[0].output_schema == contract_schema(contracts.DexResult)
    assert registry.tools[0].fn_metadata.convert_result(output()).structured_content == output()


def test_registration_preserves_context_and_input_validation():
    from typing import Annotated

    from mcp.server.mcpserver import Context
    from pydantic import Field

    from droidasc_mcp.tool_registry import ToolRegistry

    def contextual(value: Annotated[int, Field(gt=0)], ctx: Context) -> contracts.DexResult:
        return {"status": "ok"}

    registry = ToolRegistry()
    registry.tool(annotations=None)(contextual)
    tool, expected = registry.tools[0], Tool.from_function(contextual)
    assert tool.parameters == expected.parameters
    assert tool.context_kwarg == expected.context_kwarg == "ctx"
    assert tool.fn_metadata.validate_arguments({"value": 1}) == {"value": 1}
    with pytest.raises(ValidationError):
        tool.fn_metadata.validate_arguments({"value": 0})


def test_contract_source_hash_is_newline_independent(tmp_path, monkeypatch):
    from pathlib import Path

    from droidasc_mcp.tool_registry import compiled_schemas, contracts_digest

    original = Path(contracts.__file__)
    expected = contracts_digest()
    expected_schemas = compiled_schemas()
    windows = tmp_path / "contracts.py"
    windows.write_bytes(original.read_text(encoding="utf-8").replace("\n", "\r\n").encode())
    monkeypatch.setattr(contracts, "__file__", str(windows))
    assert contracts_digest() == expected
    assert compiled_schemas() == expected_schemas


def test_registry_rejects_undeclared_contracts_instead_of_dropping_validation():
    from droidasc_mcp.tool_registry import ToolRegistry

    def untyped() -> dict:
        return {}

    registry = ToolRegistry()
    with pytest.raises(TypeError, match="declared object output contracts"):
        registry.tool(annotations=None)(untyped)
    assert registry.tools == []
