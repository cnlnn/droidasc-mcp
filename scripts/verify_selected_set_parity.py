"""Compare cached MCP collections with uncached native scans of original APK bytes.

This checks ordered rows, duplicate multiplicity and all backend semantic fields.
It is a cache-equivalence check, not an independent decoder or a timing benchmark.
Only the offline oracle uses an unbounded page count; MCP limits remain unchanged.
"""

import argparse
import asyncio
import json
import tempfile
from dataclasses import replace
from pathlib import Path

import benchmark_competitor_runtime as benchmark
from verify_mcp_reference_pages import digest, fingerprint, original_bundle, runtime_identity
from verify_operand_page_benchmark import collection_kinds, replay

from droidasc_mcp.config import Settings
from droidasc_mcp.native_strings import query_strings
from droidasc_mcp.native_types import query_types
from droidasc_mcp.reference_spool import PAGE_FIELDS

DIAGNOSTICS = (
    "scanned_methods",
    "scanned_instructions",
    "methods_without_code",
    "scan_errors",
    "instruction_scan_complete",
)
HELPERS = (
    "benchmark_competitor_runtime.py",
    "benchmark_cpu_wrapper.py",
    "verify_operand_page_benchmark.py",
    "verify_mcp_reference_pages.py",
    "verify_reference_page_benchmark.py",
    "verify_fuzzy_references.py",
)


def semantic_result(result):
    assert result["status"] == "ok" and result["instruction_scan_complete"]
    assert result["scan_errors"] == 0 and len(result["items"]) == result["total"]
    assert result["offset"] == 0 and not result["has_more"]
    assert not result["truncated"] and result["next_offset"] is None
    return {k: v for k, v in result.items() if k not in PAGE_FIELDS - {"items"}}


def compare_semantics(expected, recorded, opened):
    assert expected.keys() <= recorded.keys(), "Missing backend semantic fields"
    assert {k: recorded[k] for k in expected} == expected, "Uncached/cached semantics differ"
    for key in recorded.keys() - expected.keys():
        assert key in opened and recorded[key] == opened[key], f"Unexpected context: {key}"
    return fingerprint(expected)


def cache_evidence(operations, collection):
    counts = {"selected_reference_set": 0, "exact_query_page": 0}
    for op in operations:
        if op["label"] not in collection["page_labels"]:
            continue
        cache = op["result"].get("query_cache")
        if cache is not None:
            assert cache["hit"] is True and cache["scope"] in counts
            counts[cache["scope"]] += 1
    if collection["label"].split(":")[1] != "0":
        assert sum(counts.values()), "Repeated collection has no cache evidence"
    return counts


def validate_receipt(receipt, apk_sha256, runtime, helpers):
    assert receipt["status"] == "passed"
    assert receipt["input_unchanged"] and receipt["runtime_unchanged"]
    assert receipt["apk_sha256"] == apk_sha256
    assert receipt["ours_runtime_sha256"] == runtime
    assert receipt["harness_sha256"] == helpers["benchmark_competitor_runtime.py"]
    assert receipt["cpu_wrapper_sha256"] == helpers["benchmark_cpu_wrapper.py"]
    assert receipt["repeats"] >= 2 and receipt["full_collection_page_size"] > 0
    trials = receipt["trials"]
    keys = [(t["round"], t["scenario"], t["implementation"]) for t in trials]
    expected = {
        (r, s, i)
        for r in range(max(t["round"] for t in trials) + 1)
        for s in {t["scenario"] for t in trials}
        for i in ("ours", "competitor")
    }
    assert len(keys) == len(expected) and set(keys) == expected
    assert all(t["status"] == "passed" for t in trials)
    for trial in trials:
        collection_kinds(trial, receipt["repeats"])


