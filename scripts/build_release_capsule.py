"""Build the privacy-safe 0.2.4 capsule from private, immutable cloud receipts.

Run only on the cloud acceptance machine, never on Actions or untrusted PR input:
  python -I scripts/build_release_capsule.py --manifest PRIVATE.json --output CAPSULE.json

Manifest schema 1: execution_environment, accepted_sha, ci_run_id, ci_run_attempt,
source_root; accepted_commit_json, accepted_recursive_tree_json and accepted_ci_run_json
(file references);
ci_wheel {path,sha256,installed_package_root}, inputs [{name,path,sha256,size_bytes,
version}], checks [{stage,input,check,reports:[file references],benchmarks:[file
references]}]. A file reference is {path,sha256}; report/benchmark references also
have execution, plan and driver references (each {path,sha256}). The plan binds
command/environment; driver names the exact executed immutable helper snapshot.
Supplemental_checks has eight {stage,check,input,report} entries; input is 'all'
for artifact summaries and one corpus name for method selection.

Identity files are trusted GitHub API responses, not caller success assertions.
The reviewer must independently associate those responses with the accepted run.
This is a bounded local validation/review contract, NOT remote cloud attestation.
No raw paths, descriptors, sites, errors, or private rows enter the output. Timing
ratios are deliberately not emitted, so failed comparators can never enter one.
"""

import argparse
import base64
import hashlib
import json
import os
import re
import zipfile
from pathlib import Path, PurePosixPath

CHECKS = frozenset(
    {
        "verify_preparation_directory",
        "verify_mcp_reference_pages",
        "verify_frontier_graph",
        "verify_graph_benchmark",
        "verify_reference_page_benchmark",
    }
)
INPUTS = {
    "taobao": (
        "10.62.0",
        91402818,
        "2d8844a2cefecb8b99f5e8dc83e3eabba39391b02e2dc27c562d8ba3d0755348",
    ),
    "wechat": (
        "8.0.74",
        261152116,
        "e69e7fef8de8211695f08fc22e8f374333246c2483e637ae317f7a0f15d564cf",
    ),
    "douyin": (
        "39.1.0",
        364994058,
        "c2b49cb5f85b8432e9c73a259c9eb9b8dd8d891e853177df2ce5a14ee4f3f5b9",
    ),
}
COMPARATOR_COMMIT = "848c711f1d80a1c2577283f1fa5f475ff734aa40"
COMPARATOR_SOURCES_SHA256 = "082dc4f112aacfb92e167a4ec9f9ac9eab89a6207626c91a59c005d602f1c6e0"
GRAPH_ROOT = (
    "Landroidx/core/content/FileProvider;->getUriForFile(Landroid/content/Context;"
    "Ljava/lang/String;Ljava/io/File;)Landroid/net/Uri;"
)
FRONTIER_ROOTS = {GRAPH_ROOT, "Ljava/lang/String;->equals(Ljava/lang/Object;)Z"}
WHEEL_NAME = "droidasc_mcp-0.2.4-cp311-abi3-manylinux_2_34_x86_64.whl"
SOURCE_SUFFIXES = {".py", ".java", ".c", ".json"}
RUNTIME_SUFFIXES = SOURCE_SUFFIXES | {".so", ".pyd"}
OPERATIONS = ("find_method_refs", "find_field_refs")
SCENARIOS = ("full_method", "full_field", "full_concurrent")
INDEX_SCOPE = (
    "complete declared call operands, method definitions/scan counts, and unresolved dynamic "
    "metadata in ordinary top-level multidex APKs (DEX 035/037/038/039/040 only); "
    "not DEX 041, runtime target resolution, or an independent graph traversal algorithm"
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def checked_sha(value, size=64):
    require(
        isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{size}}}", value), "Malformed digest"
    )
    return value


def integer(value, minimum=0):
    require(type(value) is int and value >= minimum, "Invalid integer count")
    return value


def file_hash(path):
    with Path(path).open("rb") as stream:
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_ref(ref):
    path = Path(ref["path"]).resolve(strict=True)
    raw = path.read_bytes()
    require(sha256(raw) == checked_sha(ref["sha256"]), "Raw file hash mismatch")
    value = json.loads(raw)
    require(isinstance(value, dict), "Expected JSON object")
    return path, value


def source_manifest(root):
    return {
        p.relative_to(root / "src/droidasc_mcp").as_posix(): file_hash(p)
        for p in sorted((root / "src/droidasc_mcp").rglob("*"))
        if p.is_file() and p.suffix in SOURCE_SUFFIXES
    }


def runtime_manifest(root):
    return {
        p.name: file_hash(p)
        for p in sorted(root.iterdir())
        if p.is_file() and p.suffix in RUNTIME_SUFFIXES
    }


