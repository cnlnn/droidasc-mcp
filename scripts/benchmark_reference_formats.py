"""Alternate flat/grouped real-MCP complete collections on the same frozen runtime.

Reuse the existing subprocess, affinity, timing, resource and receipt harness.
Replay exact requests after timing and compare every reconstructed row/diagnostic.
Text bytes count tool text payloads, not JSON-RPC framing or duplicated structured content.
"""

import argparse
import asyncio
import gc
import platform
import sys
from pathlib import Path

import benchmark_competitor_runtime as benchmark
from benchmark_cpu_wrapper import select_cpus
from benchmark_revisions import collection_digests

SCENARIOS = (
    "full_string",
    "full_type",
    "full_method",
    "full_field",
    "full_concurrent",
    "full_operands",
)


def payload_totals(operations, collections):
    labels = {label for c in collections for label in c["page_labels"]}
    pages = [op for op in operations if op["label"] in labels]
    assert len(pages) == len(labels)
    attempts = [
        op
        for op in operations
        if any(op["label"].startswith(c["label"] + ":page:") for c in collections)
    ]
    recoveries = sum(len(c["response_limit_recoveries"]) for c in collections)
    assert len(attempts) == len(pages) + recoveries
    return {
        "pages": len(pages),
        "attempts": len(attempts),
        "response_text_bytes": sum(op["response_text_bytes"] for op in attempts),
        "recovery_attempts": recoveries,
    }


async def main(args):
    assert not args.output.exists(), "Preserve previous benchmark attempts"
    args.apk = args.apk.resolve(strict=True)
    args.cpu_affinity = select_cpus(args.workers)
    args.graph_root, args.graph_depth = benchmark.GRAPH_ROOT, 3
    helpers = [Path(__file__)] + [
        Path(__file__).with_name(name)
        for name in (
            "benchmark_competitor_runtime.py",
            "benchmark_cpu_wrapper.py",
            "benchmark_revisions.py",
            "verify_mcp_reference_pages.py",
            "verify_fuzzy_references.py",
        )
    ]
    identities = {str(p.resolve()): benchmark.digest(p) for p in helpers}
    report = {
        "status": "running",
        "scope": __doc__,
        "apk_sha256": benchmark.digest(args.apk),
        "runtime_sha256": benchmark.runtime_identity(),
        "helper_sha256": identities,
        "platform": platform.platform(),
        "python": sys.version,
        "python_executable": sys.executable,
        "cpu_affinity": args.cpu_affinity,
        "workers": args.workers,
        "rounds": args.rounds,
        "repeats": args.repeats,
        "scenarios": args.scenarios,
        "requested_page_limit": args.page_size,
        "page_limit_units": {"flat": "reference_sites", "grouped": "caller_groups"},
        "ours_expansion_budget_mib": args.expanded_mib,
        "ours_session_disk_budget_mib": args.session_disk_mib,
        "memory_cap_mib": args.memory_mib,
        "benchmark_client_memory_cap_mib": args.client_memory_mib,
        "timeout_per_call_seconds": args.timeout,
        "timeout_per_complete_trial_seconds": args.trial_timeout,
        "timing_version": benchmark.TIMING_VERSION,
        "receipt_storage_version": 2,
        "cpu_budget_version": 1,
        "trials": [],
        "comparisons": [],
    }
    writer = benchmark.ReceiptWriter(args.output)

    def save():
        writer.save(report)

    try:
        save()
        for number in range(args.rounds):
            for scenario in args.scenarios:
                pair = {}
                for mode in ("flat", "grouped") if number % 2 == 0 else ("grouped", "flat"):
                    args.reference_format = mode
                    gc.collect()
                    await benchmark.trial(args, "ours", scenario, number, report, save)
                    trial = report["trials"][-1]
                    trial["reference_format"] = mode
                    assert trial["status"] == "passed", trial.get("error", trial)
                    assert trial["cpu_affinity_samples"] > 0
                    operations = benchmark.trial_operations(args.output, trial)
                    trial["complete_collections"] = await collection_digests(
                        operations,
                        trial,
                        args.repeats,
                        args.page_size,
                        mode,
                    )
                    trial["payload_totals"] = payload_totals(
                        operations, trial["reference_collections"]
                    )
                    pair[mode] = trial["complete_collections"]
                    del operations
                    save()
                equal = pair["flat"] == pair["grouped"]
                report["comparisons"].append(
                    {
                        "round": number,
                        "scenario": scenario,
                        "complete_result_equality": equal,
                    }
                )
                assert equal, "Grouped references differ from complete flat results"
        assert report["apk_sha256"] == benchmark.digest(args.apk)
        assert report["runtime_sha256"] == benchmark.runtime_identity()
        assert identities == {str(p.resolve()): benchmark.digest(p) for p in helpers}
        report.update(status="passed", input_runtime_helpers_unchanged=True)
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=list(SCENARIOS))
    parser.add_argument("--rounds", type=int, choices=range(1, 101), default=5)
    parser.add_argument("--repeats", type=int, choices=range(2, 4), default=2)
    parser.add_argument("--page-size", type=int, choices=range(1, 1001), default=1000)
    parser.add_argument("--workers", type=int, choices=(2, 4), default=4)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--trial-timeout", type=int, default=600)
    parser.add_argument("--memory-mib", type=int, default=4096)
    parser.add_argument("--client-memory-mib", type=int, default=1024)
    parser.add_argument("--expanded-mib", type=int, choices=range(1, 2049), default=768)
    parser.add_argument("--session-disk-mib", type=int, default=8192)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
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
