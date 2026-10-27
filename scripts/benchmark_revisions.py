"""Alternate installed product revisions through the shared real-MCP benchmark.

Complete rows and diagnostics are compared after timing, independently of page layout.
This regression comparison is not an independent original-byte correctness oracle.
"""

import argparse
import asyncio
import gc
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import benchmark_competitor_runtime as benchmark
from benchmark_cpu_wrapper import select_cpus
from verify_mcp_reference_pages import fingerprint

SCENARIOS = ("full_string", "full_method", "full_field", "full_concurrent")


async def collection_digests(operations, trial, repeats, page_size):
    assert trial["status"] == "passed" and trial["scenario"] in SCENARIOS
    assert operations[0]["label"] == "open" and operations[0]["status"] == "ok"
    assert operations[-1]["label"] == "close" and operations[-1]["status"] == "ok"
    opened = operations[0]["result"]
    commands = benchmark.queries(
        "ours", opened["session_id"], trial["scenario"], benchmark.GRAPH_ROOT, 3
    )
    wanted = {
        f"query:{repeat}:{index}": command
        for repeat in range(repeats)
        for index, command in enumerate(commands)
    }
    collections = trial["reference_collections"]
    assert len(collections) == len(wanted)
    assert {c["label"] for c in collections} == set(wanted)
    consumed = {"open", "close"}
    digests = {}
    for collection in collections:
        label = collection["label"]
        tool, params = wanted[label]
        params = {k: v for k, v in params.items() if k != "limit"}
        attempts = iter(op for op in operations if op["label"].startswith(label + ":page:"))

        async def call(expected_label, expected_tool, arguments, *, _attempts=attempts, **kwargs):
            attempt = next(_attempts, None)
            assert attempt is not None
            assert attempt["label"] == expected_label and attempt["tool"] == expected_tool
            assert attempt["arguments"] == arguments
            assert expected_label not in consumed
            consumed.add(expected_label)
            result = attempt["result"]
            limited = result.get("status") == "error" and result.get("code") == "response_limit"
            assert attempt["status"] == ("response_limit" if limited else "ok")
            assert result["session_id"] == opened["session_id"]
            if not limited:
                for key in ("input_id", "artifact_sha256", "sources"):
                    assert result[key] == opened[key], f"Page provenance differs: {key}"
            return result

        result, pages, recoveries = await benchmark.collect_reference_pages(
            call, "ours", tool, params, label, page_size
        )
        assert next(attempts, None) is None
        assert pages == collection["page_labels"]
        assert recoveries == collection["response_limit_recoveries"]
        result.pop("session_id")
        digests[label] = {"total": result["total"], "complete_result_sha256": fingerprint(result)}
    assert len(consumed) == len(operations) and consumed == {op["label"] for op in operations}
    return digests


def runtime_at(root):
    root = root.resolve(strict=True)
    command = (
        "import hashlib,json,sys; from pathlib import Path; "
        "import droidasc_mcp,droidasc_mcp._dexscan; "
        "root=Path(droidasc_mcp.__file__).parent.resolve(); "
        "native=Path(droidasc_mcp._dexscan.__file__).resolve(); "
        "assert root==Path(sys.argv[1])/'droidasc_mcp'; assert native.parent==root; "
        "print(json.dumps({'root':str(root),'native':str(native),'files':{"
        "p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.iterdir()) "
        "if p.suffix in {'.py','.java','.c','.so','.pyd','.json'}}}))"
    )
    return json.loads(
        subprocess.check_output(
            [sys.executable, "-c", command, str(root)],
            env={**os.environ, "PYTHONPATH": str(root)},
            timeout=30,
            text=True,
        )
    )


