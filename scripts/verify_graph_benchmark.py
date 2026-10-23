"""Replay measured graphs against a fresh, independently accepted complete call index.

Complete index operands and measured graph equality are separate checks. Traversal,
ordering/budget policy and runtime dispatch are not independently proved by this gate.
"""

import argparse
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from benchmark_call_graph import verify_sites_in_graphs
from benchmark_competitor_runtime import competitor_runtime_identity
from verify_call_index import STATUS, accept_index, validate_acceptance
from verify_mcp_reference_pages import digest, fingerprint, original_bundle, runtime_identity


def validate_graph_result(actual, opened, expected):
    session_fields = {"idle_ttl_seconds", "reserved_index_bytes", "reuse", "stored_bytes"}
    common = {key: value for key, value in opened.items() if key not in session_fields}
    diagnostics = {
        "backend",
        "backend_version",
        "instruction_scan_complete",
        "scan_errors",
        "runtime_target_resolution",
        "query_cache",
        "index",
    }
    assert actual.keys() <= expected.keys() | common.keys() | diagnostics
    assert {key: actual[key] for key in expected} == expected, (
        "Measured graph differs from full index"
    )
    for key in common.keys() - expected.keys():
        assert actual[key] == common[key], f"Graph provenance differs: {key}"
    assert actual["instruction_scan_complete"] and actual["scan_errors"] == 0
    assert actual["runtime_target_resolution"] == "not_performed"


def bind_graph_acceptance(acceptance, opened):
    """Require each measured graph to use the independently accepted input identity."""
    assert acceptance["schema"] == 2 and acceptance["status"] == STATUS
    for name in ("input_id", "engine_version", "sources"):
        assert opened[name] == acceptance[name], f"Measured {name} differs from accepted index"
    assert acceptance["sources_sha256"] == fingerprint(opened["sources"])
    return {
        "accepted_index_sha256": acceptance["index_sha256"],
        "independent_acceptance_sha256": fingerprint(acceptance),
    }


