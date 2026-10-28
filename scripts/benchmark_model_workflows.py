"""Run frozen user tasks through Codex and one real stdio MCP server.

Expected answers and judges are deliberately separate from this execution harness.
Codex owns authentication, model transport and MCP tool dispatch. JSONL and stderr
are preserved unchanged; a completed model turn is not a task-success verdict.
"""

import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path

import psutil
from benchmark_competitor_runtime import digest, runtime_identity
from mcp import Client
from mcp.client.stdio import StdioServerParameters

DISABLED_FEATURES = (
    "shell_tool",
    "apps",
    "plugins",
    "memories",
    "multi_agent",
    "browser_use",
    "computer_use",
    "image_generation",
    "hooks",
    "skill_search",
    "unbounded_connection_retries",
)


def command(spec, endpoint, directory, prompt):
    result = [
        "codex",
        "exec",
        "--ignore-user-config",
        "--ephemeral",
        "--skip-git-repo-check",
        "-C",
        str(directory),
        "-s",
        "read-only",
        "--json",
        "-m",
        spec["model"],
    ]
    for feature in DISABLED_FEATURES:
        result.extend(("--disable", feature))
    config = {
        "web_search": "disabled",
        "project_doc_max_bytes": 0,
        "model_reasoning_effort": spec["reasoning_effort"],
        "approval_policy": "never",
        "mcp_servers.analysis.command": endpoint["command"],
        "mcp_servers.analysis.args": endpoint["args"],
        "mcp_servers.analysis.cwd": endpoint["cwd"],
        "mcp_servers.analysis.required": True,
        "mcp_servers.analysis.tool_timeout_sec": 180,
    }
    for key, value in config.items():
        result.extend(("-c", key + "=" + json.dumps(value)))
    for key, value in endpoint["env"].items():
        result.extend(("-c", "mcp_servers.analysis.env." + key + "=" + json.dumps(value)))
    result.append(prompt)
    return result


def event_summary(path):
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    calls = [
        e["item"]
        for e in events
        if e.get("type") == "item.completed" and e.get("item", {}).get("type") == "mcp_tool_call"
    ]
    completed = [e for e in events if e.get("type") == "turn.completed"]
    other_tools = [
        e["item"]
        for e in events
        if e.get("type") == "item.completed"
        and e.get("item", {}).get("type") in ("command_execution", "web_search", "file_change")
    ]
    product_calls = [c for c in calls if c.get("server") == "analysis"]
    failures = 0
    retries = 0
    pending = set()
    for call in product_calls:
        result = call.get("result") or {}
        structured = result.get("structured_content") or {}
        failed = (
            call.get("status") == "failed"
            or bool(call.get("error"))
            or result.get("isError", result.get("is_error", False))
            or structured.get("status") == "error"
        )
        key = call.get("tool")
        retries += key in pending
        pending.discard(key)
        if failed:
            failures += 1
            pending.add(key)
    return {
        "turn_completed": bool(completed),
        "tool_calls": len(calls),
        "product_tool_calls": len(product_calls),
        "product_tool_errors": failures,
        "retry_calls_after_same_tool_error": retries,
        "host_mcp_calls": len(calls) - len(product_calls),
        "other_tool_calls": len(other_tools),
        "usage": [e.get("usage") for e in completed],
        "task_success": "pending_offline_judge",
    }


async def capture_surface(endpoint, output):
    import tiktoken

    async with Client(StdioServerParameters(**endpoint)) as client:
        tools = []
        cursor = None
        while True:
            page = await client.list_tools(cursor=cursor)
            tools.extend(t.model_dump(by_alias=True, exclude_none=True) for t in page.tools)
            cursor = page.next_cursor
            if cursor is None:
                break
        surface = {"instructions": client.session.instructions, "tools": tools}
    encoded = json.dumps(surface, sort_keys=True, separators=(",", ":"))
    output.write_text(json.dumps(surface, indent=2) + "\n")
    return {
        "surface_sha256": digest(output),
        "tool_count": len(tools),
        "surface_bytes": len(encoded.encode()),
        "surface_tokens": len(tiktoken.get_encoding("o200k_base").encode(encoded)),
        "token_method": (
            "o200k_base over canonical full MCP surface; not provider-billed schema tokens"
        ),
    }


