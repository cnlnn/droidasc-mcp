"""Focused artifact tools must cover the complete native session surface."""

from dataclasses import replace

import pytest
from mcp import Client
from pydantic import ValidationError

from droidasc_mcp.server import build_server
from droidasc_mcp.service import DroidAscService
from droidasc_mcp.tool_registry import ToolRegistry

CASES = [
    ("apk_get_dex_info", {}, "info"),
    ("apk_list_classes", {}, "list_classes"),
    ("apk_list_classes", {"query": "fixture"}, "search_classes"),
    ("apk_get_class_source", {"class_name": "fixture.C"}, "get_class_source"),
    ("apk_find_references", {"value": "pattern"}, "find_refs"),
    ("apk_get_dex_manifest", {}, "get_manifest"),
    ("apk_list_methods", {"class_name": "fixture.C"}, "list_methods"),
    ("apk_get_method_source", {"method_descriptor": "Lfixture/C;->m()V"}, "get_method_source"),
    (
        "apk_find_method_references",
        {"method_descriptor": "Lfixture/C;->m()V"},
        "find_method_refs",
    ),
    ("apk_get_method_calls", {"method_descriptor": "Lfixture/C;->m()V"}, "get_method_calls"),
    ("apk_get_call_graph", {"method_descriptor": "Lfixture/C;->m()V"}, "get_call_graph"),
    ("apk_find_field_references", {"field_descriptor": "Lfixture/C;->f:I"}, "find_field_refs"),
    ("apk_find_string_references", {"value": "a[b].*"}, "find_string_refs"),
    ("apk_search_references", {"kind": "method", "value": "m"}, "search_refs"),
    ("apk_find_type_references", {"type_descriptor": "Lfixture/C;"}, "find_type_refs"),
    ("apk_find_type_instructions", {"type_name": "fixture.C"}, "find_type_refs"),
    ("apk_build_xref_index", {}, "build_xref_index"),
    ("apk_search_members", {"kind": "method", "query": "m"}, "search_members"),
    ("apk_search_strings", {"query": "needle"}, "search_strings"),
    ("apk_get_class_outline", {"class_name": "fixture.C"}, "get_class_outline"),
    ("apk_get_class_hierarchy", {"class_name": "fixture.C"}, "get_class_hierarchy"),
    ("apk_get_string_constants", {"class_name": "fixture.C"}, "get_string_constants"),
    ("apk_search_method_bodies", {"query": "const-string"}, "search_method_bodies"),
    ("apk_disassemble_method", {"method_descriptor": "Lfixture/C;->m()V"}, "disassemble_method"),
    ("apk_get_class_source_metadata", {"class_name": "fixture.C"}, "get_class_source_metadata"),
]
FOCUSED_NAMES = {name for name, _, _ in CASES}


def test_focused_output_contract_is_narrow_but_preserves_diagnostics(settings):
    registry = ToolRegistry()
    build_server(settings, registry=registry)
    tools = {tool.name: tool for tool in registry.tools}
    tool = tools["apk_disassemble_method"]
    properties = tool.output_schema["properties"]
    assert "items" in properties and "groups" not in properties and "nodes" not in properties
    result = {
        "status": "ok",
        "items": [{"instruction_offset": 1, "opcode": "return-void", "future_operand": {"x": 1}}],
        "future_diagnostic": ["kept"],
    }
    assert tool.fn_metadata.convert_result(result).structured_content == result
    with pytest.raises(ValidationError):
        tool.fn_metadata.convert_result({"status": "ok", "items": [{"instruction_offset": "1"}]})
    legacy = tools["asc_query_dex_session"].output_schema["properties"]
    assert "groups" in legacy and "nodes" in legacy


def test_every_operation_has_a_focused_route(settings, monkeypatch):
    calls = []

    def query(self, key, **kwargs):
        calls.append((key, kwargs))
        return {"status": "ok"}

    monkeypatch.setattr(DroidAscService, "query_dex_session", query)
    registry = ToolRegistry()
    build_server(replace(settings, tool_profile="artifact"), registry=registry)
    tools = {tool.name: tool for tool in registry.tools}
    for name, args, operation in CASES:
        assert tools[name].fn(analysis_id="handle", **args) == {"status": "ok"}
        key, sent = calls[-1]
        assert key == "handle" and sent["operation"] == operation, name
        assert sent["offset"] == 0 and sent["limit"] == 200 and sent["threads"] == 8
        if "query" in args:
            assert sent["value"] == args["query"] and not sent["case_sensitive"]
    assert len({operation for _, _, operation in CASES}) == 24
    strings = calls[12][1]
    assert strings["value"] == "a[b].*"
    operands = calls[15][1]
    assert operands["type_relation"] == "operand" and operands["type_match"] == "substring"


@pytest.mark.anyio
async def test_final_profile_advertises_focused_tools_and_matching_guide(settings):
    async with Client(build_server(replace(settings, tool_profile="artifact"))) as client:
        tools = (await client.list_tools()).tools
        names = {tool.name for tool in tools}
        assert names == FOCUSED_NAMES | {
            "load_artifact",
            "close_artifact",
            "apk_get_summary",
            "apk_get_manifest",
            "apk_list_entries",
            "apk_get_resource_content",
            "apk_get_signing_info",
            "asc_ping",
            "asc_diff_dex_sessions",
            "asc_secret_candidates",
        }
        assert "asc_query_dex_session" not in names
        assert "asc_open_dex_session" not in names
        for tool in tools:
            for name, field in tool.input_schema.get("properties", {}).items():
                assert field.get("description"), (tool.name, name)
        guide = (await client.read_resource("droidasc://analysis-guide")).contents[0].text
        assert guide == client.session.instructions
        assert "apk_disassemble_method" in guide and "asc_query_dex_session" not in guide
        prompt = await client.get_prompt(
            "trace_exact_method",
            {"session_id": "missing", "method_descriptor": "Lfixture/C;->m()V"},
        )
        text = prompt.messages[0].content.text
        assert "apk_list_methods" in text and "apk_get_method_calls" in text
        # Compatibility calls remain registered even when not advertised.
        result = await client.call_tool("asc_query_dex_session", {"session_id": "missing"})
        assert not result.is_error and result.structured_content["code"] == "session_not_found"