def git_blob(path):
    raw = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def validate_source_identity(manifest, root):
    _, commit = read_ref(manifest["accepted_commit_json"])
    _, tree = read_ref(manifest["accepted_recursive_tree_json"])
    _, run = read_ref(manifest["accepted_ci_run_json"])
    require(
        run["id"] == manifest["ci_run_id"]
        and run["run_attempt"] == manifest["ci_run_attempt"]
        and run["head_sha"] == manifest["accepted_sha"]
        and run["status"] == "completed"
        and run["conclusion"] == "success",
        "CI run does not bind accepted source",
    )
    require(commit["sha"] == manifest["accepted_sha"], "Wrong accepted commit")
    require(commit["tree"]["sha"] == tree["sha"], "Wrong accepted tree")
    checked_sha(tree["sha"], 40)
    require(tree.get("truncated") is False, "Incomplete accepted Git tree")
    entries = tree["tree"]
    require(len({e["path"] for e in entries}) == len(entries), "Duplicate Git tree path")
    blobs = {e["path"]: e for e in entries if e["type"] == "blob"}
    source = source_manifest(root)
    require(source, "No accepted source")
    needed = {"src/droidasc_mcp/" + name for name in source}
    # Bind all helper/verifier source, not just the top-level executable.
    needed |= {p.relative_to(root).as_posix() for p in (root / "scripts").glob("*.py")}
    require(
        {
            p
            for p in blobs
            if p.startswith("src/droidasc_mcp/") and Path(p).suffix in SOURCE_SUFFIXES
        }
        == {"src/droidasc_mcp/" + name for name in source},
        "Accepted source inventory differs",
    )
    require(
        all(
            p in blobs
            and blobs[p]["mode"] in {"100644", "100755"}
            and git_blob(root / p) == blobs[p]["sha"]
            for p in needed
        ),
        "Local source/verifier bytes differ from accepted tree",
    )
    return source


def wheel_runtime(ref):
    path = Path(ref["path"]).resolve(strict=True)
    require(path.name == WHEEL_NAME, "Incorrect wheel asset")
    require(file_hash(path) == checked_sha(ref["sha256"]), "CI wheel byte hash mismatch")
    with zipfile.ZipFile(path) as wheel:
        names = wheel.namelist()
        require(len(names) == len(set(names)), "Duplicate wheel member")
        result = {}
        for name in names:
            if name.startswith("droidasc_mcp/") and not name.endswith("/"):
                relative = name.removeprefix("droidasc_mcp/")
                require(".." not in PurePosixPath(relative).parts, "Unsafe wheel member")
                result[relative] = sha256(wheel.read(name))
    require(result, "Empty wheel runtime")
    installed = Path(ref["installed_package_root"]).resolve(strict=True)
    files = {
        p.relative_to(installed).as_posix(): file_hash(p)
        for p in installed.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }
    require(files == result, "Installed runtime bytes do not equal the exact CI wheel")
    return result


def dependencies(report, required):
    bindings = report.get("acceptance_inputs_sha256", {})
    require(isinstance(bindings, dict), "Missing dependency map")
    for path, digest in bindings.items():
        require(file_hash(path) == checked_sha(digest), "Acceptance dependency changed")
    for path in required:
        require(
            bindings.get(str(path.resolve())) == file_hash(path), "Required dependency not bound"
        )


def stable(report, *fields):
    require(
        all(report.get(k) is True for k in fields),
        "Raw verifier reports unstable or incomplete execution",
    )
    require("error" not in report and "safety_stop" not in report, "Raw verifier error")