def main(args):
    from droidasc_mcp.call_graph import query_call_graph
    from droidasc_mcp.config import Settings
    from droidasc_mcp.native_index import build
    from droidasc_mcp.service import _normalize_dex_query

    args.apk = args.apk.resolve(strict=True)
    receipts = [path.resolve(strict=True) for path in args.receipts]
    assert not args.output.exists(), "Preserve previous acceptance attempts"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    helpers = [
        Path(__file__),
        *[
            Path(__file__).with_name(name)
            for name in (
                "benchmark_call_graph.py",
                "benchmark_competitor_runtime.py",
                "verify_fuzzy_references.py",
                "verify_mcp_reference_pages.py",
                "verify_call_index.py",
            )
        ],
    ]
    bound = [args.apk, *receipts, *helpers]
    report = {
        "status": "running",
        "runtime_sha256": runtime_identity(),
        "acceptance_inputs_sha256": {str(path): digest(path) for path in bound},
        "graphs": [],
        "competitor_failures": [],
        "release_approved": False,
        "scope": "exact measured graph versus independently accepted complete call/method/"
        "dynamic index for ordinary pre-041 APK DEX; not independent graph traversal/ordering/"
        "budget policy, DEX 041 normalization, or runtime dispatch",
    }

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    try:
        save()
        data = [json.loads(path.read_text()) for path in receipts]
        first_opened = next(
            t["operations"][0]["result"] for t in data[0]["trials"] if t["implementation"] == "ours"
        )
        sources = first_opened["sources"]
        with tempfile.TemporaryDirectory(prefix="measured-graph-oracle-") as directory:
            root = Path(directory)
            bundle, index = root / "original.apk", root / "calls.sqlite"
            original_bundle(
                args.apk,
                bundle,
                sources,
                min(row["ours_expansion_budget_mib"] for row in data) * 1024**2,
            )
            # Oracle storage is excluded from both timed products and their resource budgets.
            build(
                Settings(
                    allowed_roots=(args.apk.parent,), max_xref_index_bytes=args.index_mib * 1024**2
                ),
                bundle,
                index,
                root,
                {},
                calls_only=True,
            )
            report["oracle_index_bytes"] = index.stat().st_size
            acceptance = accept_index(
                args.apk,
                bundle,
                index,
                sources,
                root,
                byte_limit=min(row["ours_expansion_budget_mib"] for row in data) * 1024**2,
                input_id=first_opened["input_id"],
                engine_version=first_opened["engine_version"],
            )
            report["independent_full_index"] = acceptance
            save()
            graphs = []
            with closing(sqlite3.connect(index)) as db:
                for path, receipt in zip(receipts, data, strict=True):
                    assert receipt["repeats"] >= 1
                    identities = [(t["implementation"], t["round"]) for t in receipt["trials"]]
                    assert len(set(identities)) == len(identities)
                    ours = {
                        number for implementation, number in identities if implementation == "ours"
                    }
                    competitor = {
                        number
                        for implementation, number in identities
                        if implementation == "competitor"
                    }
                    assert ours and ours == competitor
                    assert receipt["input_unchanged"] and receipt["runtime_unchanged"]
                    assert receipt["competitor_runtime_unchanged"]
                    assert receipt["competitor_runtime"] == competitor_runtime_identity(
                        args.competitor
                    )
                    assert receipt["apk_sha256"] == digest(args.apk)
                    assert receipt["ours_runtime_sha256"] == report["runtime_sha256"]
                    assert receipt["harness_sha256"] == digest(helpers[2])
                    for trial in receipt["trials"]:
                        assert trial["scenario"] == "graph"
                        if trial["implementation"] == "competitor":
                            if trial["status"] != "passed":
                                report["competitor_failures"].append(
                                    {
                                        "receipt": str(path),
                                        "round": trial["round"],
                                        "error": trial.get("error"),
                                        "safety_stop": trial.get("safety_stop"),
                                        "query_failures": [
                                            {
                                                key: operation[key]
                                                for key in (
                                                    "label",
                                                    "status",
                                                    "seconds",
                                                    "error",
                                                    "external_deadline_expired",
                                                )
                                                if key in operation
                                            }
                                            for operation in trial["operations"]
                                            if operation.get("status") == "error"
                                        ],
                                    }
                                )
                            continue
                        assert trial["implementation"] == "ours" and trial["status"] == "passed"
                        opened = trial["operations"][0]["result"]
                        graph_binding = bind_graph_acceptance(acceptance, opened)
                        measured = [
                            op for op in trial["operations"] if op["label"].startswith("query:")
                        ]
                        assert [op["label"] for op in measured] == [
                            f"query:{repeat}:0" for repeat in range(receipt["repeats"])
                        ]
                        for operation in measured:
                            assert (
                                operation["status"] == "ok"
                                and operation["tool"] == "asc_query_dex_session"
                            )
                            params = dict(operation["arguments"])
                            assert params.pop("session_id") == opened["session_id"]
                            assert params["operation"] == "get_call_graph"
                            query = _normalize_dex_query(params)
                            expected = query_call_graph(db, query)
                            actual = operation["result"]
                            validate_graph_result(actual, opened, expected)
                            graphs.append(actual)
                            report["graphs"].append(
                                {
                                    "receipt": str(path),
                                    "round": trial["round"],
                                    "label": operation["label"],
                                    "status": "passed",
                                    "query": query,
                                    "exact_full_index_match": True,
                                    **graph_binding,
                                    "graph_sha256": fingerprint(expected),
                                    "nodes": actual["node_count"],
                                    "edges": actual["edge_count"],
                                    "truncation_reasons": actual["truncation_reasons"],
                                }
                            )
                save()
            report["independent_emitted_sites"] = verify_sites_in_graphs(args.apk, sources, graphs)
            validate_acceptance(
                acceptance,
                args.apk,
                bundle,
                index,
                sources,
                input_id=first_opened["input_id"],
                engine_version=first_opened["engine_version"],
            )
        assert not root.exists()
        assert report["runtime_sha256"] == runtime_identity()
        assert report["acceptance_inputs_sha256"] == {str(path): digest(path) for path in bound}
        report.update(status="passed", input_runtime_oracles_unchanged=True, cleanup_verified=True)
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("receipts", nargs="+", type=Path)
    parser.add_argument("--competitor", type=Path, default=Path("artifacts/aimard-asc-mcp"))
    parser.add_argument("--index-mib", type=int, choices=range(1, 8193), default=4096)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
