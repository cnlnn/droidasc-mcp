"""Matched real-stdio cold/warm/parallel trials against an unmodified competitor.

Run with ``uv run --with ./artifacts/aimard-asc-mcp python scripts/...``.
Both packages share the same interpreter/dependencies, APK, concurrency and
external time/RSS caps. No OS caches are dropped; fresh servers alternate order.
"""

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import platform
import stat
import subprocess
import sys
import tempfile
import time
from contextlib import suppress
from pathlib import Path

import psutil
from benchmark_cpu_wrapper import select_cpus
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
        if path.suffix in {".py", ".java", ".c", ".so", ".pyd", ".json"}
    }


def competitor_runtime_identity(checkout):
    spec = importlib.util.find_spec("asc_mcp")
    if spec is None or spec.origin is None:
        raise RuntimeError("Install the pinned competitor in this interpreter with uv run --with")
    root = Path(spec.origin).parent

    def tree(directory):
        return {
            path.relative_to(directory).as_posix(): digest(path)
            for path in sorted(directory.rglob("*.py"))
        }

    installed, expected = tree(root), tree(checkout / "asc_mcp")
    if not expected or installed != expected:
        raise RuntimeError("Installed competitor Python sources differ from the pinned checkout")
    return {"root": str(root), "python_sources_sha256": installed}


def temporary_usage(root):
    """Sample owned regular files, never following symlinks outside the trial."""
    logical, allocated, files = 0, 0, 0
    available = hasattr(os.stat_result, "st_blocks")
    for directory, _, names in os.walk(root):
        for name in names:
            try:
                info = (Path(directory) / name).stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(info.st_mode):
                continue
            files += 1
            logical += info.st_size
            blocks = getattr(info, "st_blocks", None)
            if blocks is None:
                available = False
            else:
                allocated += blocks * 512
    return logical, allocated if available else None, files


def query_content(result):
    """Compare the complete structured response, apart from explicit cache state."""
    content = {key: value for key, value in result.items() if key != "query_cache"}
    if isinstance(content.get("index"), dict):
        content["index"] = {
            key: value
            for key, value in content["index"].items()
            if key not in {"reused", "durable_cache"}
        }
    return content