def validate_execution(ref, report_path, report, verifier, stage=None, installed_package_root=None):
    _, execution = read_ref(ref["execution"])
    require(execution["status"] == "completed", "Execution not complete")
    require(
        execution["raw_receipt_sha256"] == ref["sha256"]
        and execution["raw_status"] == report["status"],
        "Execution receipt mismatch",
    )
    command = execution["command"]
    _, plan = read_ref(ref["plan"])
    driver = ref["driver"]
    require(
        file_hash(driver["path"]) == checked_sha(driver["sha256"]) == execution["driver_sha256"],
        "Executed driver bytes differ",
    )
    matches = [
        row
        for row in plan["commands"]
        if row["command"] == command and Path(row["output"]).resolve() == report_path
    ]
    require(len(matches) == 1, "Execution is not in immutable run plan")
    environment = plan["environment_allowlist"]
    if stage == "source":
        require(
            environment.get("PYTHONPATH") == str(verifier.parent.parent / "src"),
            "Source plan does not select source runtime",
        )
    elif stage == "ci_wheel":
        require("PYTHONPATH" not in environment, "Wheel plan imports source PYTHONPATH")
        venv = Path(command[0]).absolute().parent.parent
        require(
            Path(installed_package_root).absolute().is_relative_to(venv),
            "Wheel interpreter differs from installed wheel environment",
        )
    require(
        len(command) > 3 and Path(command[1]).resolve() == verifier.resolve(),
        "Wrong executed verifier",
    )
    require(
        "--output" in command
        and Path(command[command.index("--output") + 1]).resolve() == report_path,
        "Execution output mismatch",
    )
    require("safety_stop" not in execution, "Execution safety stop")
    expected_exit = (
        1
        if report["status"] == "failed"
        and verifier.name
        in {"verify_reference_page_benchmark.py", "benchmark_competitor_runtime.py"}
        else 0
    )
    # Graph measured comparator failures may also cause nonzero exit, never waive product failures.
    require(execution["exit_code"] == expected_exit, "Unexpected execution exit code")
    before, after = execution["source_before"], execution["source_after"]
    require(before == after, "Source identity changed during execution")
    source_path = Path(before["manifest_path"]).resolve(strict=True)
    require(
        file_hash(source_path) == checked_sha(before["manifest_sha256"]),
        "Frozen source receipt changed",
    )
    frozen = json.loads(source_path.read_text())
    require(integer(before["files"], 1) == len(frozen), "Incomplete frozen source manifest")
    root = verifier.parent.parent
    for name, digest in frozen.items():
        relative = PurePosixPath(name)
        require(
            not relative.is_absolute() and ".." not in relative.parts, "Unsafe frozen source path"
        )
        require(file_hash(root / name) == checked_sha(digest), "Frozen source file changed")


def validate_index(index, apk_sha, runtime, root):
    require(
        index["schema"] == 2 and index["status"] == "all_persisted_call_sites_equal",
        "Independent index not accepted",
    )
    require(index["scope"] == INDEX_SCOPE, "Incomplete independent index scope")
    require(
        index["apk_sha256"] == apk_sha and index["runtime_sha256"] == runtime,
        "Independent index provenance mismatch",
    )
    stable(index, "original_unchanged", "runtime_unchanged", "verifier_unchanged")
    for key in (
        "bundle_sha256",
        "index_sha256",
        "site_multiset_sha256",
        "method_multiset_sha256",
        "dynamic_multiset_sha256",
    ):
        checked_sha(index[key])
    for key in ("index_bytes", "total_call_sites", "methods", "scanned_instructions"):
        integer(index[key], 1)
    for key in ("methods_without_code", "dynamic_sites"):
        integer(index[key])
    require(index["methods_without_code"] <= index["methods"], "Invalid method accounting")
    sources = index["sources"]
    require(isinstance(sources, list) and sources, "Empty original DEX inventory")
    require(
        index["sources_sha256"] == sha256(canonical(sources)), "Independent sources digest mismatch"
    )
    for row in sources:
        checked_sha(row["sha256"])
        require(
            row.get("dex_version") in {"035", "037", "038", "039", "040"}, "Unsupported DEX oracle"
        )
    identity = {
        "schema": 1,
        "engine": index["engine_version"],
        "dex_sha256": [r["sha256"] for r in sources],
    }
    require(
        index["input_id"] == sha256(json.dumps(identity, sort_keys=True).encode()),
        "Index input ID mismatch",
    )
    expected = {
        name: file_hash(root / "scripts" / name)
        for name in (
            "verify_call_index.py",
            "verify_fuzzy_references.py",
            "verify_mcp_reference_pages.py",
        )
    }
    require(index["verifier_sha256"] == expected, "Independent index verifier changed")
    decoder = index["decoder_identity"]
    require(decoder["name"] == "androguard" and decoder["version"], "Missing independent decoder")
    for rows in (decoder["python_sources_sha256"], decoder["mutf8"]["files_sha256"]):
        require(isinstance(rows, dict) and rows, "Missing decoder byte identity")
        for value in rows.values():
            checked_sha(value)
    return index["index_sha256"]


