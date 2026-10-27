"""Verify full string/type MCP benchmark receipts against original-byte Androguard decoding.

Run after timing. This verifier accepts only the fixed literal benchmark selectors,
preserves duplicate sites and compares byte offsets, not caller-group counts.
"""

import argparse
import asyncio
import gc
import importlib.metadata
import json
import tempfile
import zipfile
from pathlib import Path

from benchmark_competitor_runtime import (
    GRAPH_ROOT,
    collect_reference_pages,
    competitor_runtime_identity,
    operation_receipt_path,
    queries,
    trial_operations,
)
from verify_mcp_reference_pages import digest, original_bundle, runtime_identity
from verify_reference_page_benchmark import compare_sites


def oracle(bundle, sources):
    from androguard.core.dex import DEX
    from loguru import logger

    logger.remove()
    sites = {"string": [], "type": []}
    string_indexes = {}
    methods = instructions = without_code = 0
    with zipfile.ZipFile(bundle) as archive:
        for source in sources:
            dex = DEX(archive.read(source["dex_entry"]))
            for cls in dex.get_classes():
                for method in cls.get_methods():
                    methods += 1
                    without_code += method.get_code() is None
                    caller = (
                        method.get_class_name()
                        + "->"
                        + method.get_name()
                        + "".join(method.get_descriptor().split())
                    )
                    for offset, instruction in method.get_instructions_idx():
                        instructions += 1
                        opcode = instruction.get_name()
                        if opcode in {"const-string", "const-string/jumbo"}:
                            kind = "string"
                            value = dex.get_cm_string(instruction.get_ref_kind())
                            match = "https://" in value
                        elif opcode in {
                            "const-class",
                            "check-cast",
                            "instance-of",
                            "new-instance",
                            "new-array",
                            "filled-new-array",
                            "filled-new-array/range",
                        }:
                            kind = "type"
                            value = dex.get_cm_type(instruction.get_ref_kind())
                            match = "Ljava/lang/String;" in value
                        else:
                            continue
                        if match:
                            assert offset >= 0 and offset % 2 == 0
                            site = (source["container_entry"], caller, value, offset, opcode)
                            sites[kind].append(site)
                            if kind == "string":
                                string_indexes[site] = instruction.get_ref_kind()
            cls = method = None
            del dex
            gc.collect()
            print(
                json.dumps(
                    {
                        "decoded": source["container_entry"],
                        "sites": {k: len(v) for k, v in sites.items()},
                    }
                ),
                flush=True,
            )
    return (
        {k: sorted(v) for k, v in sites.items()},
        string_indexes,
        {
            "scanned_methods": methods,
            "scanned_instructions": instructions,
            "methods_without_code": without_code,
            "scan_errors": 0,
            "instruction_scan_complete": True,
        },
    )


def native_sites(rows, sources, kind):
    mapping = {r["dex_entry"]: r["container_entry"] for r in sources}
    sites = []
    for row in rows:
        assert row["offset_unit"] == "code_units_from_method_start"
        offset = row["instruction_offset"]
        assert type(offset) is int and offset >= 0
        sites.append(
            (
                mapping[row["dex_entry"]],
                row["caller"],
                row["value" if kind == "string" else "type_descriptor"],
                offset * 2,
                row["opcode"],
            )
        )
    return sorted(sites)


def competitor_sites(rows, sources, kind):
    names = {r["container_entry"] for r in sources}
    sites = []
    for row in rows:
        assert row["dex_name"] in names and row["match_type"] == kind
        caller = row["method_class"] + "->" + row["method_name"] + row["method_descriptor"]
        assert row["evidence"], "Caller group has no operand evidence"
        for evidence in row["evidence"]:
            offset = evidence["offset"]
            assert type(offset) is int and offset >= 0 and offset % 2 == 0
            assert evidence["access"] == ("load" if kind == "string" else "type-use")
            target = evidence["target_value" if kind == "string" else "target_descriptor"]
            assert isinstance(target, str)
            sites.append((row["dex_name"], caller, target, offset, evidence["opcode"]))
    return sorted(sites)


def collection_kinds(trial, repeats):
    assert trial["scenario"] in {"full_string", "full_type", "full_operands"}
    kinds = (
        ["string", "type"]
        if trial["scenario"] == "full_operands"
        else [trial["scenario"].removeprefix("full_")]
    )
    expected = {f"query:{r}:{i}": kind for r in range(repeats) for i, kind in enumerate(kinds)}
    collections = trial["reference_collections"]
    labels = [c["label"] for c in collections]
    assert len(labels) == len(expected) and set(labels) == set(expected)
    return [(c, expected[c["label"]]) for c in collections]


async def replay(operations, collection, implementation, opened, kind, page_size, diagnostics):
    ours = implementation == "ours"
    tool, params = queries(
        implementation, opened["session_id" if ours else "analysis_id"], kind, GRAPH_ROOT, 3
    )[0]
    attempts = iter(
        op for op in operations if op["label"].startswith(collection["label"] + ":page:")
    )

    async def call(label, expected_tool, arguments, **kwargs):
        attempt = next(attempts, None)
        assert attempt is not None, "Missing recorded page attempt"
        assert attempt["label"] == label and attempt["tool"] == expected_tool
        assert attempt["arguments"] == arguments
        response = attempt["result"]
        limited = response.get("status") == "error" and response.get("code") == "response_limit"
        assert attempt["status"] == ("response_limit" if limited else "ok")
        if ours:
            assert response["session_id"] == opened["session_id"]
            if not limited:
                for key in ("input_id", "artifact_sha256", "sources"):
                    assert response[key] == opened[key], f"Page provenance differs: {key}"
                for key, expected in diagnostics.items():
                    assert response[key] == expected, f"Page diagnostic differs: {key}"
        return response

    result, labels, recoveries = await collect_reference_pages(
        call, implementation, tool, params, collection["label"], page_size
    )
    assert next(attempts, None) is None, "Unaccounted recorded page attempt"
    assert labels == collection["page_labels"]
    assert recoveries == collection["response_limit_recoveries"]
    return result


