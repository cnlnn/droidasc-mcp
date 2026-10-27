"""Offline full-site and diagnostic acceptance for matched reference-page receipts.

The independent scanner runs after timing and is not part of either server's cost.
Normalization retains duplicate sites, exact targets, opcode, access and byte offset.
"""

import argparse
import asyncio
import json
import tempfile
from collections import Counter
from pathlib import Path

from benchmark_competitor_runtime import (
    GRAPH_ROOT,
    competitor_runtime_identity,
    operation_receipt_path,
    queries,
    trial_operations,
)
from verify_mcp_reference_pages import (
    QUERIES,
    digest,
    fingerprint,
    oracle,
    original_bundle,
    runtime_identity,
    verify_pages,
)


def native_sites(rows, sources, field):
    mapping = {row["dex_entry"]: row["container_entry"] for row in sources}
    sites = []
    for row in rows:
        assert row["offset_unit"] == "code_units_from_method_start"
        assert isinstance(row["instruction_offset"], int) and row["instruction_offset"] >= 0
        sites.append(
            (
                mapping[row["dex_entry"]],
                row["caller"],
                row["field_descriptor" if field else "callee"],
                row["instruction_offset"] * 2,
                row["opcode"],
                row["access"] if field else "invoke",
            )
        )
    return sorted(sites)


def competitor_sites(rows, sources, field):
    names = {row["container_entry"] for row in sources}
    sites = []
    for row in rows:
        assert row["dex_name"] in names
        assert row["match_type"] == ("field" if field else "method")
        caller = row["method_class"] + "->" + row["method_name"] + row["method_descriptor"]
        assert row["evidence"], "A caller group has no instruction evidence"
        for site in row["evidence"]:
            assert (
                isinstance(site["offset"], int) and site["offset"] >= 0 and site["offset"] % 2 == 0
            )
            assert site["access"] in ({"read", "write"} if field else {"invoke"})
            target = site["target_class"] + "->" + site["target_name"]
            target += (":" if field else "") + site["target_descriptor"]
            sites.append(
                (row["dex_name"], caller, target, site["offset"], site["opcode"], site["access"])
            )
    return sorted(sites)


def compare_sites(expected, actual):
    missing, extra = Counter(expected) - Counter(actual), Counter(actual) - Counter(expected)
    return {
        "status": "passed" if actual == expected else "failed",
        "expected_sites": len(expected),
        "actual_sites": len(actual),
        "expected_sites_sha256": fingerprint(expected),
        "actual_sites_sha256": fingerprint(actual),
        "missing_sites": sum(missing.values()),
        "extra_sites": sum(extra.values()),
        "missing_examples": [
            {"site": site, "count": count} for site, count in sorted(missing.items())[:5]
        ],
        "extra_examples": [
            {"site": site, "count": count} for site, count in sorted(extra.items())[:5]
        ],
    }


async def verify_native_collection(operations, collection, opened, query, expected, page_size):
    attempts = iter(
        op for op in operations if op["label"].startswith(collection["label"] + ":page:")
    )
    labels = []

    async def call(**params):
        attempt = next(attempts)
        assert attempt["tool"] == "asc_query_dex_session"
        assert attempt["arguments"] == {"session_id": opened["session_id"], **params}
        result = attempt["result"]
        assert result["session_id"] == opened["session_id"]
        if result["status"] == "ok":
            for key in ("input_id", "artifact_sha256", "sources"):
                assert result[key] == opened[key], f"Page provenance differs: {key}"
            labels.append(attempt["label"])
        return result

    result = await verify_pages(call, query, expected, page_size)
    assert next(attempts, None) is None, "Unaccounted reference response"
    assert labels == collection["page_labels"]
    assert result["response_limit_recoveries"] == [
        {**row, "code": "response_limit"} for row in collection["response_limit_recoveries"]
    ]
    return result


def collection_fields(trial, repeats):
    scenario = trial["scenario"]
    assert scenario in {"full_method", "full_field", "full_concurrent"}
    fields = [False, True] if scenario == "full_concurrent" else [scenario == "full_field"]
    expected = {
        f"query:{repeat}:{index}": field
        for repeat in range(repeats)
        for index, field in enumerate(fields)
    }
    collections = trial["reference_collections"]
    labels = [row["label"] for row in collections]
    assert len(labels) == len(expected) and set(labels) == set(expected), (
        "Missing, duplicate or unexpected complete collection"
    )
    return [(row, expected[row["label"]]) for row in collections]


def competitor_collection(operations, collection, opened, field, page_size):
    tool, params = queries(
        "competitor", opened["analysis_id"], "field" if field else "method", GRAPH_ROOT, 1
    )[0]
    params.pop("limit")
    attempts = [op for op in operations if op["label"].startswith(collection["label"] + ":page:")]
    assert attempts and not collection["response_limit_recoveries"]
    assert collection["page_labels"] == [op["label"] for op in attempts]
    rows, total, cursor = [], None, None
    for index, attempt in enumerate(attempts):
        assert attempt["label"] == f"{collection['label']}:page:{index}:attempt:0"
        assert attempt["tool"] == tool
        assert attempt["arguments"] == {**params, "limit": page_size, "cursor": cursor}
        assert attempt["status"] == "ok"
        response = attempt["result"]
        assert response.get("status", "ok") == "ok"
        assert response["total"] == (response["total"] if total is None else total)
        total = response["total"]
        hits = response["hits"]
        assert isinstance(hits, list) and len(hits) <= page_size
        rows.extend(hits)
        assert len(rows) <= total and (hits or len(rows) == total)
        cursor = response["next_cursor"]
        assert cursor == (str(len(rows)) if len(rows) < total else None)
        assert (cursor is None) == (index == len(attempts) - 1)
    assert len(rows) == total
    return rows, total


