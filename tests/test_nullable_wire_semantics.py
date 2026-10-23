"""Nullable schema compaction must preserve nested wire and SDK validation."""

import pytest
from jsonschema import Draft202012Validator
from pydantic import TypeAdapter, ValidationError

from droidasc_mcp.contracts import DexResult
from droidasc_mcp.tool_registry import ToolRegistry


@pytest.fixture
def dex_wire_contract():
    def result() -> DexResult:
        return {"status": "ok"}

    registry = ToolRegistry()
    registry.tool(annotations=None)(result)
    tool = registry.tools[0]
    # The SDK's original anyOf representation and the registered (cached or
    # freshly compacted) schema must accept the same complete JSON responses.
    schemas = [TypeAdapter(DexResult).json_schema(), tool.output_schema]
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
    return [Draft202012Validator(schema) for schema in schemas], tool.fn_metadata


@pytest.mark.parametrize("field", ["items", "edges", "unresolved_sites"])
@pytest.mark.parametrize(
    ("offset", "valid"),
    [
        (None, True),
        (0, True),
        (12, True),
        (-1, True),
        (2**63, True),
        (True, False),
        (False, False),
        ("12", False),
        ("twelve", False),
        (1.5, False),
        ([], False),
        ({}, False),
    ],
)
def test_nullable_offset_preserves_full_response_semantics(dex_wire_contract, field, offset, valid):
    validators, metadata = dex_wire_contract
    response = {
        "status": "ok",
        "format": "cli-text-best-effort",
        field: [{"caller": "LC;->f()V", "instruction_offset": offset}],
        "future_diagnostic": {"value": 1},
    }
    for validator in validators:
        assert validator.is_valid(response) is valid
    if valid:
        assert metadata.convert_result(response).structured_content == response
    else:
        with pytest.raises(ValidationError) as error:
            metadata.convert_result(response)
        assert any(
            detail["loc"] == (field, 0, "instruction_offset") for detail in error.value.errors()
        )