def validate_frontier(report, apk_sha, runtime, root):
    stable(report, "input_unchanged", "runtime_unchanged", "verifier_unchanged")
    index = report["independent_full_index"]
    digest = validate_index(index, apk_sha, runtime, root)
    require(
        report["sources"] == index["sources"] and report["input_id"] == index["input_id"],
        "Frontier index binding differs",
    )
    rows = report["queries"]
    require(rows, "Empty frontier result")
    seen = set()
    roots = set()
    for row in rows:
        query = row["query"]
        key = (query["method_descriptor"], query["direction"], query["depth"])
        require(key not in seen, "Duplicate frontier case")
        seen.add(key)
        roots.add(key[0])
        require(row["status"] == "passed" and row["exact_match"] is True, "Nested frontier failure")
        require(
            query["operation"] == "get_call_graph"
            and query["max_nodes"] == 500
            and query["max_edges"] == 1000,
            "Frontier bounds changed",
        )
        require(
            row["accepted_full_index_sha256"] == digest
            and row["independent_acceptance_sha256"] == sha256(canonical(index)),
            "Unbound frontier oracle",
        )
        checked_sha(row["graph_sha256"])
    require(
        roots == FRONTIER_ROOTS
        and seen
        == {(r, d, n) for r in roots for d in ("incoming", "outgoing", "both") for n in (1, 3, 5)},
        "Shortened frontier matrix",
    )
    return len(rows), digest


def collection_keys():
    return {
        (implementation, scenario, round_no, f"query:{repeat}:{index}", OPERATIONS[field])
        for implementation in ("ours", "competitor")
        for scenario in SCENARIOS
        for round_no in range(3)
        for repeat in range(2)
        for index, field in enumerate(
            [0, 1] if scenario == "full_concurrent" else [int(scenario == "full_field")]
        )
    }


def validate_comparator(report):
    require(report["competitor_commit"] == COMPARATOR_COMMIT, "Unapproved comparator commit")
    identity = report["competitor_runtime"]
    sources = identity["python_sources_sha256"]
    require(
        sha256(canonical(sources)) == COMPARATOR_SOURCES_SHA256,
        "Comparator source bytes differ from pinned commit",
    )
    installed = Path(identity["root"]).resolve(strict=True)
    actual = {p.relative_to(installed).as_posix(): file_hash(p) for p in installed.rglob("*.py")}
    require(actual == sources, "Installed comparator bytes changed")


def validate_benchmark(report, apk_sha, runtime, root, graph=False):
    require(
        report["apk_sha256"] == apk_sha and report["ours_runtime_sha256"] == runtime,
        "Measured runtime/input mismatch",
    )
    stable(report, "input_unchanged", "runtime_unchanged", "competitor_runtime_unchanged")
    validate_comparator(report)
    budgets = {
        "memory_cap_mib": 4096,
        "ours_session_disk_budget_mib": 8192,
        "external_temporary_logical_cap_mib": 8192,
        "ours_expansion_budget_mib": 512,
        "full_collection_page_size": 1000,
        "graph_depth": 3,
        "timeout_per_call_seconds": 30 if graph else 180,
    }
    require(
        all(report.get(k) == v for k, v in budgets.items()),
        "Measurement budget differs from frozen protocol",
    )
    require(
        report["harness_sha256"] == file_hash(root / "scripts/benchmark_competitor_runtime.py")
        and report["cpu_wrapper_sha256"] == file_hash(root / "scripts/benchmark_cpu_wrapper.py"),
        "Measured harness mismatch",
    )
    require(
        report["timing_version"] == 2
        and report["cpu_budget_version"] == 1
        and report["external_call_deadline_version"] == 1,
        "Incomplete measurement protocol",
    )
    cpus = report["workers"]
    require(cpus in (2, 4) and len(set(report["cpu_affinity"])) == cpus, "Wrong CPU budget")
    require(report["repeats"] == 2, "Shortened repeat matrix")
    scenarios = ("graph",) if graph else SCENARIOS
    expected = [
        (i, s, n)
        for n in range(3)
        for s in scenarios
        for i in (("competitor", "ours") if n % 2 else ("ours", "competitor"))
    ]
    trials = report["trials"]
    require(
        [(t["implementation"], t["scenario"], t["round"]) for t in trials] == expected,
        "Incomplete or non-alternating measured matrix",
    )
    for trial in trials:
        integer(trial["cpu_affinity_samples"], 1)
        if trial["implementation"] == "ours" or not graph:
            require(trial["status"] == "passed", "Product measured trial failed")
        if trial["implementation"] == "ours":
            require(
                "safety_stop" not in trial and "error" not in trial,
                "Product measured safety/error failure",
            )
            opened = trial["operations"][0]["result"]
            require(
                opened["status"] == "ok" and opened["artifact_sha256"] == apk_sha,
                "Wrong measured input",
            )
        if graph and trial["implementation"] == "ours":
            measured = [op for op in trial["operations"] if op["label"].startswith("query:")]
            for operation in measured:
                params = operation["arguments"]
                require(
                    params["method_descriptor"] == GRAPH_ROOT
                    and params["depth"] == 3
                    and params["direction"] == "both"
                    and params["max_nodes"] == 500
                    and params["max_edges"] == 1000,
                    "Measured graph workload changed",
                )
            require(
                [op["label"] for op in measured] == ["query:0:0", "query:1:0"]
                and all(op["status"] == "ok" for op in measured),
                "Incomplete measured graph operations",
            )
        elif not graph:
            fields = (
                [0, 1]
                if trial["scenario"] == "full_concurrent"
                else [int(trial["scenario"] == "full_field")]
            )
            wanted = {
                f"query:{repeat}:{index}" for repeat in range(2) for index, _ in enumerate(fields)
            }
            collections = trial["reference_collections"]
            require(
                len(collections) == len(wanted) and {c["label"] for c in collections} == wanted,
                "Incomplete measured reference collections",
            )
            labels = {op["label"] for op in trial["operations"]}
            for collection in collections:
                require(
                    collection["page_labels"]
                    and len(collection["page_labels"]) == len(set(collection["page_labels"]))
                    and set(collection["page_labels"]) <= labels,
                    "Missing measured reference pages",
                )
    require(
        report["status"]
        == ("passed" if all(t["status"] == "passed" for t in trials) else "failed"),
        "Wrong measurement aggregate status",
    )
    if not graph:
        require(report["status"] == "passed", "Reference measurement failed")
    return cpus


