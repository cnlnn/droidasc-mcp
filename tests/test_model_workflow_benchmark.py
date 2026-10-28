"""Model workflow receipts separate actual execution from offline task grading."""

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture
def harness(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "model_workflows", scripts / "benchmark_model_workflows.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_isolated_command_contains_only_task_and_one_mcp(harness, tmp_path):
    spec = {"model": "test-model", "reasoning_effort": "medium"}
    endpoint = {
        "command": "/python",
        "args": ["-m", "server"],
        "cwd": "/repo",
        "env": {"DROIDASC_MCP_ALLOWED_ROOTS": "/inputs"},
    }
    args = harness.command(spec, endpoint, tmp_path, "Inspect /inputs/example.apk")
    assert args[-1] == "Inspect /inputs/example.apk"
    assert "--ignore-user-config" in args and "--ephemeral" in args
    assert "project_doc_max_bytes=0" in args
    assert 'web_search="disabled"' in args
    assert args[args.index("-s") + 1] == "read-only"
    for feature in ("shell_tool", "memories", "plugins", "multi_agent"):
        assert args[args.index(feature) - 1] == "--disable"
    assert sum(a.startswith("mcp_servers.") and ".command=" in a for a in args) == 1


def test_completed_turn_is_not_task_success_and_errors_count_as_retries(harness, tmp_path):
    events = []
    for server, tool, result in (
        ("codex", "list_mcp_resources", {}),
        ("analysis", "query", {"structured_content": {"status": "error"}}),
        ("analysis", "query", {"structured_content": {"status": "ok"}}),
        ("analysis", "query", {"structured_content": {"status": "ok"}}),
    ):
        events.append(
            {
                "type": "item.completed",
                "item": {
                    "type": "mcp_tool_call",
                    "server": server,
                    "tool": tool,
                    "status": "completed",
                    "result": result,
                    "error": None,
                },
            }
        )
    events.append({"type": "turn.completed", "usage": {"input_tokens": 123}})
    path = tmp_path / "events.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in events))
    result = harness.event_summary(path)
    assert result["turn_completed"]
    assert result["task_success"] == "pending_offline_judge"
    assert result["tool_calls"] == 4 and result["product_tool_calls"] == 3
    assert result["host_mcp_calls"] == 1
    assert result["product_tool_errors"] == result["retry_calls_after_same_tool_error"] == 1


def test_missing_completion_and_non_mcp_execution_are_visible(harness, tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text(json.dumps({"type": "item.completed", "item": {"type": "command_execution"}}))
    result = harness.event_summary(path)
    assert not result["turn_completed"]
    assert result["other_tool_calls"] == 1
    assert result["task_success"] == "pending_offline_judge"
