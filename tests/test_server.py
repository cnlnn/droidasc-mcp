from __future__ import annotations

import pytest
from jsonschema import Draft202012Validator
from mcp import Client
from pydantic import TypeAdapter, ValidationError

from droidasc_mcp.config import Settings
from droidasc_mcp.contracts import DexResult, SecretResult
from droidasc_mcp.server import build_server


@pytest.mark.anyio
async def test_server_advertises_expected_tools(settings: Settings):
    async with Client(build_server(settings)) as client:
        result = await client.list_tools()
    names = {tool.name for tool in result.tools}
    for tool in result.tools:
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.open_world_hint is False
        assert tool.annotations.read_only_hint is (
            "session" not in tool.name and tool.name != "asc_secret_candidates"
        )
    assert names == {
        "asc_ping",
        "asc_signing_inventory",
        "asc_inspect_artifact",
        "asc_open_artifact_session",
        "asc_diff_dex_sessions",
        "asc_secret_candidates",
        "asc_apk_info",
        "asc_list_apk_entries",
        "asc_read_apk_entry",
        "asc_manifest_summary",
        "asc_get_manifest",
        "asc_list_classes",
        "asc_get_class_source",
        "asc_find_refs",
        "asc_analyze_dex",
        "asc_open_dex_session",
        "asc_query_dex_session",
        "asc_close_dex_session",
    }


@pytest.mark.anyio
async def test_all_public_arguments_describe_scope(settings):
    async with Client(build_server(settings)) as client:
        tools = await client.list_tools()
    for tool in tools.tools:
        for name, definition in tool.input_schema.get("properties", {}).items():
            assert definition.get("description"), (tool.name, name)


@pytest.mark.anyio
async def test_every_tool_advertises_typed_wire_contract(settings):
    async with Client(build_server(settings)) as client:
        tools = await client.list_tools()
    for tool in tools.tools:
        schema = tool.output_schema
        assert schema and schema["type"] == "object", tool.name
        properties = schema["properties"]
        assert len(properties) >= 5, tool.name
        if tool.name.startswith(("asc_query_dex", "asc_analyze_dex")):
            assert properties["items"]["items"]["$ref"].endswith("/DexRow")
            offset_schema = schema["$defs"]["DexRow"]["properties"]["instruction_offset"]
            Draft202012Validator.check_schema(offset_schema)
            validator = Draft202012Validator(offset_schema)
            for value in (None, 0, 12):
                assert validator.is_valid(value), (tool.name, value)
            for value in (True, 1.5, "12", [], {}):
                assert not validator.is_valid(value), (tool.name, value)
            assert properties["status"]["enum"] == ["ok", "partial", "error", "not_applicable"]


def test_output_contract_checks_nested_types_and_preserves_wire_shape():
    adapter = TypeAdapter(DexResult)
    original = {
        "status": "ok",
        "format": "cli-text-best-effort",
        "items": [{"caller": "LC;->f()V", "instruction_offset": 12}],
        "future_diagnostic": {"value": 1},
    }
    assert adapter.dump_python(adapter.validate_python(original)) == original
    with pytest.raises(ValidationError):
        adapter.validate_python({"status": "ok", "items": [{"instruction_offset": "twelve"}]})
    with pytest.raises(ValidationError):
        adapter.validate_python({"status": "success"})
    with pytest.raises(ValidationError):
        TypeAdapter(SecretResult).validate_python(
            {"status": "ok", "items": [{"pattern": "test", "string_index": 1}]}
        )


@pytest.mark.anyio
async def test_ping_exposes_effective_scope(settings: Settings):
    async with Client(build_server(settings)) as client:
        result = await client.call_tool("asc_ping", {})
    assert result.structured_content["status"] == "ok"
    assert result.structured_content["allowed_roots"] == [str(settings.allowed_roots[0])]
    assert result.structured_content["max_worker_memory_bytes"] == 2 * 1024**3


@pytest.mark.anyio
async def test_workflow_prompts_and_resource(settings):
    async with Client(build_server(settings)) as client:
        prompts = await client.list_prompts()
        assert {p.name for p in prompts.prompts} == {
            "triage_apk",
            "trace_exact_method",
            "compare_versions",
        }
        guide = await client.read_resource("droidasc://analysis-guide")
        assert "16-bit code units" in guide.contents[0].text
        assert "Core DEX operations need neither Java nor JADX" in guide.contents[0].text
        assert "search_refs" in guide.contents[0].text
        assert "call-only index" in guide.contents[0].text
        assert "exact references and Java require" not in guide.contents[0].text
        tools = await client.list_tools()
        secrets = next(tool for tool in tools.tools if tool.name == "asc_secret_candidates")
        assert "native DEX string pools" in secrets.description
        assert "Uses optional JADX" not in secrets.description
        result = await client.get_prompt("triage_apk", {"apk_path": '/samples/name".apk'})
        text = result.messages[0].content.text
        assert 'name\\".apk' in text and "not instructions" in text
        result = await client.get_prompt(
            "trace_exact_method",
            {
                "session_id": "example",
                "method_descriptor": "Lpkg/C;->f(I)V",
            },
        )
        assert "Lpkg/C;->f(I)V" in result.messages[0].content.text
        assert "unresolved dynamic" in result.messages[0].content.text