async def main(args):
    for key in (
        "receipt",
        "apk",
        "baseline_source",
        "java",
        "oracle_home",
        "competitor",
        "benchmark_source",
    ):
        setattr(args, key, getattr(args, key).resolve(strict=True))
    assert not args.output.exists(), "Preserve previous acceptance attempts"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    inputs = [
        args.receipt,
        args.apk,
        args.baseline_source,
        args.java,
        *sorted((args.oracle_home / "lib").glob("*.jar")),
        Path(__file__),
        Path(__file__).with_name("verify_mcp_reference_pages.py"),
        Path(__file__).with_name("verify_fuzzy_references.py"),
        args.benchmark_source,
    ]
    report = {
        "status": "running",
        "acceptance_inputs_sha256": {str(p): digest(p) for p in inputs},
        "runtime_sha256": runtime_identity(),
        "oracle_heap_mib": args.oracle_heap_mib,
        "scope": (
            "all reference pages and native diagnostics versus original bytes; every competitor "
            "site versus the same independent scanner; acceptance cost excluded from benchmark"
        ),
        "collections": [],
    }

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    try:
        save()
        receipt = json.loads(args.receipt.read_text())
        for trial in receipt["trials"]:
            if "operations_file" in trial:
                path = operation_receipt_path(args.receipt, trial)
                inputs.append(path)
                report["acceptance_inputs_sha256"][str(path)] = digest(path)
        assert (
            receipt["status"] == "passed"
            and receipt["input_unchanged"]
            and receipt["runtime_unchanged"]
        )
        assert receipt["competitor_runtime_unchanged"]
        assert receipt["apk_sha256"] == digest(args.apk)
        assert receipt["ours_runtime_sha256"] == report["runtime_sha256"]
        assert receipt["competitor_runtime"] == competitor_runtime_identity(args.competitor)
        assert receipt["harness_sha256"] == digest(args.benchmark_source)
        opened = next(
            trial_operations(args.receipt, t)[0]["result"]
            for t in receipt["trials"]
            if t["implementation"] == "ours"
        )
        assert opened["artifact_sha256"] == receipt["apk_sha256"]
        sources = opened["sources"]
        with tempfile.TemporaryDirectory(prefix="reference-page-oracle-") as directory:
            bundle = Path(directory) / "original.apk"
            original_bundle(
                args.apk, bundle, sources, receipt["ours_expansion_budget_mib"] * 1024**2
            )
            expected = {}
            for trial in receipt["trials"]:
                assert trial["status"] == "passed"
                assert trial["implementation"] in {"ours", "competitor"}
                operations = trial_operations(args.receipt, trial)
                for collection, field in collection_fields(trial, receipt["repeats"]):
                    operation, name, descriptor = QUERIES[int(field)]
                    if operation not in expected:
                        expected[operation] = await asyncio.to_thread(
                            oracle, args, bundle, operation, descriptor
                        )
                    truth = expected[operation]
                    sites = native_sites(truth["items"], sources, field)
                    row = {
                        "implementation": trial["implementation"],
                        "scenario": trial["scenario"],
                        "round": trial["round"],
                        "label": collection["label"],
                        "operation": operation,
                    }
                    report["collections"].append(row)
                    if trial["implementation"] == "ours":
                        result = await verify_native_collection(
                            operations,
                            collection,
                            operations[0]["result"],
                            {"operation": operation, name: descriptor},
                            truth,
                            receipt["full_collection_page_size"],
                        )
                        row.update(
                            status="passed",
                            total=result["total"],
                            pages=len(result["pages"]),
                            native_diagnostics_verified=True,
                            normalized_sites_sha256=fingerprint(sites),
                        )
                    else:
                        rows, total = competitor_collection(
                            operations,
                            collection,
                            operations[0]["result"],
                            field,
                            receipt["full_collection_page_size"],
                        )
                        row.update(
                            compare_sites(sites, competitor_sites(rows, sources, field)),
                            caller_groups=total,
                            pages=len(collection["page_labels"]),
                        )
                    save()
        assert not bundle.parent.exists()
        assert report["runtime_sha256"] == runtime_identity()
        assert report["acceptance_inputs_sha256"] == {str(p): digest(p) for p in inputs}
        assert sorted((args.oracle_home / "lib").glob("*.jar")) == [
            p for p in inputs if p.suffix == ".jar"
        ]
        report.update(
            status="passed"
            if all(r["status"] == "passed" for r in report["collections"])
            else "failed",
            input_runtime_oracle_unchanged=True,
            oracle_cleanup_verified=True,
        )
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        save()
    if report["status"] != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--oracle-home", type=Path, required=True)
    parser.add_argument("--competitor", type=Path, default=Path("artifacts/aimard-asc-mcp"))
    parser.add_argument(
        "--benchmark-source",
        type=Path,
        default=Path(__file__).with_name("benchmark_competitor_runtime.py"),
        help="Exact frozen benchmark source that produced this receipt",
    )
    parser.add_argument("--oracle-heap-mib", type=int, choices=range(128, 4097), default=1024)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