async def main(args):
    assert not args.output.exists(), "Preserve previous acceptance attempts"
    inputs = [args.receipt, args.apk, Path(__file__)]
    inputs.extend(Path(__file__).with_name(name) for name in HELPERS)

    def identity():
        return {str(p.resolve()): digest(p) for p in inputs}

    report = {
        "status": "running",
        "scope": __doc__,
        "acceptance_inputs_sha256": identity(),
        "runtime_sha256": runtime_identity(),
        "collections": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    directory = None
    try:
        save()
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        validate_receipt(
            receipt,
            digest(args.apk),
            report["runtime_sha256"],
            {name: digest(Path(__file__).with_name(name)) for name in HELPERS},
        )
        trials = [t for t in receipt["trials"] if t["implementation"] == "ours"]
        for trial in trials:
            if "operations_file" in trial:
                path = benchmark.operation_receipt_path(args.receipt, trial)
                inputs.append(path)
                report["acceptance_inputs_sha256"][str(path.resolve())] = digest(path)
        opened = benchmark.trial_operations(args.receipt, trials[0])[0]["result"]
        assert opened["artifact_sha256"] == receipt["apk_sha256"]
        sources = opened["sources"]
        kinds = {kind for t in trials for _, kind in collection_kinds(t, receipt["repeats"])}
        with tempfile.TemporaryDirectory(prefix="selected-set-parity-") as directory:
            bundle = Path(directory) / "original.apk"
            original_bundle(
                args.apk, bundle, sources, receipt["ours_expansion_budget_mib"] * 1024**2
            )
            expected = {}
            settings = replace(Settings.from_env(), max_page_size=2**31 - 1)
            for kind in sorted(kinds):
                _, params = benchmark.queries("ours", "offline", kind, benchmark.GRAPH_ROOT, 3)[0]
                query = {k: v for k, v in params.items() if k != "session_id"}
                query.update(offset=0, limit=2**31 - 1)
                scan = query_strings if kind == "string" else query_types
                expected[kind] = semantic_result(scan(settings, bundle, query))
                print(json.dumps({"uncached": kind, "total": expected[kind]["total"]}), flush=True)
            report["uncached"] = {
                kind: {"total": result["total"], "semantic_sha256": fingerprint(result)}
                for kind, result in expected.items()
            }
            for trial in trials:
                operations = benchmark.trial_operations(args.receipt, trial)
                trial_open = operations[0]["result"]
                assert operations[0]["label"] == "open" and operations[0]["status"] == "ok"
                assert operations[-1]["label"] == "close" and operations[-1]["status"] == "ok"
                assert trial_open["sources"] == sources
                assert trial_open["artifact_sha256"] == receipt["apk_sha256"]
                collections = collection_kinds(trial, receipt["repeats"])
                labels = [op["label"] for op in operations]
                assert len(labels) == len(set(labels)), "Duplicate operation label"
                assert all(
                    label in {"open", "close"}
                    or any(label.startswith(c["label"] + ":page:") for c, _ in collections)
                    for label in labels
                ), "Unaccounted query operation"
                for collection, kind in collections:
                    result = await replay(
                        operations,
                        collection,
                        "ours",
                        trial_open,
                        kind,
                        receipt["full_collection_page_size"],
                        {k: expected[kind][k] for k in DIAGNOSTICS},
                    )
                    semantic_hash = compare_semantics(expected[kind], result, trial_open)
                    cached_pages = cache_evidence(operations, collection)
                    report["collections"].append(
                        {
                            "scenario": trial["scenario"],
                            "round": trial["round"],
                            "label": collection["label"],
                            "kind": kind,
                            "total": result["total"],
                            "pages": len(collection["page_labels"]),
                            "cached_pages": cached_pages,
                            "semantic_sha256": semantic_hash,
                            "status": "passed",
                        }
                    )
                    save()
        assert report["acceptance_inputs_sha256"] == identity()
        assert report["runtime_sha256"] == runtime_identity()
        report.update(status="passed", identities_unchanged=True)
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        report["oracle_cleanup_verified"] = directory is None or not Path(directory).exists()
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
