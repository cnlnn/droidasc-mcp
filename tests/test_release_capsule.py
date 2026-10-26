"""Synthetic contract tests; these fixtures are NEVER release evidence."""

import base64
import copy
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

MODULE = Path(__file__).parents[1] / "scripts/build_release_capsule.py"
spec = importlib.util.spec_from_file_location("capsule_builder", MODULE)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
H = "a" * 64


class CapsuleTests(unittest.TestCase):
    def setUp(self):
        # The suite tests the cloud-only builder with synthetic local evidence even
        # when the test process itself is Actions; production CLI still rejects it.
        environment = {k: v for k, v in b.os.environ.items() if k != "GITHUB_ACTIONS"}
        cloud_test = patch.dict(b.os.environ, environment, clear=True)
        cloud_test.start()
        self.addCleanup(cloud_test.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # Windows TEMP may use a short-name/case alias which resolve() expands.
        # Raw verifier receipts bind resolved paths, so create the entire fixture
        # under one canonical root before serializing any path-keyed evidence.
        self.base = Path(self.temp.name).resolve(strict=True)
        self.root = self.base / "source"
        (self.root / "src/droidasc_mcp").mkdir(parents=True)
        (self.root / "scripts").mkdir()
        (self.root / "src/droidasc_mcp/__init__.py").write_text("# fixture only\n")
        scripts = b.CHECKS | {
            "verify_call_index",
            "verify_fuzzy_references",
            "benchmark_competitor_runtime",
            "benchmark_cpu_wrapper",
            "verify_method_selection",
            "verify_artifact_summary",
        }
        for name in scripts:
            (self.root / "scripts" / (name + ".py")).write_text("# fixture " + name + "\n")
        (self.root / "scripts/build_release_capsule.py").write_bytes(MODULE.read_bytes())
        self.runtime = b.runtime_manifest(self.root / "src/droidasc_mcp")
        competitor = self.base / "competitor"
        competitor.mkdir()
        (competitor / "__init__.py").write_text("# public synthetic comparator")
        self.comparator = {
            "root": str(competitor),
            "python_sources_sha256": {"__init__.py": b.file_hash(competitor / "__init__.py")},
        }
        digest_patch = patch.object(
            b,
            "COMPARATOR_SOURCES_SHA256",
            b.sha256(b.canonical(self.comparator["python_sources_sha256"])),
        )
        digest_patch.start()
        self.addCleanup(digest_patch.stop)
        self.frozen = self.write(
            "frozen.json",
            {
                p.relative_to(self.root).as_posix(): b.file_hash(p)
                for p in self.root.rglob("*")
                if p.is_file()
            },
        )
        entries = [
            {
                "path": p.relative_to(self.root).as_posix(),
                "mode": "100644",
                "type": "blob",
                "sha": b.git_blob(p),
            }
            for p in self.root.rglob("*")
            if p.is_file()
        ]
        commit = self.write("commit.json", {"sha": "c" * 40, "tree": {"sha": "d" * 40}})
        tree = self.write("tree.json", {"sha": "d" * 40, "truncated": False, "tree": entries})
        run = self.write(
            "run.json",
            {
                "id": 123,
                "run_attempt": 1,
                "head_sha": "c" * 40,
                "status": "completed",
                "conclusion": "success",
            },
        )
        wheel = self.base / b.WHEEL_NAME
        installed = self.base / "ci-venv/lib/python3/site-packages/droidasc_mcp"
        installed.mkdir(parents=True)
        with zipfile.ZipFile(wheel, "w") as archive:
            for path in (self.root / "src/droidasc_mcp").iterdir():
                archive.writestr("droidasc_mcp/" + path.name, path.read_bytes())
                (installed / path.name).write_bytes(path.read_bytes())
        inputs = []
        constants = {}
        for name in ("taobao", "wechat", "douyin"):
            path = self.base / (name + ".apk")
            path.write_bytes(("NOT AN APK fixture " + name).encode())
            digest = b.file_hash(path)
            constants[name] = ("fixture", path.stat().st_size, digest)
            inputs.append(
                {
                    "name": name,
                    "path": str(path),
                    "version": "fixture",
                    "size_bytes": path.stat().st_size,
                    "sha256": digest,
                }
            )
        self.patcher = patch.dict(b.INPUTS, constants, clear=True)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.manifest = {
            "schema": 1,
            "execution_environment": "dot-cloud",
            "accepted_sha": "c" * 40,
            "ci_run_id": 123,
            "ci_run_attempt": 1,
            "source_root": str(self.root),
            "accepted_commit_json": commit,
            "accepted_recursive_tree_json": tree,
            "accepted_ci_run_json": run,
            "ci_wheel": {
                "path": str(wheel),
                "sha256": b.file_hash(wheel),
                "installed_package_root": str(installed),
            },
            "inputs": inputs,
            "checks": [],
            "supplemental_checks": [],
        }
        for stage in ("source", "ci_wheel"):
            for original in inputs:
                self.add_input(stage, original)
            artifacts = [
                {
                    "path": i["path"],
                    "sha256": i["sha256"],
                    "size_bytes": i["size_bytes"],
                    "dex_count": 1,
                    "status": "passed",
                    "summary": {
                        "entry_count": 1,
                        "native_scope": "archive",
                        "manifest": {"status": "ok", "resource_values_resolved": False},
                    },
                }
                for i in inputs
            ]
            report = self.common("verify_artifact_summary")
            report.update(input_runtime_and_verifier_unchanged=True, artifacts=artifacts)
            self.manifest["supplemental_checks"].append(
                {
                    "stage": stage,
                    "check": "verify_artifact_summary",
                    "input": "all",
                    "report": self.receipt(stage + "-summary", report, "verify_artifact_summary"),
                }
            )

    def write(self, name, value):
        path = self.base / name
        path.write_bytes(b.canonical(value))
        return {"path": str(path), "sha256": b.file_hash(path)}

    def receipt(self, name, report, check):
        ref = self.write(name + ".json", report)
        stage = "ci_wheel" if name.startswith("ci_wheel") else "source"
        python = self.base / ("ci-venv" if stage == "ci_wheel" else "source-venv") / "bin/python"
        driver = self.base / "driver.py"
        driver.write_text("# immutable synthetic runner")
        ref["driver"] = {"path": str(driver), "sha256": b.file_hash(driver)}
        frozen = {
            "manifest_path": self.frozen["path"],
            "manifest_sha256": self.frozen["sha256"],
            "files": len(json.loads(Path(self.frozen["path"]).read_text())),
            "unchanged": True,
        }
        execution = {
            "status": "completed",
            "raw_receipt_sha256": ref["sha256"],
            "raw_status": report["status"],
            "command": [
                str(python),
                str(self.root / "scripts" / (check + ".py")),
                "--output",
                ref["path"],
            ],
            "exit_code": int(
                report["status"] == "failed"
                and check in {"verify_reference_page_benchmark", "benchmark_competitor_runtime"}
            ),
            "source_before": frozen,
            "source_after": frozen,
            "driver_sha256": ref["driver"]["sha256"],
        }
        ref["plan"] = self.write(
            name + ".plan.json",
            {
                "commands": [{"command": execution["command"], "output": ref["path"]}],
                "environment_allowlist": {"PYTHONPATH": str(self.root / "src")}
                if stage == "source"
                else {},
            },
        )
        ref["execution"] = self.write(name + ".execution.json", execution)
        return ref

    def common(self, check, apk=None):
        result = {
            "status": "passed",
            "runtime_sha256": self.runtime,
            "verifier_sha256": b.file_hash(self.root / "scripts" / (check + ".py")),
            "competitor_commit": b.COMPARATOR_COMMIT,
            "competitor_runtime": self.comparator,
        }
        if apk:
            result["apk_sha256"] = apk
        return result

    def index(self, apk):
        sources = [{"sha256": H, "dex_version": "039", "path": "/secret/private.apk"}]
        identity = {"schema": 1, "engine": "fixture", "dex_sha256": [H]}
        return {
            "schema": 2,
            "status": "all_persisted_call_sites_equal",
            "scope": b.INDEX_SCOPE,
            "apk_sha256": apk,
            "runtime_sha256": self.runtime,
            "original_unchanged": True,
            "runtime_unchanged": True,
            "verifier_unchanged": True,
            "bundle_sha256": H,
            "index_sha256": H,
            "site_multiset_sha256": H,
            "method_multiset_sha256": H,
            "dynamic_multiset_sha256": H,
            "index_bytes": 1,
            "total_call_sites": 1,
            "methods": 1,
            "scanned_instructions": 1,
            "methods_without_code": 0,
            "dynamic_sites": 0,
            "sources": sources,
            "sources_sha256": b.sha256(b.canonical(sources)),
            "engine_version": "fixture",
            "input_id": b.sha256(json.dumps(identity, sort_keys=True).encode()),
            "verifier_sha256": {
                n: b.file_hash(self.root / "scripts" / n)
                for n in (
                    "verify_call_index.py",
                    "verify_fuzzy_references.py",
                    "verify_mcp_reference_pages.py",
                )
            },
            "decoder_identity": {
                "name": "androguard",
                "version": "fixture",
                "python_sources_sha256": {"a.py": H},
                "mutf8": {"files_sha256": {"m.py": H}},
            },
        }

    def measurement(self, apk, cpu, graph):
        trials = []
        for n in range(3):
            for scenario in ("graph",) if graph else b.SCENARIOS:
                for implementation in ("competitor", "ours") if n % 2 else ("ours", "competitor"):
                    t = {
                        "implementation": implementation,
                        "scenario": scenario,
                        "round": n,
                        "status": "passed",
                        "cpu_affinity_samples": 1,
                        "operations": [
                            {"label": "open", "result": {"status": "ok", "artifact_sha256": apk}}
                        ],
                    }
                    if graph:
                        t["operations"] += [
                            {
                                "label": f"query:{r}:0",
                                "status": "ok",
                                "arguments": {
                                    "method_descriptor": b.GRAPH_ROOT,
                                    "depth": 3,
                                    "direction": "both",
                                    "max_nodes": 500,
                                    "max_edges": 1000,
                                },
                            }
                            for r in range(2)
                        ]
                    else:
                        fields = (
                            (0, 1)
                            if scenario == "full_concurrent"
                            else (int(scenario == "full_field"),)
                        )
                        collections = []
                        for repeat in range(2):
                            for index, _ in enumerate(fields):
                                label = f"query:{repeat}:{index}"
                                page = label + ":page:0:attempt:0"
                                collections.append({"label": label, "page_labels": [page]})
                                t["operations"].append({"label": page, "status": "ok"})
                        t["reference_collections"] = collections
                    trials.append(t)
        return {
            "status": "passed",
            "apk_sha256": apk,
            "ours_runtime_sha256": self.runtime,
            "competitor_commit": b.COMPARATOR_COMMIT,
            "competitor_runtime": self.comparator,
            "memory_cap_mib": 4096,
            "ours_session_disk_budget_mib": 8192,
            "external_temporary_logical_cap_mib": 8192,
            "ours_expansion_budget_mib": 512,
            "full_collection_page_size": 1000,
            "graph_depth": 3,
            "timeout_per_call_seconds": 30 if graph else 180,
            "input_unchanged": True,
            "runtime_unchanged": True,
            "competitor_runtime_unchanged": True,
            "harness_sha256": b.file_hash(self.root / "scripts/benchmark_competitor_runtime.py"),
            "cpu_wrapper_sha256": b.file_hash(self.root / "scripts/benchmark_cpu_wrapper.py"),
            "timing_version": 2,
            "cpu_budget_version": 1,
            "external_call_deadline_version": 1,
            "workers": cpu,
            "cpu_affinity": list(range(cpu)),
            "repeats": 2,
            "trials": trials,
        }

    def add_input(self, stage, original):
        name, apk = original["name"], original["sha256"]
        prefix = stage + "-" + name
        index = self.index(apk)
        for check in sorted(b.CHECKS):
            report = self.common(check, apk)
            refs, benchmarks = [], []
            if check == "verify_preparation_directory":
                report.update(
                    input_unchanged=True,
                    runtime_unchanged=True,
                    snapshot_bytes_match_original=True,
                    common_metadata_exact_match=True,
                    dex_count=1,
                    exact_classes_and_owners=1,
                    ordered_class_owner_sha256=H,
                )
            elif check == "verify_mcp_reference_pages":
                report.update(
                    input_runtime_oracle_unchanged=True,
                    cleanup_verified=True,
                    operations=[
                        {
                            "operation": op,
                            "status": "passed",
                            "full_result_sha256": H,
                            "total": 1,
                            "pages": [{"offset": 0, "count": 1, "items_sha256": H}],
                        }
                        for op in b.OPERATIONS
                    ],
                )
            elif check == "verify_frontier_graph":
                report.update(
                    input_unchanged=True,
                    runtime_unchanged=True,
                    verifier_unchanged=True,
                    independent_full_index=index,
                    sources=index["sources"],
                    input_id=index["input_id"],
                    queries=[],
                )
                for root in b.FRONTIER_ROOTS:
                    for direction in ("incoming", "outgoing", "both"):
                        for depth in (1, 3, 5):
                            report["queries"].append(
                                {
                                    "query": {
                                        "operation": "get_call_graph",
                                        "method_descriptor": root,
                                        "direction": direction,
                                        "depth": depth,
                                        "max_nodes": 500,
                                        "max_edges": 1000,
                                    },
                                    "status": "passed",
                                    "exact_match": True,
                                    "accepted_full_index_sha256": H,
                                    "independent_acceptance_sha256": b.sha256(b.canonical(index)),
                                    "graph_sha256": H,
                                }
                            )
            else:
                graph = check == "verify_graph_benchmark"
                for cpu in (2, 4):
                    bench = self.receipt(
                        prefix + check + str(cpu) + "measured",
                        self.measurement(apk, cpu, graph),
                        "benchmark_competitor_runtime",
                    )
                    benchmarks.append(bench)
                if graph:
                    report.update(
                        input_runtime_oracles_unchanged=True,
                        cleanup_verified=True,
                        independent_full_index=index,
                        independent_emitted_sites={
                            "status": "passed",
                            "matched_unique_call_sites": 1,
                        },
                        competitor_failures=[],
                        graphs=[],
                    )
                    for bench in benchmarks:
                        for n in range(3):
                            for repeat in range(2):
                                report["graphs"].append(
                                    {
                                        "receipt": bench["path"],
                                        "round": n,
                                        "label": f"query:{repeat}:0",
                                        "status": "passed",
                                        "exact_full_index_match": True,
                                        "accepted_index_sha256": H,
                                        "independent_acceptance_sha256": b.sha256(
                                            b.canonical(index)
                                        ),
                                        "graph_sha256": H,
                                    }
                                )
                    report["acceptance_inputs_sha256"] = {
                        ref["path"]: ref["sha256"] for ref in benchmarks
                    }
                    report["acceptance_inputs_sha256"].update(
                        {
                            original["path"]: apk,
                            str(self.root / "scripts" / (check + ".py")): report["verifier_sha256"],
                        }
                    )
                else:
                    for i, bench in enumerate(benchmarks):
                        rr = copy.deepcopy(report)
                        rr.update(
                            input_runtime_oracle_unchanged=True,
                            oracle_cleanup_verified=True,
                            collections=[],
                            acceptance_inputs_sha256={
                                bench["path"]: bench["sha256"],
                                original["path"]: apk,
                                str(self.root / "scripts" / (check + ".py")): report[
                                    "verifier_sha256"
                                ],
                            },
                        )
                        for implementation, scenario, n, label, operation in sorted(
                            b.collection_keys()
                        ):
                            row = {
                                "implementation": implementation,
                                "scenario": scenario,
                                "round": n,
                                "label": label,
                                "operation": operation,
                                "status": "passed",
                                "pages": 1,
                            }
                            if implementation == "ours":
                                row.update(
                                    native_diagnostics_verified=True,
                                    total=1,
                                    normalized_sites_sha256=H,
                                )
                            else:
                                row.update(
                                    expected_sites=1,
                                    actual_sites=1,
                                    expected_sites_sha256=H,
                                    actual_sites_sha256=H,
                                    missing_sites=0,
                                    extra_sites=0,
                                )
                                if name == "taobao" and operation == "find_field_refs":
                                    row.update(
                                        status="failed",
                                        actual_sites=2,
                                        extra_sites=1,
                                        actual_sites_sha256="b" * 64,
                                        extra_examples=[{"site": "PROPRIETARY_ROW"}],
                                    )
                                    rr["status"] = "failed"
                            rr["collections"].append(row)
                        refs.append(self.receipt(prefix + check + str(i), rr, check))
            if not refs:
                refs.append(self.receipt(prefix + check, report, check))
            self.manifest["checks"].append(
                {
                    "stage": stage,
                    "input": name,
                    "check": check,
                    "reports": refs,
                    "benchmarks": benchmarks,
                }
            )
        report = self.common("verify_method_selection", apk)
        report.update(
            input_runtime_and_verifier_unchanged=True,
            selected={"instructions": [[0, "return"]]},
            overloaded={"candidate_count": 2},
            overload_recovery="passed",
            competitor_disassembly_and_ambiguity="passed",
            operations=[
                {"operation": op, "status": "passed", "response_sha256": H}
                for op in (
                    "disassemble_method",
                    "get_method_source",
                    "get_method_calls",
                    "find_method_refs",
                    "get_call_graph",
                )
            ],
        )
        self.manifest["supplemental_checks"].append(
            {
                "stage": stage,
                "check": "verify_method_selection",
                "input": name,
                "report": self.receipt(prefix + "method", report, "verify_method_selection"),
            }
        )

    def item(self, check, name="wechat", stage="source"):
        return next(
            r
            for r in self.manifest["checks"]
            if (r["check"], r["input"], r["stage"]) == (check, name, stage)
        )

    def mutate(self, ref, edit):
        path = Path(ref["path"])
        value = json.loads(path.read_text())
        edit(value)
        path.write_bytes(b.canonical(value))
        ref["sha256"] = b.file_hash(path)
        if "execution" in ref:
            self.mutate(
                ref["execution"],
                lambda e: e.update(raw_receipt_sha256=ref["sha256"], raw_status=value["status"]),
            )

    def test_full_valid_synthesis_is_deterministic_private_and_preserves_failures(self):
        first = b.build_capsule(self.manifest)
        self.assertEqual(b.canonical(first), b.canonical(b.build_capsule(self.manifest)))
        self.assertEqual((len(first["checks"]), len(first["supplemental_checks"])), (30, 8))
        decoded = [json.loads(base64.b64decode(r["evidence_base64"])) for r in first["checks"]]
        failed = [r for r in decoded if r["raw_status"] == "failed"]
        self.assertEqual(len(failed), 2)
        self.assertTrue(
            all(r["status"] == "passed" and r["competitor"]["failed_cases"] == 24 for r in failed)
        )
        public = b.canonical([first, decoded])
        for private in (str(self.base), "PROPRIETARY_ROW", "Lprivate", "/secret/"):
            self.assertNotIn(private.encode(), public)

    def test_end_to_end_publisher_validation_and_tampering(self):
        spec = importlib.util.spec_from_file_location(
            "publisher_e2e", MODULE.with_name("publish_accepted_release.py")
        )
        publisher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(publisher)
        capsule = b.build_capsule(self.manifest)
        packages = {b.WHEEL_NAME: Path(self.manifest["ci_wheel"]["path"]).read_bytes()}

        def approval(value):
            raw = b.canonical(value)
            return {
                **{k: self.manifest[k] for k in ("accepted_sha", "ci_run_id", "ci_run_attempt")},
                "corpus_capsule_base64": base64.b64encode(raw).decode(),
                "corpus_capsule_sha256": b.sha256(raw),
            }

        self.assertEqual(publisher.validate_corpus(approval(capsule), packages, self.root), capsule)
        for tamper in (
            lambda c: c["supplemental_checks"].pop(),
            lambda c: c["ci_wheel"].update(sha256=H),
            lambda c: c.update(capsule_builder_sha256=H),
        ):
            broken = copy.deepcopy(capsule)
            tamper(broken)
            with self.assertRaises(ValueError):
                publisher.validate_corpus(approval(broken), packages, self.root)

    def test_shortened_rounds_and_repeats_rejected_in_measured_raw(self):
        original = self.manifest["inputs"][0]
        for edit in (
            lambda r: r["trials"].pop(),
            lambda r: r.update(repeats=1),
            lambda r: r["trials"].reverse(),
            lambda r: r["trials"][0]["reference_collections"].pop(),
        ):
            raw = self.measurement(original["sha256"], 2, False)
            edit(raw)
            with self.assertRaises(ValueError):
                b.validate_benchmark(raw, original["sha256"], self.runtime, self.root)

    def test_graph_competitor_failure_preserved_not_product_waiver(self):
        original = self.manifest["inputs"][0]
        raw = self.measurement(original["sha256"], 2, True)
        raw["trials"][1]["status"] = "failed"
        raw["status"] = "failed"
        ref = self.receipt("failed-graph-benchmark", raw, "benchmark_competitor_runtime")
        path, report = b.read_ref(ref)
        b.validate_execution(
            ref, path, report, self.root / "scripts/benchmark_competitor_runtime.py"
        )
        self.assertEqual(
            b.validate_benchmark(raw, original["sha256"], self.runtime, self.root, True), 2
        )
        raw["trials"][0]["status"] = "failed"
        with self.assertRaisesRegex(ValueError, "Product measured trial"):
            b.validate_benchmark(raw, original["sha256"], self.runtime, self.root, True)

    def test_early_product_graph_and_reference_pages_cannot_hide_behind_last_trial(self):
        original = self.manifest["inputs"][0]
        for graph in (False, True):
            raw = self.measurement(original["sha256"], 2, graph)
            raw["trials"][0]["operations"].pop()
            with self.assertRaises(ValueError):
                b.validate_benchmark(raw, original["sha256"], self.runtime, self.root, graph)

    def test_non_taobao_comparator_failure_blocked(self):
        item = self.item("verify_reference_page_benchmark")

        def edit(r):
            target = next(
                c
                for c in r["collections"]
                if c["implementation"] == "competitor" and c["operation"] == "find_field_refs"
            )
            target.update(
                status="failed", extra_sites=1, actual_sites=2, actual_sites_sha256="b" * 64
            )
            r["status"] = "failed"

        ref = item["reports"][0]
        self.mutate(ref, edit)
        self.mutate(ref["execution"], lambda e: e.update(exit_code=1))
        with self.assertRaisesRegex(ValueError, "Unknown comparator"):
            b.build_capsule(self.manifest)

    def test_altered_comparator_graph_depth_and_budgets_blocked(self):
        original = self.manifest["inputs"][0]
        for key, value in (
            ("competitor_commit", "f" * 40),
            ("graph_depth", 1),
            ("memory_cap_mib", 8192),
            ("timeout_per_call_seconds", 300),
            ("full_collection_page_size", 10),
        ):
            raw = self.measurement(original["sha256"], 2, True)
            raw[key] = value
            with self.assertRaises(ValueError):
                b.validate_benchmark(raw, original["sha256"], self.runtime, self.root, True)

    def test_reused_source_execution_as_wheel_is_blocked(self):
        source = self.item("verify_preparation_directory")
        wheel = self.item("verify_preparation_directory", stage="ci_wheel")
        wheel["reports"] = source["reports"]
        with self.assertRaisesRegex(ValueError, "Reused execution"):
            b.build_capsule(self.manifest)

    def test_wheel_source_pythonpath_blocked(self):
        ref = self.item("verify_preparation_directory", stage="ci_wheel")["reports"][0]
        self.mutate(
            ref["plan"],
            lambda p: p.update(environment_allowlist={"PYTHONPATH": str(self.root / "src")}),
        )
        with self.assertRaisesRegex(ValueError, "PYTHONPATH"):
            b.build_capsule(self.manifest)

    def test_actions_execution_blocked(self):
        with (
            patch.dict(b.os.environ, {"GITHUB_ACTIONS": "true"}),
            self.assertRaisesRegex(ValueError, "must not run in Actions"),
        ):
            b.build_capsule(self.manifest)

    def test_missing_raw_file_blocked(self):
        Path(self.manifest["checks"][0]["reports"][0]["path"]).unlink()
        with self.assertRaises(FileNotFoundError):
            b.build_capsule(self.manifest)

    def test_raw_hash_mismatch_blocked(self):
        Path(self.manifest["checks"][0]["reports"][0]["path"]).write_text("{}")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            b.build_capsule(self.manifest)

    def test_nested_failed_product_collection_blocked(self):
        ref = self.item("verify_reference_page_benchmark")["reports"][0]
        self.mutate(
            ref,
            lambda r: next(c for c in r["collections"] if c["implementation"] == "ours").update(
                status="failed"
            ),
        )
        with self.assertRaisesRegex(ValueError, "Nested product"):
            b.build_capsule(self.manifest)

    def test_omitted_independent_index_blocked(self):
        self.mutate(
            self.item("verify_frontier_graph")["reports"][0],
            lambda r: r.pop("independent_full_index"),
        )
        with self.assertRaises(KeyError):
            b.build_capsule(self.manifest)

    def test_nested_failed_index_blocked(self):
        self.mutate(
            self.item("verify_frontier_graph")["reports"][0],
            lambda r: r["independent_full_index"].update(status="failed"),
        )
        with self.assertRaisesRegex(ValueError, "Independent index"):
            b.build_capsule(self.manifest)

    def test_stale_wheel_blocked(self):
        self.manifest["ci_wheel"]["sha256"] = H
        with self.assertRaisesRegex(ValueError, "wheel byte hash"):
            b.build_capsule(self.manifest)

    def test_stale_installed_runtime_blocked(self):
        (Path(self.manifest["ci_wheel"]["installed_package_root"]) / "__init__.py").write_text(
            "changed"
        )
        with self.assertRaisesRegex(ValueError, "Installed runtime"):
            b.build_capsule(self.manifest)

    def test_stale_report_runtime_blocked(self):
        self.mutate(
            self.item("verify_preparation_directory")["reports"][0],
            lambda r: r.update(runtime_sha256={"__init__.py": H}),
        )
        with self.assertRaisesRegex(ValueError, "Stale raw runtime"):
            b.build_capsule(self.manifest)

    def test_shortened_core_matrix_blocked(self):
        self.manifest["checks"].pop()
        with self.assertRaisesRegex(ValueError, "30-check"):
            b.build_capsule(self.manifest)

    def test_shortened_reference_matrix_blocked(self):
        self.mutate(
            self.item("verify_reference_page_benchmark")["reports"][0],
            lambda r: r["collections"].pop(),
        )
        with self.assertRaisesRegex(ValueError, "collection matrix"):
            b.build_capsule(self.manifest)

    def test_shortened_frontier_matrix_blocked(self):
        self.mutate(self.item("verify_frontier_graph")["reports"][0], lambda r: r["queries"].pop())
        with self.assertRaisesRegex(ValueError, "frontier matrix"):
            b.build_capsule(self.manifest)

    def test_missing_supplement_blocked(self):
        self.manifest["supplemental_checks"].pop()
        with self.assertRaisesRegex(ValueError, "eight-check"):
            b.build_capsule(self.manifest)

    def test_wrong_ci_run_binding_blocked(self):
        self.mutate(self.manifest["accepted_ci_run_json"], lambda r: r.update(head_sha="e" * 40))
        with self.assertRaisesRegex(ValueError, "CI run"):
            b.build_capsule(self.manifest)

    def test_source_not_in_accepted_tree_blocked(self):
        (self.root / "src/droidasc_mcp/__init__.py").write_text("changed")
        with self.assertRaisesRegex(ValueError, "accepted tree"):
            b.build_capsule(self.manifest)

    def test_caller_pass_flags_do_not_replace_missing_receipts(self):
        item = self.item("verify_preparation_directory")
        item.update(status="passed", oracle_match=True, reports=[])
        with self.assertRaisesRegex(ValueError, "report count"):
            b.build_capsule(self.manifest)


class FixturePathTests(unittest.TestCase):
    def test_aliased_temporary_root_builds_complete_capsule(self):
        # Exercise Windows-style alias expansion without requiring Windows-only
        # short-name APIs, administrator privileges, symlinks, or a skipped test.
        factory = tempfile.TemporaryDirectory
        aliases = []

        class AliasedTemporaryDirectory:
            def __init__(self):
                self.actual = factory()
                root = Path(self.actual.name)
                (root / "alias-anchor").mkdir()
                self.name = str(root / "alias-anchor" / "..")
                aliases.append(self.name)

            def cleanup(self):
                self.actual.cleanup()

        case = CapsuleTests(
            methodName="test_full_valid_synthesis_is_deterministic_private_and_preserves_failures"
        )
        try:
            with patch.object(tempfile, "TemporaryDirectory", AliasedTemporaryDirectory):
                case.setUp()
            self.assertNotEqual(aliases[0], str(Path(aliases[0]).resolve(strict=True)))
            self.assertEqual(case.base, Path(aliases[0]).resolve(strict=True))
            # Full 30+8 validation, determinism, privacy and comparator accounting,
            # not only a lexical path assertion.
            case.test_full_valid_synthesis_is_deterministic_private_and_preserves_failures()
        finally:
            case.doCleanups()

    def test_same_bytes_at_another_path_do_not_bind_required_dependency(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(strict=True)
            required, substitute = root / "required.json", root / "substitute.json"
            required.write_bytes(b"identical bytes do not make identical provenance")
            substitute.write_bytes(required.read_bytes())
            report = {"acceptance_inputs_sha256": {str(substitute): b.file_hash(substitute)}}
            with self.assertRaisesRegex(ValueError, "Required dependency not bound"):
                b.dependencies(report, [required])


if __name__ == "__main__":
    unittest.main()