async def main(args):
    args.apk = args.apk.resolve(strict=True)
    sources = {
        "baseline": args.baseline_runtime.resolve(strict=True),
        "candidate": args.candidate_runtime.resolve(strict=True),
    }
    assert sources["baseline"] != sources["candidate"]
    runtimes = {name: runtime_at(root) for name, root in sources.items()}
    helpers = [
        Path(__file__),
        Path(benchmark.__file__),
        Path(__file__).with_name("benchmark_cpu_wrapper.py"),
    ]
    helpers.extend(
        Path(__file__).with_name(name)
        for name in ("verify_mcp_reference_pages.py", "verify_fuzzy_references.py")
    )
    helper_hashes = {str(p.resolve()): benchmark.digest(p) for p in helpers}
    args.cpu_affinity = select_cpus(args.workers)
    report = {
        "status": "running",
        "scope": __doc__,
        "apk_sha256": benchmark.digest(args.apk),
        "runtime_sha256": runtimes,
        "helper_sha256": helper_hashes,
        "python": sys.version,
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "timing_version": 2,
        "cpu_budget_version": 1,
        "receipt_storage_version": 2,
        "cpu_affinity": args.cpu_affinity,
        "workers": args.workers,
        "memory_cap_mib": args.memory_mib,
        "benchmark_client_memory_cap_mib": args.client_memory_mib,
        "timeout_per_call_seconds": args.timeout,
        "timeout_per_complete_trial_seconds": args.trial_timeout,
        "ours_expansion_budget_mib": args.expanded_mib,
        "ours_session_disk_budget_mib": args.session_disk_mib,
        "full_collection_page_size": args.page_size,
        "repeats": args.repeats,
        "rounds": args.rounds,
        "scenarios": args.scenarios,
        "trials": [],
        "comparisons": [],
    }
    writer = benchmark.ReceiptWriter(args.output)

    def save():
        writer.save(report)

    original_path = os.environ.get("PYTHONPATH")
    try:
        save()
        for number in range(args.rounds):
            for scenario in args.scenarios:
                pair = {}
                order = ("baseline", "candidate") if number % 2 == 0 else ("candidate", "baseline")
                for revision in order:
                    os.environ["PYTHONPATH"] = str(sources[revision])
                    gc.collect()
                    await benchmark.trial(args, "ours", scenario, number, report, save)
                    trial = report["trials"][-1]
                    trial["revision"] = revision
                    assert trial["status"] == "passed", trial.get("error", trial)
                    assert trial["cpu_affinity_samples"] > 0
                    operations = benchmark.trial_operations(args.output, trial)
                    trial["complete_collections"] = await collection_digests(
                        operations, trial, args.repeats, args.page_size
                    )
                    del operations
                    pair[revision] = trial["complete_collections"]
                    save()
                equal = pair["baseline"] == pair["candidate"]
                report["comparisons"].append(
                    {"round": number, "scenario": scenario, "complete_result_equality": equal}
                )
                assert equal, "Complete rows or diagnostics differ between revisions"
        assert report["apk_sha256"] == benchmark.digest(args.apk)
        assert runtimes == {name: runtime_at(root) for name, root in sources.items()}
        assert helper_hashes == {str(p.resolve()): benchmark.digest(p) for p in helpers}
        report.update(status="passed", input_runtime_helpers_unchanged=True)
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        if original_path is None:
            os.environ.pop("PYTHONPATH", None)
        else:
            os.environ["PYTHONPATH"] = original_path
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--baseline-runtime", type=Path, required=True)
    parser.add_argument("--candidate-runtime", type=Path, required=True)
    parser.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=list(SCENARIOS))
    parser.add_argument("--rounds", type=int, choices=range(1, 101), default=5)
    parser.add_argument("--repeats", type=int, choices=range(1, 4), default=2)
    parser.add_argument("--page-size", type=int, choices=range(1, 1001), default=1000)
    parser.add_argument("--workers", type=int, choices=(2, 4), default=2)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--trial-timeout", type=int, default=600)
    parser.add_argument("--memory-mib", type=int, default=4096)
    parser.add_argument("--client-memory-mib", type=int, default=1024)
    parser.add_argument("--expanded-mib", type=int, choices=range(1, 2049), default=768)
    parser.add_argument("--session-disk-mib", type=int, default=8192)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.graph_root, args.graph_depth = benchmark.GRAPH_ROOT, 3
    if (
        min(
            args.timeout,
            args.trial_timeout,
            args.memory_mib,
            args.client_memory_mib,
            args.session_disk_mib,
        )
        < 1
    ):
        parser.error("Timeouts and resource budgets must be positive")
    asyncio.run(main(args))