async def main(args):
    import androguard

    assert not args.output.exists(), "Preserve previous acceptance attempts"
    inputs = [
        args.receipt,
        args.apk,
        Path(__file__),
        *[
            Path(__file__).with_name(name)
            for name in (
                "benchmark_competitor_runtime.py",
                "benchmark_cpu_wrapper.py",
                "verify_mcp_reference_pages.py",
                "verify_reference_page_benchmark.py",
                "verify_fuzzy_references.py",
            )
        ],
    ]
    inputs.extend(sorted(Path(androguard.__file__).parent.rglob("*.py")))

    def identity():
        return {str(p.resolve()): digest(p) for p in inputs}

    report = {
        "status": "running",
        "scope": __doc__,
        "acceptance_inputs_sha256": identity(),
        "runtime_sha256": runtime_identity(),
        "oracle_version": importlib.metadata.version("androguard"),
        "collections": [],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    try:
        save()
        receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        for trial in receipt["trials"]:
            if "operations_file" in trial:
                path = operation_receipt_path(args.receipt, trial)
                inputs.append(path)
                report["acceptance_inputs_sha256"][str(path.resolve())] = digest(path)
        assert receipt["status"] == "passed" and all(
            receipt[k]
            for k in ("input_unchanged", "runtime_unchanged", "competitor_runtime_unchanged")
        )
        assert receipt["apk_sha256"] == digest(args.apk)
        assert receipt["ours_runtime_sha256"] == report["runtime_sha256"]
        assert (
            receipt["competitor_runtime"]["python_sources_sha256"]
            == competitor_runtime_identity(args.competitor)["python_sources_sha256"]
        )
        assert receipt["harness_sha256"] == digest(inputs[3])
        assert receipt["cpu_wrapper_sha256"] == digest(inputs[4])
        trials = receipt["trials"]
        keys = [(t["round"], t["scenario"], t["implementation"]) for t in trials]
        expected_keys = {
            (r, s, i)
            for r in range(max(t["round"] for t in trials) + 1)
            for s in {t["scenario"] for t in trials}
            for i in ("ours", "competitor")
        }
        assert len(keys) == len(expected_keys) and set(keys) == expected_keys
        opened = next(
            trial_operations(args.receipt, t)[0]["result"]
            for t in trials
            if t["implementation"] == "ours"
        )
        assert opened["artifact_sha256"] == receipt["apk_sha256"]
        sources = opened["sources"]
        with tempfile.TemporaryDirectory(prefix="operand-page-oracle-") as directory:
            bundle = Path(directory) / "original.apk"
            original_bundle(
                args.apk, bundle, sources, receipt["ours_expansion_budget_mib"] * 1024**2
            )
            expected, indexes, diagnostics = await asyncio.to_thread(oracle, bundle, sources)
            report["oracle_diagnostics"] = diagnostics
            for trial in trials:
                assert trial["status"] == "passed"
                operations = trial_operations(args.receipt, trial)
                ours = trial["implementation"] == "ours"
                trial_open = operations[0]["result"]
                assert operations[0]["label"] == "open" and operations[0]["status"] == "ok"
                assert operations[-1]["label"] == "close" and operations[-1]["status"] == "ok"
                if ours:
                    assert trial_open["sources"] == sources
                    assert trial_open["artifact_sha256"] == receipt["apk_sha256"]
                collections = collection_kinds(trial, receipt["repeats"])
                assert all(
                    op["label"] in {"open", "close"}
                    or any(op["label"].startswith(c["label"] + ":page:") for c, _ in collections)
                    for op in operations
                ), "Unaccounted query operation"
                for collection, kind in collections:
                    result = await replay(
                        operations,
                        collection,
                        trial["implementation"],
                        trial_open,
                        kind,
                        receipt["full_collection_page_size"],
                        diagnostics,
                    )
                    rows = result["items" if ours else "hits"]
                    actual = (native_sites if ours else competitor_sites)(rows, sources, kind)
                    comparison = compare_sites(expected[kind], actual)
                    if ours and kind == "string" and comparison["status"] == "passed":
                        for row in rows:
                            assert (
                                row["string_index"]
                                == indexes[native_sites([row], sources, kind)[0]]
                            )
                    report["collections"].append(
                        {
                            "implementation": trial["implementation"],
                            "scenario": trial["scenario"],
                            "round": trial["round"],
                            "label": collection["label"],
                            "kind": kind,
                            "pages": len(collection["page_labels"]),
                            "reported_total": result["total"],
                            "native_diagnostics_verified": ours,
                            **comparison,
                        }
                    )
                    save()
        assert not bundle.parent.exists()
        assert report["acceptance_inputs_sha256"] == identity()
        assert report["runtime_sha256"] == runtime_identity()
        report.update(
            status="passed"
            if all(c["status"] == "passed" for c in report["collections"])
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
    parser.add_argument("--competitor", type=Path, default=Path("artifacts/aimard-asc-mcp"))
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
