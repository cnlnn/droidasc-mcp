"""Compare frontier results against a freshly built, independently accepted full index.

This is an accuracy diagnostic; use the real MCP harness for latency/RSS acceptance.
"""

import argparse
import json
import sqlite3
import tempfile
import time
from contextlib import closing
from pathlib import Path

from verify_call_index import accept_index, validate_acceptance
from verify_fuzzy_references import digest, runtime_identity
from verify_mcp_reference_pages import fingerprint


def main(args):
    from droidasc_mcp.call_graph import query_call_graph
    from droidasc_mcp.config import Settings
    from droidasc_mcp.dex_worker import analyze
    from droidasc_mcp.native_graph import query_frontier
    from droidasc_mcp.native_index import build
    from droidasc_mcp.runner import DroidAscRunner
    from droidasc_mcp.service import _normalize_dex_query

    args.apk = args.apk.resolve(strict=True)
    assert not args.output.exists(), "Preserve previous acceptance attempts"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        allowed_roots=(args.apk.parent,), max_xref_index_bytes=args.index_mib * 1024**2
    )
    report = {
        "apk_sha256": digest(args.apk),
        "runtime_sha256": runtime_identity(),
        "verifier_sha256": digest(Path(__file__)),
        "status": "running",
        "queries": [],
        "notes": "Direct-worker accuracy only; not a real transport performance comparison. "
        "Full index data is independently accepted; bounded graph traversal is shared product "
        "logic, not an independent BFS/ordering/budget oracle. DEX 041 is outside this gate.",
    }

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    save()
    try:
        with tempfile.TemporaryDirectory(prefix="frontier-oracle-", dir=args.output.parent) as temp:
            root = Path(temp)
            request = DroidAscRunner(settings)._dex_request([], {"offset": 0, "limit": 100})
            request.update(
                artifact_path=str(args.apk),
                max_uncompressed_bytes=args.expanded_mib * 1024**2,
                prepare=True,
            )
            prepared = analyze(request, root)
            assert prepared["status"] == "ok", prepared
            report["input_id"] = prepared["input_id"]
            report["sources"] = prepared["sources"]
            bundle, target = root / "analysis.apk", root / "calls.sqlite"
            started = time.perf_counter()
            build(settings, bundle, target, root, {}, calls_only=True)
            report["full_index"] = {
                "stored_bytes": target.stat().st_size,
                "build_seconds": time.perf_counter() - started,
            }
            report["independent_full_index"] = accept_index(
                args.apk,
                bundle,
                target,
                prepared["sources"],
                root,
                byte_limit=args.expanded_mib * 1024**2,
                input_id=prepared["input_id"],
                engine_version=prepared["engine_version"],
            )
            accepted = report["independent_full_index"]
            assert accepted["runtime_sha256"] == report["runtime_sha256"]
            assert accepted["apk_sha256"] == report["apk_sha256"]
            save()
            with closing(sqlite3.connect(f"{target.as_uri()}?mode=ro", uri=True)) as db:
                for descriptor in args.root:
                    for direction in ("incoming", "outgoing", "both"):
                        for depth in args.depths:
                            query = _normalize_dex_query(
                                {
                                    "operation": "get_call_graph",
                                    "method_descriptor": descriptor,
                                    "direction": direction,
                                    "depth": depth,
                                    "max_nodes": 500,
                                    "max_edges": 1000,
                                }
                            )
                            expected = query_call_graph(db, query)
                            started = time.perf_counter()
                            actual = query_frontier(settings, bundle, query)
                            elapsed = time.perf_counter() - started
                            assert (
                                actual["instruction_scan_complete"] and actual["scan_errors"] == 0
                            )
                            assert actual["runtime_target_resolution"] == "not_performed"
                            for key in (
                                "backend",
                                "backend_version",
                                "instruction_scan_complete",
                                "scan_errors",
                                "runtime_target_resolution",
                            ):
                                actual.pop(key)
                            assert actual == expected, (query, actual, expected)
                            receipt = {
                                "query": query,
                                "status": "passed",
                                "exact_match": True,
                                "accepted_full_index_sha256": accepted["index_sha256"],
                                "independent_acceptance_sha256": fingerprint(accepted),
                                "graph_sha256": fingerprint(expected),
                                "node_count": actual.get("node_count"),
                                "edge_count": actual.get("edge_count"),
                                "truncation_reasons": actual.get("truncation_reasons"),
                                "diagnostic_seconds": elapsed,
                            }
                            report["queries"].append(receipt)
                            print(json.dumps(receipt), flush=True)
                            save()
            validate_acceptance(
                accepted,
                args.apk,
                bundle,
                target,
                prepared["sources"],
                input_id=prepared["input_id"],
                engine_version=prepared["engine_version"],
            )
        report["verifier_unchanged"] = digest(Path(__file__)) == report["verifier_sha256"]
        assert report["verifier_unchanged"]
        report["input_unchanged"] = digest(args.apk) == report["apk_sha256"]
        report["runtime_unchanged"] = runtime_identity() == report["runtime_sha256"]
        assert report["input_unchanged"] and report["runtime_unchanged"]
        report["status"] = "passed"
    except BaseException as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        raise
    finally:
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--root", action="append", required=True)
    parser.add_argument("--depths", nargs="+", type=int, choices=range(1, 6), default=[1, 3, 5])
    parser.add_argument("--expanded-mib", type=int, choices=range(1, 2049), default=128)
    parser.add_argument("--index-mib", type=int, choices=range(1, 8193), default=4096)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