def validate_reference(report, measurement, apk_name):
    stable(report, "input_runtime_oracle_unchanged", "oracle_cleanup_verified")
    rows = report["collections"]
    actual = [
        (r["implementation"], r["scenario"], r["round"], r["label"], r["operation"]) for r in rows
    ]
    require(
        len(actual) == len(set(actual)) and set(actual) == collection_keys(),
        "Shortened reference collection matrix",
    )
    failures = []
    ours = {
        (r["scenario"], r["round"], r["label"], r["operation"]): r
        for r in rows
        if r["implementation"] == "ours"
    }
    for row in rows:
        integer(row["pages"], 1)
        if row["implementation"] == "ours":
            require(
                row["status"] == "passed" and row["native_diagnostics_verified"] is True,
                "Nested product collection failed",
            )
            integer(row["total"])
            checked_sha(row["normalized_sites_sha256"])
            # Native verifier proves exact rows; older raw schema omits explicit zero counts.
            require(
                row.get("missing_sites", 0) == 0 and row.get("extra_sites", 0) == 0,
                "Product site mismatch",
            )
        else:
            corresponding = ours[(row["scenario"], row["round"], row["label"], row["operation"])]
            require(
                row["expected_sites_sha256"] == corresponding["normalized_sites_sha256"]
                and row["expected_sites"] == corresponding["total"],
                "Comparator oracle differs from product oracle",
            )
            expected, actual_count = integer(row["expected_sites"]), integer(row["actual_sites"])
            missing, extra = integer(row["missing_sites"]), integer(row["extra_sites"])
            checked_sha(row["expected_sites_sha256"])
            checked_sha(row["actual_sites_sha256"])
            require(actual_count == expected - missing + extra, "Comparator count inconsistency")
            if row["status"] == "passed":
                require(
                    missing == extra == 0
                    and row["expected_sites_sha256"] == row["actual_sites_sha256"],
                    "Comparator false pass",
                )
            else:
                require(
                    row["status"] == "failed"
                    and apk_name == "taobao"
                    and row["operation"] == "find_field_refs"
                    and missing == 0
                    and extra > 0,
                    "Unknown comparator failure, cannot waive",
                )
                failures.append(row)
    require(
        report["status"] == ("failed" if failures else "passed"),
        "Incorrect reference aggregate status",
    )
    return len([r for r in rows if r["implementation"] == "ours"]), failures


def validate_graph(report, benchmarks, apk_sha, runtime, root):
    stable(report, "input_runtime_oracles_unchanged", "cleanup_verified")
    index = report["independent_full_index"]
    digest = validate_index(index, apk_sha, runtime, root)
    emitted = report["independent_emitted_sites"]
    require(emitted["status"] == "passed", "Independent emitted sites failed")
    integer(emitted["matched_unique_call_sites"])
    expected = {
        (str(path), n, f"query:{repeat}:0")
        for path, _ in benchmarks
        for n in range(3)
        for repeat in range(2)
    }
    rows = report["graphs"]
    actual = [(r["receipt"], r["round"], r["label"]) for r in rows]
    require(
        len(actual) == len(set(actual)) and set(actual) == expected,
        "Shortened measured graph acceptance",
    )
    for row in rows:
        require(
            row["status"] == "passed" and row["exact_full_index_match"] is True,
            "Nested graph failure",
        )
        require(
            row["accepted_index_sha256"] == digest
            and row["independent_acceptance_sha256"] == sha256(canonical(index)),
            "Unbound graph oracle",
        )
        checked_sha(row["graph_sha256"])
    failed = [
        (str(path), t["round"])
        for path, b in benchmarks
        for t in b["trials"]
        if t["implementation"] == "competitor" and t["status"] != "passed"
    ]
    require(
        sorted((f["receipt"], f["round"]) for f in report["competitor_failures"]) == sorted(failed),
        "Lost comparator graph failures",
    )
    return len(rows), digest, report["competitor_failures"]


