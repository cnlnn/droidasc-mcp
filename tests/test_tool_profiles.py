"""The opt-in artifact workflow keeps legacy calls, identities and links usable."""

from dataclasses import replace

import pytest
from mcp import Client

from droidasc_mcp.config import ConfigurationError, Settings
from droidasc_mcp.server import build_server


def test_profile_defaults_and_validation(settings, monkeypatch):
    assert settings.tool_profile == "legacy"
    monkeypatch.setenv("DROIDASC_MCP_ALLOWED_ROOTS", str(settings.allowed_roots[0]))
    monkeypatch.setenv("DROIDASC_MCP_TOOL_PROFILE", "artifact_preview")
    assert Settings.from_env().tool_profile == "artifact_preview"
    monkeypatch.setenv("DROIDASC_MCP_TOOL_PROFILE", "artifact")
    assert Settings.from_env().tool_profile == "artifact"
    monkeypatch.setenv("DROIDASC_MCP_TOOL_PROFILE", "unknown")
    with pytest.raises(ConfigurationError, match="TOOL_PROFILE"):
        Settings.from_env()
    with pytest.raises(ConfigurationError, match="TOOL_PROFILE"):
        replace(settings, tool_profile="unknown")


@pytest.mark.anyio
async def test_preview_has_one_metadata_surface_and_complete_dex_bridge(settings):
    async with Client(build_server(replace(settings, tool_profile="artifact_preview"))) as client:
        tools = (await client.list_tools()).tools
        assert {t.name for t in tools} == {
            "load_artifact",
            "close_artifact",
            "apk_get_summary",
            "apk_get_manifest",
            "apk_list_entries",
            "apk_get_resource_content",
            "apk_get_signing_info",
            "asc_ping",
            "asc_query_dex_session",
            "asc_diff_dex_sessions",
            "asc_secret_candidates",
        }
        for tool in tools:
            for name, field in tool.input_schema.get("properties", {}).items():
                assert field.get("description"), (tool.name, name)
        guide = (await client.read_resource("droidasc://analysis-guide")).contents[0].text
        assert guide == client.session.instructions
        assert "load_artifact" in guide and "session_id=analysis_id" in guide
        assert "asc_apk_info" not in guide
        prompt = await client.get_prompt("triage_apk", {"apk_path": '/a/quoted".apk'})
        assert guide in prompt.messages[0].content.text
        assert 'quoted\\".apk' in prompt.messages[0].content.text
        # Hidden legacy adapters remain callable, not re-advertised duplicates.
        result = await client.call_tool("asc_close_dex_session", {"session_id": "missing"})
        assert not result.is_error and result.structured_content["code"] == "session_not_found"
