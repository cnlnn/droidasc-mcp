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
    assert names == {
        "asc_ping",
        "asc_apk_info",
        "asc_get_manifest",
        "asc_list_classes",
        "asc_get_class_source",
        "asc_find_refs",
    }


@pytest.mark.anyio
async def test_ping_exposes_effective_scope(settings: Settings):
    async with Client(build_server(settings)) as client:
        result = await client.call_tool("asc_ping", {})
    assert result.structured_content["status"] == "ok"
    assert result.structured_content["allowed_roots"] == [str(settings.allowed_roots[0])]
    assert result.structured_content["max_worker_memory_bytes"] == 1024**3