def validate_supplemental(manifest, root, runtimes, inputs):
    rows = manifest["supplemental_checks"]
    expected = {(stage, "verify_method_selection", name) for stage in runtimes for name in INPUTS}
    expected |= {(stage, "verify_artifact_summary", "all") for stage in runtimes}
    keys = [(r["stage"], r["check"], r["input"]) for r in rows]
    require(len(keys) == 8 and set(keys) == expected, "Incomplete supplemental eight-check matrix")
    result = []
    for row in sorted(rows, key=lambda r: (r["stage"], r["check"], r["input"])):
        stage, check = row["stage"], row["check"]
        verifier = root / "scripts" / (check + ".py")
        ref = row["report"]
        path, report = read_ref(ref)
        validate_execution(
            ref, path, report, verifier, stage, manifest["ci_wheel"]["installed_package_root"]
        )
        require(
            report["status"] == "passed"
            and report["runtime_sha256"] == runtimes[stage]
            and report["verifier_sha256"] == file_hash(verifier),
            "Supplemental status/runtime/verifier mismatch",
        )
        stable(report, "input_runtime_and_verifier_unchanged")
        validate_comparator(report)
        if check == "verify_method_selection":
            hashes = [inputs[row["input"]]["sha256"]]
            require(report["apk_sha256"] == hashes[0], "Method input mismatch")
            operations = report["operations"]
            required = {
                "disassemble_method",
                "get_method_source",
                "get_method_calls",
                "find_method_refs",
                "get_call_graph",
            }
            require(
                len(operations) == 5 and {r["operation"] for r in operations} == required,
                "Incomplete named-method matrix",
            )
            for operation in operations:
                require(operation["status"] == "passed", "Nested method-selection failure")
                checked_sha(operation["response_sha256"])
            require(
                report["overload_recovery"]
                == report["competitor_disassembly_and_ambiguity"]
                == "passed",
                "Method overload/comparator failure",
            )
            require(report["selected"]["instructions"], "Missing independent method instructions")
            integer(report["overloaded"]["candidate_count"], 2)
            cases = len(operations)
        else:
            hashes = sorted(i["sha256"] for i in inputs.values())
            artifacts = report["artifacts"]
            require(
                len(artifacts) == 3 and sorted(a["sha256"] for a in artifacts) == hashes,
                "Incomplete artifact-summary inputs",
            )
            for artifact in artifacts:
                require(artifact["status"] == "passed", "Nested artifact-summary failure")
                original = next(i for i in inputs.values() if i["sha256"] == artifact["sha256"])
                require(
                    artifact["size_bytes"] == original["size_bytes"]
                    and Path(artifact["path"]).resolve() == Path(original["path"]).resolve(),
                    "Summary input provenance mismatch",
                )
                integer(artifact["dex_count"], 1)
                summary = artifact["summary"]
                require(
                    summary["manifest"]["status"] == "ok"
                    and summary["manifest"]["resource_values_resolved"] is False
                    and summary["native_scope"] == "archive",
                    "Incomplete nested artifact summary",
                )
                integer(summary["entry_count"], 1)
            cases = len(artifacts)
        evidence = {
            "stage": stage,
            "check": check,
            "input_sha256s": hashes,
            "raw_receipt_sha256": ref["sha256"],
            "status": "passed",
            "input_unchanged": True,
            "runtime_unchanged": True,
            "product_cases": cases,
            "product_failures": 0,
            "oracle_match": True,
            "verifier_sha256": file_hash(verifier),
            "runtime_sha256": runtimes[stage],
        }
        raw = canonical(evidence)
        result.append(
            {"evidence_base64": base64.b64encode(raw).decode(), "evidence_sha256": sha256(raw)}
        )
    return result


