"""Matched real-stdio cold/warm/parallel trials against an unmodified competitor.

Run with ``uv run --with ./artifacts/aimard-asc-mcp python scripts/...``.
Both packages share the same interpreter/dependencies, APK, concurrency and
external time/RSS caps. No OS caches are dropped; fresh servers alternate order.
"""

import argparse
import asyncio
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path

import psutil
from mcp import Client
from mcp.client.stdio import StdioServerParameters

METHOD = "Ljava/lang/String;->equals(Ljava/lang/Object;)Z"
FIELD = "Landroid/os/Build;->MODEL:Ljava/lang/String;"
GRAPH_ROOT = "Landroid/taobao/safemode/SafeModeActivity;->onCreate(Landroid/os/Bundle;)V"


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024**2):
            result.update(block)
    return result.hexdigest()


def runtime_identity():
    import droidasc_mcp

    root = Path(droidasc_mcp.__file__).parent
    return {
        path.name: digest(path)
        for path in sorted(root.iterdir())
        if path.suffix in {".py", ".java", ".c", ".so", ".pyd"}
    }


def queries(implementation, key, scenario, graph_root, graph_depth):
    if implementation == "ours":
        method = {"operation": "find_method_refs", "method_descriptor": METHOD}
        field = {"operation": "find_field_refs", "field_descriptor": FIELD}
        fuzzy = {
            "operation": "search_refs",
            "kind": "method",
            "value": "equal",
            "member_match": "name",
            "class_name": "java.lang",
            "fuzzy_class": True,
        }
        graph = {
            "operation": "get_call_graph",
            "method_descriptor": graph_root,
            "direction": "both",
            "depth": graph_depth,
            "max_nodes": 500,
            "max_edges": 1000,
        }

        def command(query):
            return "asc_query_dex_session", {"session_id": key, "limit": 100, **query}

    else:
        method = (
            "apk_find_method_references",
            {
                "class_name": "java.lang.String",
                "method_name": "equals",
                "descriptor": "(Ljava/lang/Object;)Z",
            },
        )
        field = (
            "apk_find_field_references",
            {
                "class_name": "android.os.Build",
                "field_name": "MODEL",
                "field_type": "Ljava/lang/String;",
            },
        )
        fuzzy = (
            "apk_find_method_references",
            {
                "class_name": "java.lang",
                "method_name": "equal",
                "fuzzy_class": True,
                "exact_name": False,
            },
        )
        owner, local = graph_root.split("->", 1)
        name, proto = local.split("(", 1)
        graph = (
            "apk_get_call_graph",
            {
                "class_name": owner,
                "method_name": name,
                "descriptor": "(" + proto,
                "depth": graph_depth,
            },
        )

        def command(query):
            tool, params = query
            return tool, {
                "analysis_id": key,
                **({} if "graph" in tool else {"limit": 100}),
                **params,
            }

    chosen = {"method": method, "field": field, "fuzzy": fuzzy, "graph": graph}
    return (
        [command(method), command(field)]
        if scenario == "concurrent"
        else [command(chosen[scenario])]
    )


