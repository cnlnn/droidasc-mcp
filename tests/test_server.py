from __future__ import annotations

import pytest
from mcp import Client

from droidasc_mcp.config import Settings
from droidasc_mcp.server import build_server


@pytest.mark.anyio
async def test_server_advertises_expected_tools(settings: Settings):
    async with Client(build_server(settings)) as client:
        result = await client.list_tools()
    names = {tool.name for tool in result.tools}
    for tool in result.tools:
        assert tool.annotations.destructive_hint is False
        assert tool.annotations.open_world_hint is False
        assert tool.annotations.read_only_hint is ("session" not in tool.name)
    assert names == {
        "asc_ping",
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
        assert {p.name for p in prompts.prompts} == {"triage_apk", "trace_exact_method"}
        guide = await client.read_resource("droidasc://analysis-guide")
        assert "16-bit code units" in guide.contents[0].text
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