def main(args):
    assert not args.output.exists(), "Preserve previous trial output directories"
    args.output.mkdir(parents=True)
    repo = Path(__file__).resolve().parents[1]
    spec = json.loads(args.tasks.read_text())
    task = next(t for t in spec["tasks"] if t["id"] == args.task)
    artifact = (repo / task["artifact"]).resolve(strict=True)
    assert 0 <= args.round < spec["rounds"]
    env = {
        "ASC_MCP_ALLOWED_ROOTS": str(artifact.parent),
        "ASC_MCP_WORKERS": "4",
        "DROIDASC_MCP_ALLOWED_ROOTS": str(artifact.parent),
        "DROIDASC_MCP_MAX_PARALLEL": "4",
        "DROIDASC_MCP_MAX_DEX_SESSION_BYTES": str(8192 * 1024**2),
        "DROIDASC_MCP_TIMEOUT_SECONDS": "180",
    }
    endpoint = {
        "command": sys.executable,
        "args": [
            str(repo / "scripts/benchmark_cpu_wrapper.py"),
            "--cpus",
            ",".join(map(str, psutil.Process().cpu_affinity()[:4])),
            "droidasc_mcp" if args.implementation == "ours" else "asc_mcp",
        ],
        "cwd": str(repo),
        "env": env,
    }
    if args.implementation == "ours":
        import droidasc_mcp

        runtime = runtime_identity()
        runtime_root = Path(droidasc_mcp.__file__).parent
    else:
        import asc_mcp

        runtime_root = Path(asc_mcp.__file__).parent
        runtime = {str(p.relative_to(runtime_root)): digest(p) for p in runtime_root.rglob("*.py")}
    report = {
        "status": "running",
        "implementation": args.implementation,
        "task": args.task,
        "round": args.round,
        "artifact_sha256": digest(artifact),
        "tasks_sha256": digest(args.tasks),
        "harness_sha256": digest(Path(__file__)),
        "runtime_root": str(runtime_root),
        "runtime_sha256": runtime,
        "model": spec["model"],
        "reasoning_effort": spec["reasoning_effort"],
        "codex_version": subprocess.check_output(["codex", "--version"], text=True).strip(),
        "endpoint": endpoint,
        "task_success": "pending_offline_judge",
    }
    report_path = args.output / "receipt.json"

    def save():
        report_path.write_text(json.dumps(report, indent=2) + "\n")

    save()
    try:
        report.update(asyncio.run(capture_surface(endpoint, args.output / "surface.json")))
    except BaseException as exc:
        report.update(status="failed_surface_capture", error=repr(exc))
        save()
        raise
    save()
    started = time.monotonic()
    process = None
    children = []
    storage = tempfile.TemporaryDirectory(prefix="droidasc-model-")
    try:
        directory = storage.name
        endpoint["env"].update({k: directory for k in ("TMPDIR", "TEMP", "TMP")})
        prompt = task["request"].format(artifact=artifact)
        argv = command(spec, endpoint, directory, prompt)
        report["argv"] = argv
        save()
        with (
            (args.output / "events.jsonl").open("x") as stdout,
            (args.output / "stderr.log").open("x") as stderr,
        ):
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            owner = psutil.Process(process.pid)
            while process.poll() is None:
                with suppress(psutil.NoSuchProcess):
                    children.extend(p for p in owner.children(recursive=True) if p not in children)
                if time.monotonic() - started > spec["task_timeout_seconds"]:
                    raise TimeoutError("Model workflow trial deadline exceeded")
                time.sleep(0.2)
        report["returncode"] = process.returncode
        report.update(event_summary(args.output / "events.jsonl"))
        report["status"] = (
            "executed"
            if process.returncode == 0 and report["turn_completed"]
            else "failed_execution"
        )
        assert not report["other_tool_calls"], "Baseline escaped the MCP-only tool surface"
    except BaseException as exc:
        report.update(status="failed_execution", error=repr(exc))
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        remaining = []
        for child in children:
            with suppress(psutil.NoSuchProcess):
                if child.is_running() and child.status() != psutil.STATUS_ZOMBIE:
                    remaining.append(child)
        report["surviving_children_before_cleanup"] = [p.pid for p in remaining]
        for child in remaining:
            with suppress(psutil.NoSuchProcess):
                child.kill()
        _, alive = psutil.wait_procs(remaining, timeout=5)
        report["cleanup_verified"] = not alive
        if alive:
            report["status"] = "failed_cleanup"
        storage.cleanup()
        report["seconds"] = round(time.monotonic() - started, 4)
        report["input_runtime_unchanged"] = report["artifact_sha256"] == digest(artifact) and all(
            digest(runtime_root / name) == expected for name, expected in runtime.items()
        )
        report["tasks_harness_unchanged"] = report["tasks_sha256"] == digest(args.tasks) and report[
            "harness_sha256"
        ] == digest(Path(__file__))
        if not report["input_runtime_unchanged"] or not report["tasks_harness_unchanged"]:
            report["status"] = "failed_identity"
        for name in ("events.jsonl", "stderr.log"):
            path = args.output / name
            if path.exists():
                report[name + "_sha256"] = digest(path)
        save()
    return 0 if report["status"] == "executed" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tasks", type=Path, default=Path(__file__).with_name("model_workflow_tasks.json")
    )
    parser.add_argument("--task", required=True)
    parser.add_argument("--round", type=int, default=0)
    parser.add_argument("--implementation", choices=("ours", "competitor"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