async def trial(args, implementation, scenario, round_number, report, save):
    metric = {
        "implementation": implementation,
        "scenario": scenario,
        "round": round_number,
        "operations": [],
        "peak_descendant_rss_bytes": 0,
        "status": "running",
    }
    report["trials"].append(metric)
    started = time.monotonic()
    before = {child.pid for child in psutil.Process().children(recursive=True)}

    def children():
        return [
            child for child in psutil.Process().children(recursive=True) if child.pid not in before
        ]

    running, peak = True, 0

    def current_rss():
        total = 0
        for child in children():
            with suppress(psutil.Error):
                total += child.memory_info().rss
        return total

    async def monitor():
        nonlocal peak
        while running:
            processes = children()
            total = 0
            for child in processes:
                with suppress(psutil.Error):
                    total += child.memory_info().rss
            peak = max(peak, total)
            metric["peak_descendant_rss_bytes"] = max(metric["peak_descendant_rss_bytes"], total)
            if total > args.memory_mib * 1024**2:
                metric["safety_stop"] = "aggregate_descendant_rss"
                for child in reversed(processes):
                    with suppress(psutil.Error):
                        child.kill()
                return
            await asyncio.sleep(0.02)

    task = asyncio.create_task(monitor())
    try:
        with tempfile.TemporaryDirectory(prefix="matched-runtime-") as temporary:
            env = {
                **os.environ,
                "TMPDIR": temporary,
                "TEMP": temporary,
                "TMP": temporary,
                "ASC_MCP_WORKERS": str(args.workers),
                "DROIDASC_MCP_MAX_PARALLEL": str(args.workers),
                "DROIDASC_MCP_ALLOWED_ROOTS": str(args.apk.parent),
                "DROIDASC_MCP_TIMEOUT_SECONDS": str(args.timeout),
                "DROIDASC_MCP_MAX_XREF_INDEX_BYTES": str(1024**3),
                "DROIDASC_MCP_MAX_DEX_SESSION_BYTES": str(4 * 1024**3),
            }
            env.pop("DROIDASC_MCP_XREF_CACHE_DIR", None)
            if implementation == "ours":
                # The measured core must not accidentally use a configured Java backend.
                env.pop("DROIDASC_MCP_JADX_HOME", None)
                env["DROIDASC_MCP_JAVA"] = "java-must-not-run"
            endpoint = StdioServerParameters(
                command=sys.executable,
                args=["-m", "droidasc_mcp" if implementation == "ours" else "asc_mcp"],
                env=env,
            )
            async with Client(endpoint) as client:
                metric["transport_start_seconds"] = round(time.monotonic() - started, 4)

                async def call(label, tool, params):
                    nonlocal peak
                    peak = current_rss()
                    start = time.monotonic()
                    operation = {"label": label, "tool": tool, "arguments": params, "progress": []}
                    metric["operations"].append(operation)

                    async def progress(completed, total, message):
                        operation["progress"].append(
                            {
                                "seconds": round(time.monotonic() - start, 4),
                                "completed": completed,
                                "total": total,
                                "message": message,
                            }
                        )

                    try:
                        reply = await asyncio.wait_for(
                            client.call_tool(
                                tool,
                                params,
                                read_timeout_seconds=args.timeout,
                                progress_callback=progress,
                            ),
                            args.timeout,
                        )
                        result = reply.structured_content
                        if reply.is_error or not result or result.get("status", "ok") != "ok":
                            raise RuntimeError(str(reply)[:2000])
                        operation["status"] = "ok"
                        operation["result"] = result
                        return result
                    except Exception as exc:
                        operation.update(status="error", error=repr(exc)[:2000])
                        # A timed-out ProcessPool task can outlive the MCP transport.
                        # Stop only this trial's descendants before context shutdown.
                        for child in reversed(children()):
                            with suppress(psutil.Error):
                                child.kill()
                        raise
                    finally:
                        operation["seconds"] = round(time.monotonic() - start, 4)
                        operation["peak_descendant_rss_bytes"] = max(peak, current_rss())
                        save()
                        print(
                            json.dumps(
                                {
                                    k: v
                                    for k, v in operation.items()
                                    if k not in {"result", "progress", "arguments"}
                                }
                            ),
                            flush=True,
                        )

                ours = implementation == "ours"
                opened = await call(
                    "open",
                    "asc_open_artifact_session" if ours else "load_artifact",
                    {"artifact_path" if ours else "path": str(args.apk)},
                )
                metric["ready_from_process_start_seconds"] = round(time.monotonic() - started, 4)
                key = opened["session_id" if ours else "analysis_id"]
                commands = queries(implementation, key, scenario, args.graph_root, args.graph_depth)
                for repeat in range(3):
                    start = time.monotonic()
                    results = await asyncio.gather(
                        *(
                            call(f"query:{repeat}:{i}", tool, params)
                            for i, (tool, params) in enumerate(commands)
                        )
                    )
                    metric.setdefault("batch_seconds", []).append(
                        round(time.monotonic() - start, 4)
                    )
                    if repeat == 0:
                        cold = results
                    else:
                        for first, current in zip(cold, results, strict=True):
                            assert first.get(
                                "items", first.get("hits", first.get("edges"))
                            ) == current.get("items", current.get("hits", current.get("edges")))
                await call(
                    "close",
                    "asc_close_dex_session" if ours else "close_artifact",
                    {"session_id" if ours else "analysis_id": key},
                )
                metric["status"] = "passed"
    except Exception as exc:
        metric.update(status="failed", error=str(exc)[:2000])
    finally:
        running = False
        await task
        for child in reversed(children()):
            with suppress(psutil.Error):
                child.kill()
        save()


async def main(args):
    args.apk = args.apk.resolve(strict=True)
    commit = subprocess.check_output(
        ["git", "-C", str(args.competitor), "rev-parse", "HEAD"], text=True
    ).strip()
    assert not subprocess.check_output(["git", "-C", str(args.competitor), "status", "--porcelain"])
    report = {
        "apk_sha256": digest(args.apk),
        "competitor_commit": commit,
        "platform": platform.platform(),
        "python": sys.version,
        "ours_runtime_sha256": runtime_identity(),
        "logical_cpus": psutil.cpu_count(),
        "physical_cpus": psutil.cpu_count(logical=False),
        "system_memory_bytes": psutil.virtual_memory().total,
        "workers": args.workers,
        "graph_depth": args.graph_depth,
        "memory_cap_mib": args.memory_mib,
        "timeout_per_call_seconds": args.timeout,
        "notes": "Fresh servers alternate; same interpreter/dependencies; OS caches retained. "
        "RSS sums all owned descendants (shared pages can be counted more than once). "
        "Reference totals: ours individual sites, competitor caller groups. "
        "Graphs must normalize to caller/callee pairs and check truncation.",
        "trials": [],
        "status": "running",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    for number in range(args.rounds):
        for scenario in args.scenarios:
            implementations = ["ours", "competitor"]
            if number % 2:
                implementations.reverse()
            for implementation in implementations:
                await trial(args, implementation, scenario, number, report, save)
    report["input_unchanged"] = report["apk_sha256"] == digest(args.apk)
    report["runtime_unchanged"] = report["ours_runtime_sha256"] == runtime_identity()
    report["status"] = (
        "passed"
        if report["input_unchanged"]
        and report["runtime_unchanged"]
        and all(trial["status"] == "passed" for trial in report["trials"])
        else "failed"
    )
    save()
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--competitor", type=Path, default=Path("artifacts/aimard-asc-mcp"))
    parser.add_argument(
        "--scenarios",
        nargs="+",
        choices=["method", "field", "fuzzy", "graph", "concurrent"],
        default=["method", "field", "fuzzy", "graph", "concurrent"],
    )
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--memory-mib", type=int, default=4096)
    parser.add_argument("--graph-root", default=GRAPH_ROOT)
    parser.add_argument("--graph-depth", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if min(arguments.rounds, arguments.workers, arguments.timeout, arguments.memory_mib) < 1:
        parser.error("rounds, workers, timeout and memory cap must be positive")
    asyncio.run(main(arguments))