def build_capsule(manifest):
    require(
        manifest["schema"] == 1 and manifest["execution_environment"] == "dot-cloud",
        "Cloud manifest required",
    )
    require(not os.environ.get("GITHUB_ACTIONS"), "Private raw evidence must not run in Actions")
    checked_sha(manifest["accepted_sha"], 40)
    for key in ("ci_run_id", "ci_run_attempt"):
        integer(manifest[key], 1)
    root = Path(manifest["source_root"]).resolve(strict=True)
    source = validate_source_identity(manifest, root)
    runtimes = {
        "source": runtime_manifest(root / "src/droidasc_mcp"),
        "ci_wheel": wheel_runtime(manifest["ci_wheel"]),
    }
    require(
        {name: runtimes["source"].get(name) for name in source} == source, "Source runtime differs"
    )
    inputs = manifest["inputs"]
    require(
        len(inputs) == 3 and {i["name"] for i in inputs} == set(INPUTS),
        "Three exact original inputs required",
    )
    for row in inputs:
        require(
            (row["version"], row["size_bytes"], row["sha256"]) == INPUTS[row["name"]],
            "Wrong original corpus identity",
        )
        require(
            Path(row["path"]).stat().st_size == row["size_bytes"]
            and file_hash(row["path"]) == row["sha256"],
            "Original input bytes differ",
        )
    by_name = {row["name"]: row for row in inputs}
    checks = manifest["checks"]
    keys = [(row["stage"], row["input"], row["check"]) for row in checks]
    expected = {(stage, name, check) for stage in runtimes for name in INPUTS for check in CHECKS}
    require(
        len(keys) == len(expected) and set(keys) == expected, "Incomplete mandatory 30-check matrix"
    )
    # A path may appear only once: copied stage labels cannot reuse source execution.
    all_refs = [
        (row["stage"], ref) for row in checks for ref in row["reports"] + row.get("benchmarks", [])
    ]
    all_refs += [(row["stage"], row["report"]) for row in manifest["supplemental_checks"]]
    raw_paths = [str(Path(ref["path"]).resolve()) for _, ref in all_refs]
    execution_paths = [str(Path(ref["execution"]["path"]).resolve()) for _, ref in all_refs]
    require(
        len(raw_paths) == len(set(raw_paths)) and len(execution_paths) == len(set(execution_paths)),
        "Reused execution across corpus gates",
    )
    interpreters = {stage: set() for stage in runtimes}
    for stage, ref in all_refs:
        _, execution = read_ref(ref["execution"])
        interpreters[stage].add(execution["command"][0])
    require(
        all(len(values) == 1 for values in interpreters.values())
        and interpreters["source"] != interpreters["ci_wheel"],
        "Distinct source and wheel interpreters required",
    )
    projected = []
    for item in sorted(checks, key=lambda r: (r["stage"], r["input"], r["check"])):
        stage, name, check = item["stage"], item["input"], item["check"]
        apk_sha, runtime = by_name[name]["sha256"], runtimes[stage]
        verifier = root / "scripts" / (check + ".py")
        reports = []
        for ref in item["reports"]:
            path, report = read_ref(ref)
            validate_execution(
                ref, path, report, verifier, stage, manifest["ci_wheel"]["installed_package_root"]
            )
            require(report["runtime_sha256"] == runtime, "Stale raw runtime")
            if "apk_sha256" in report:
                require(report["apk_sha256"] == apk_sha, "Stale raw input")
            if "verifier_sha256" in report:
                require(report["verifier_sha256"] == file_hash(verifier), "Stale raw verifier")
            else:
                dependencies(report, [verifier])
            require(
                report["status"] == "passed" or check == "verify_reference_page_benchmark",
                "Raw product gate failed",
            )
            reports.append((path, report))
        require(
            len(reports) == (2 if check == "verify_reference_page_benchmark" else 1),
            "Wrong raw report count",
        )
        benchmarks = []
        for ref in item.get("benchmarks", []):
            path, report = read_ref(ref)
            validate_execution(
                ref,
                path,
                report,
                root / "scripts/benchmark_competitor_runtime.py",
                stage,
                manifest["ci_wheel"]["installed_package_root"],
            )
            benchmarks.append((path, report))
        count, failures, index_digest = 0, [], None
        if check in {"verify_reference_page_benchmark", "verify_graph_benchmark"}:
            require(
                len(benchmarks) == 2
                and {
                    validate_benchmark(b, apk_sha, runtime, root, check == "verify_graph_benchmark")
                    for _, b in benchmarks
                }
                == {2, 4},
                "Missing 2/4 CPU measurements",
            )
        else:
            require(not benchmarks, "Unexpected benchmark inputs")
        report = reports[0][1]
        if check == "verify_preparation_directory":
            stable(
                report,
                "input_unchanged",
                "runtime_unchanged",
                "snapshot_bytes_match_original",
                "common_metadata_exact_match",
            )
            integer(report["dex_count"], 1)
            count = integer(report["exact_classes_and_owners"], 1)
            checked_sha(report["ordered_class_owner_sha256"])
        elif check == "verify_mcp_reference_pages":
            stable(report, "input_runtime_oracle_unchanged", "cleanup_verified")
            rows = report["operations"]
            require(
                len(rows) == 2 and {r["operation"] for r in rows} == set(OPERATIONS),
                "Incomplete MCP reference matrix",
            )
            for row in rows:
                require(row["status"] == "passed", "Nested MCP reference failure")
                checked_sha(row["full_result_sha256"])
                offset = 0
                require(row["pages"], "Missing reference pages")
                for page in row["pages"]:
                    require(page["offset"] == offset, "Reference continuation gap")
                    offset += integer(page["count"])
                    checked_sha(page["items_sha256"])
                require(offset == integer(row["total"]), "Incomplete reference rows")
            count = len(rows)
        elif check == "verify_frontier_graph":
            count, index_digest = validate_frontier(report, apk_sha, runtime, root)
        elif check == "verify_reference_page_benchmark":
            seen = set()
            for _, report in reports:
                candidates = [
                    (path, b)
                    for path, b in benchmarks
                    if str(path) in report["acceptance_inputs_sha256"]
                ]
                require(len(candidates) == 1, "Reference acceptance not bound to one measurement")
                path, measured = candidates[0]
                require(path not in seen, "Duplicate reference acceptance")
                seen.add(path)
                dependencies(report, [path, verifier, Path(by_name[name]["path"])])
                cases, failed = validate_reference(report, measured, name)
                count += cases
                failures.extend(failed)
        else:
            dependencies(
                report, [verifier, Path(by_name[name]["path"]), *(p for p, _ in benchmarks)]
            )
            count, index_digest, failures = validate_graph(
                report, benchmarks, apk_sha, runtime, root
            )
        raw_hashes = sorted(ref["sha256"] for ref in item["reports"])
        evidence = {
            "stage": stage,
            "check": check,
            "input_sha256": apk_sha,
            "raw_receipt_sha256": raw_hashes[0]
            if len(raw_hashes) == 1
            else sha256(canonical(raw_hashes)),
            "raw_receipt_sha256s": raw_hashes,
            "raw_status": "failed"
            if any(r["status"] == "failed" for _, r in reports)
            else "passed",
            "status": "passed",
            "input_unchanged": True,
            "runtime_unchanged": True,
            "product_results_complete": True,
            "oracle_match": True,
            "product_cases": count,
            "product_failures": 0,
            "product_missing_sites": 0,
            "product_extra_sites": 0,
            "verifier_sha256": file_hash(verifier),
            "runtime_sha256": runtime,
            "competitor": {
                "failed_cases": len(failures),
                "failures_sha256": sha256(canonical(failures)),
                "failed_cases_excluded_from_ratios": True,
            },
        }
        if index_digest:
            evidence["independent_call_index_sha256"] = index_digest
        if benchmarks:
            evidence["benchmark_receipts"] = sorted(
                [
                    {
                        "sha256": file_hash(path),
                        "raw_status": measured["status"],
                        "logical_cpus": measured["workers"],
                    }
                    for path, measured in benchmarks
                ],
                key=lambda r: r["logical_cpus"],
            )
            evidence["measurement_protocol"] = {
                "logical_cpus": [2, 4],
                "alternating_rounds": 3,
                "repeats": 2,
                "scenarios": ["graph"] if check == "verify_graph_benchmark" else list(SCENARIOS),
            }
        raw = canonical(evidence)
        projected.append(
            {"evidence_sha256": sha256(raw), "evidence_base64": base64.b64encode(raw).decode()}
        )
    supplemental = validate_supplemental(manifest, root, runtimes, by_name)
    return {
        "schema": 1,
        "execution_environment": "dot-cloud",
        "status": "passed",
        "capsule_builder_sha256": file_hash(__file__),
        "supplemental_checks": supplemental,
        **{k: manifest[k] for k in ("accepted_sha", "ci_run_id", "ci_run_attempt")},
        "source_manifest_sha256": sha256(canonical(source)),
        "ci_wheel": {
            "asset_name": WHEEL_NAME,
            "sha256": manifest["ci_wheel"]["sha256"],
            "installed_byte_identity_passed": True,
        },
        "inputs": [
            {k: row[k] for k in ("name", "sha256", "size_bytes", "version")}
            for row in sorted(inputs, key=lambda r: r["name"])
        ],
        "checks": projected,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    capsule = build_capsule(json.loads(args.manifest.read_text()))
    raw = canonical(capsule) + b"\n"
    with args.output.open("xb") as stream:
        stream.write(raw)
    print(
        json.dumps(
            {"capsule_sha256": sha256(raw), "checks": len(capsule["checks"]), "status": "passed"}
        )
    )


if __name__ == "__main__":
    main()