async def collect_reference_pages(call, implementation, tool, params, label, page_size):
    """Follow real continuations, preserving all rows and stable page diagnostics."""
    ours = implementation == "ours"
    combined, pages, recoveries = [], [], []
    cursor, expected = None, None
    while True:
        arguments = {**params, "limit": page_size}
        arguments["offset" if ours else "cursor"] = len(combined) if ours else cursor
        page_label = f"{label}:page:{len(pages)}:attempt:{len(recoveries)}"
        result = await call(page_label, tool, arguments, allow_response_limit=ours)
        if result.get("status") == "error":
            assert ours and result.get("code") == "response_limit" and page_size > 1, result
            recoveries.append({"offset": len(combined), "limit": page_size})
            page_size = max(1, page_size // 2)
            continue
        row_key = "items" if ours else "hits"
        rows = result[row_key]
        assert isinstance(rows, list) and len(rows) <= page_size
        stable = query_content(result)
        for key in (
            row_key,
            "offset",
            "limit",
            "next_offset",
            "next_cursor",
            "has_more",
            "truncated",
            "page_limited_by",
            "response_byte_limit",
        ):
            stable.pop(key, None)
        if expected is None:
            expected = stable
        assert stable == expected, "Page metadata changes inside a collection"
        assert len(combined) + len(rows) <= result["total"]
        more = len(combined) + len(rows) < result["total"]
        if ours:
            assert result["offset"] == len(combined) and result["limit"] == page_size
            assert result["has_more"] == result["truncated"] == more
            assert result["next_offset"] == (len(combined) + len(rows) if more else None)
        else:
            cursor = result["next_cursor"]
            assert cursor == (str(len(combined) + len(rows)) if more else None)
        assert rows or not more, "Nonterminal reference page does not advance"
        combined.extend(rows)
        pages.append(page_label)
        if not more:
            break
    assert len(combined) == expected["total"]
    return {**expected, row_key: combined}, pages, recoveries


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
        string = {"operation": "find_string_refs", "value": "https://"}
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
        string = ("apk_find_string_references", {"value": "https://"})
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

    chosen = {"method": method, "field": field, "fuzzy": fuzzy, "string": string, "graph": graph}
    return (
        [command(method), command(field)]
        if scenario == "concurrent"
        else [command(chosen[scenario.removeprefix("full_")])]
    )


async def trial(args, implementation, scenario, round_number, report, save):
    metric = {
        "implementation": implementation,
        "scenario": scenario,
        "round": round_number,
        "operations": [],
        "peak_descendant_rss_bytes": 0,
        "sampled_peak_temporary_logical_bytes": 0,
        "sampled_peak_temporary_allocated_bytes": None,
        "sampled_peak_temporary_file_count": 0,
        "temporary_usage_samples": 0,
        "temporary_usage_errors": 0,
        "cpu_affinity_samples": 0,
        "peak_descendant_process_count": 0,
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
    response_times = {}
    printed_operations = 0
    temporary_root = None
    next_affinity_check = 0

    def show_operations():
        nonlocal printed_operations
        for operation in metric["operations"][printed_operations:]:
            print(
                json.dumps(
                    {
                        key: value
                        for key, value in operation.items()
                        if key not in {"result", "progress", "arguments"}
                    }
                ),
                flush=True,
            )
        printed_operations = len(metric["operations"])

    def current_rss():
        total = 0
        for child in children():
            with suppress(psutil.Error):
                total += child.memory_info().rss
        return total

    async def monitor():
        nonlocal peak, next_affinity_check
        next_disk_sample = 0
        while running:
            processes = children()
            metric["peak_descendant_process_count"] = max(
                metric["peak_descendant_process_count"], len(processes)
            )
            total = 0
            for child in processes:
                with suppress(psutil.Error):
                    total += child.memory_info().rss
            peak = max(peak, total)
            metric["peak_descendant_rss_bytes"] = max(metric["peak_descendant_rss_bytes"], total)
            if total > args.memory_mib * 1024**2:
                metric["safety_stop"] = "aggregate_descendant_rss"
            if "transport_start_seconds" in metric and time.monotonic() >= next_affinity_check:
                for child in processes:
                    try:
                        affinity = child.cpu_affinity()
                        if not affinity or not set(affinity) <= set(args.cpu_affinity):
                            metric["safety_stop"] = "descendant_cpu_affinity"
                        metric["cpu_affinity_samples"] += 1
                    except psutil.NoSuchProcess:
                        continue
                    except (psutil.Error, AttributeError, NotImplementedError) as exc:
                        metric["safety_stop"] = "unverifiable_cpu_affinity"
                        metric["cpu_affinity_error"] = repr(exc)
                next_affinity_check = time.monotonic() + 0.2
            if temporary_root is not None and time.monotonic() >= next_disk_sample:
                try:
                    logical, allocated, files = await asyncio.to_thread(
                        temporary_usage, temporary_root
                    )
                    metric["temporary_usage_samples"] += 1
                    metric["sampled_peak_temporary_logical_bytes"] = max(
                        metric["sampled_peak_temporary_logical_bytes"], logical
                    )
                    metric["sampled_peak_temporary_file_count"] = max(
                        metric["sampled_peak_temporary_file_count"], files
                    )
                    if allocated is not None:
                        metric["sampled_peak_temporary_allocated_bytes"] = max(
                            metric["sampled_peak_temporary_allocated_bytes"] or 0, allocated
                        )
                    if logical > args.session_disk_mib * 1024**2:
                        metric["safety_stop"] = "temporary_logical_bytes"
                except OSError:
                    metric["temporary_usage_errors"] += 1
                next_disk_sample = time.monotonic() + 0.2
            if metric.get("safety_stop"):
                for child in reversed(processes):
                    with suppress(psutil.Error):
                        child.kill()
                return
            await asyncio.sleep(0.02)

    task = asyncio.create_task(monitor())
    try:
        with tempfile.TemporaryDirectory(prefix="matched-runtime-") as temporary:
            temporary_root = Path(temporary)
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
                "DROIDASC_MCP_MAX_DEX_SESSION_BYTES": str(args.session_disk_mib * 1024**2),
            }
            env.pop("DROIDASC_MCP_XREF_CACHE_DIR", None)
            if implementation == "ours":
                # The measured core must not accidentally use a configured Java backend.
                env.pop("DROIDASC_MCP_JADX_HOME", None)
                env["DROIDASC_MCP_JAVA"] = "java-must-not-run"
            endpoint = StdioServerParameters(
                command=sys.executable,
                args=[
                    str(Path(__file__).with_name("benchmark_cpu_wrapper.py")),
                    "--cpus",
                    ",".join(map(str, args.cpu_affinity)),
                    "droidasc_mcp" if implementation == "ours" else "asc_mcp",
                ],
                env=env,
            )
            async with Client(endpoint) as client:
                metric["transport_start_seconds"] = round(time.monotonic() - started, 4)

                async def call(label, tool, params, *, allow_response_limit=False):
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
                        response_times[label] = time.monotonic()
                        operation["response_from_process_start_seconds"] = round(
                            response_times[label] - started, 4
                        )
                        result = reply.structured_content
                        operation["result"] = result
                        recovery = (
                            allow_response_limit
                            and result
                            and result.get("status") == "error"
                            and result.get("code") == "response_limit"
                        )
                        if (
                            reply.is_error
                            or not result
                            or (result.get("status", "ok") != "ok" and not recovery)
                        ):
                            raise RuntimeError(str(reply)[:2000])
                        operation["status"] = "response_limit" if recovery else "ok"
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
                        operation["seconds"] = round(
                            response_times.get(label, time.monotonic()) - start, 4
                        )
                        operation["peak_descendant_rss_bytes"] = max(peak, current_rss())

                ours = implementation == "ours"
                opened = await call(
                    "open",
                    "asc_open_artifact_session" if ours else "load_artifact",
                    {
                        "artifact_path": str(args.apk),
                        "max_uncompressed_bytes": args.expanded_mib * 1024**2,
                    }
                    if ours
                    else {"path": str(args.apk)},
                )
                metric["ready_from_process_start_seconds"] = round(
                    response_times["open"] - started, 4
                )
                key = opened["session_id" if ours else "analysis_id"]
                commands = queries(implementation, key, scenario, args.graph_root, args.graph_depth)

                async def command(label, tool, params):
                    if not scenario.startswith("full_"):
                        return await call(label, tool, params)
                    result, pages, recoveries = await collect_reference_pages(
                        call, implementation, tool, params, label, args.page_size
                    )
                    response_times[label] = response_times[pages[-1]]
                    metric.setdefault("reference_collections", []).append(
                        {
                            "label": label,
                            "page_labels": pages,
                            "response_limit_recoveries": recoveries,
                        }
                    )
                    return result

                for repeat in range(getattr(args, "repeats", 3)):
                    start = time.monotonic()
                    results = await asyncio.gather(
                        *(
                            command(f"query:{repeat}:{i}", tool, params)
                            for i, (tool, params) in enumerate(commands)
                        )
                    )
                    metric.setdefault("batch_seconds", []).append(
                        round(
                            max(response_times[f"query:{repeat}:{i}"] for i in range(len(commands)))
                            - start,
                            4,
                        )
                    )
                    if repeat == 0:
                        metric["first_result_from_process_start_seconds"] = round(
                            max(response_times[f"query:0:{i}"] for i in range(len(commands)))
                            - started,
                            4,
                        )
                        cold = results
                    else:
                        for first, current in zip(cold, results, strict=True):
                            assert query_content(first) == query_content(current), (
                                "Warm structured result differs from cold result"
                            )
                    show_operations()
                await call(
                    "close",
                    "asc_close_dex_session" if ours else "close_artifact",
                    {"session_id" if ours else "analysis_id": key},
                )
                if metric.get("safety_stop"):
                    raise RuntimeError(f"Trial exceeded resource cap: {metric['safety_stop']}")
                if metric["temporary_usage_errors"] or not metric["temporary_usage_samples"]:
                    raise RuntimeError("Temporary storage measurement is incomplete")
                metric["status"] = "passed"
    except Exception as exc:
        metric.update(status="failed", error=str(exc)[:2000])
    finally:
        running = False
        await task
        for child in reversed(children()):
            with suppress(psutil.Error):
                child.kill()
        show_operations()
        # Serialize potentially multi-megabyte receipts only after all measured
        # responses. Report I/O must not delay concurrent callbacks or first results.
        save()


async def main(args):
    args.apk = args.apk.resolve(strict=True)
    args.cpu_affinity = select_cpus(args.workers)
    commit = subprocess.check_output(
        ["git", "-C", str(args.competitor), "rev-parse", "HEAD"], text=True
    ).strip()
    assert not subprocess.check_output(["git", "-C", str(args.competitor), "status", "--porcelain"])
    competitor_runtime = competitor_runtime_identity(args.competitor)
    report = {
        "apk_sha256": digest(args.apk),
        "competitor_commit": commit,
        "platform": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "competitor_runtime": competitor_runtime,
        "ours_runtime_sha256": runtime_identity(),
        "harness_sha256": digest(Path(__file__)),
        "timing_version": 2,
        "temporary_usage_sampling_seconds": 0.2,
        "logical_cpus": psutil.cpu_count(),
        "physical_cpus": psutil.cpu_count(logical=False),
        "system_memory_bytes": psutil.virtual_memory().total,
        "workers": args.workers,
        "cpu_budget_version": 1,
        "cpu_affinity": args.cpu_affinity,
        "cpu_wrapper_sha256": digest(Path(__file__).with_name("benchmark_cpu_wrapper.py")),
        "graph_depth": args.graph_depth,
        "memory_cap_mib": args.memory_mib,
        "timeout_per_call_seconds": args.timeout,
        "repeats": args.repeats,
        "full_collection_page_size": args.page_size,
        "ours_expansion_budget_mib": args.expanded_mib,
        "ours_session_disk_budget_mib": args.session_disk_mib,
        "external_temporary_logical_cap_mib": args.session_disk_mib,
        "notes": "Fresh servers alternate; same interpreter/dependencies; OS caches retained. "
        "Both server roots inherit the same explicit CPU affinity before product imports; "
        "all descendants are periodically checked after transport initialization. Nested pools "
        "can contain more processes than workers, but cannot exceed this logical-CPU set. "
        "The common Python/psutil wrapper overhead is included in time and RSS. "
        "Timing stops on decoded MCP response arrival; full receipt I/O is outside measured calls. "
        "RSS sums all owned descendants (shared pages can be counted more than once). "
        "Temporary regular files are sampled separately in a background thread every 0.2 s, "
        "not added to RSS; peaks are lower bounds and include indexes/private snapshots. "
        "Allocated bytes use st_blocks where available, otherwise null; tmpfs is not process RSS. "
        "Reference totals: ours individual sites, competitor caller groups. "
        "full_method/full_field collect every page; timings include all response-limit retries. "
        "Cross-implementation complete-site equality requires the separate offline verifier. "
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
    try:
        report["competitor_runtime_unchanged"] = competitor_runtime == competitor_runtime_identity(
            args.competitor
        )
    except RuntimeError as exc:
        report["competitor_runtime_unchanged"] = False
        report["competitor_runtime_error"] = str(exc)
    report["status"] = (
        "passed"
        if report["input_unchanged"]
        and report["runtime_unchanged"]
        and report["competitor_runtime_unchanged"]
        and all(trial["cpu_affinity_samples"] > 0 for trial in report["trials"])
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
        choices=[
            "method",
            "field",
            "fuzzy",
            "string",
            "graph",
            "concurrent",
            "full_method",
            "full_field",
        ],
        default=["method", "field", "fuzzy", "graph", "concurrent"],
    )
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--repeats", type=int, choices=range(1, 4), default=3)
    parser.add_argument("--page-size", type=int, choices=range(1, 1001), default=1000)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--memory-mib", type=int, default=4096)
    parser.add_argument("--expanded-mib", type=int, choices=range(1, 2049), default=128)
    parser.add_argument("--session-disk-mib", type=int, default=4096)
    parser.add_argument("--graph-root", default=GRAPH_ROOT)
    parser.add_argument("--graph-depth", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    if (
        min(
            arguments.rounds,
            arguments.workers,
            arguments.timeout,
            arguments.memory_mib,
            arguments.session_disk_mib,
        )
        < 1
    ):
        parser.error("rounds, workers, timeout and memory cap must be positive")
    asyncio.run(main(arguments))
