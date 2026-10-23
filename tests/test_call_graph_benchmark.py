"""Exercise the graph acceptance script against the current frontier/session contract."""

import asyncio
import importlib
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from conftest import assemble_smali


@pytest.fixture
def graph_benchmark(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("benchmark_call_graph")


@pytest.mark.parametrize("fault", [None, "missing_edge", "provenance", "diagnostic", "unknown"])
def test_measured_graph_replay_checks_complete_payload_and_provenance(monkeypatch, fault):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    verifier = importlib.import_module("verify_graph_benchmark")
    expected = {"status": "ok", "edges": [{"site": 1}], "truncated": False}
    opened = {"status": "ok", "session_id": "session", "sources": [{"sha256": "original"}]}
    actual = {
        **opened,
        **expected,
        "instruction_scan_complete": True,
        "scan_errors": 0,
        "runtime_target_resolution": "not_performed",
        "backend": "native-dex-frontier",
        "query_cache": {"hit": True},
    }
    opened.update(
        idle_ttl_seconds=1800, reserved_index_bytes=1024, reuse="immutable", stored_bytes=512
    )
    if fault == "missing_edge":
        actual["edges"] = []
    elif fault == "provenance":
        actual["session_id"] = "wrong"
    elif fault == "diagnostic":
        actual["instruction_scan_complete"] = False
    elif fault == "unknown":
        actual["unverified_field"] = 123
    if fault:
        with pytest.raises(AssertionError):
            verifier.validate_graph_result(actual, opened, expected)
    else:
        verifier.validate_graph_result(actual, opened, expected)


@pytest.mark.parametrize("opcode", [0x6E, 0x74, 0xFA, 0xFB])
def test_independent_method_operand_handles_polymorphic_formats(graph_benchmark, opcode):
    oracle = importlib.import_module("verify_fuzzy_references")

    def generic_reference():
        if opcode in {0xFA, 0xFB}:
            raise Exception("not implemented")
        return 17

    instruction = SimpleNamespace(
        get_op_value=lambda: opcode, get_ref_kind=generic_reference, BBBB=23, HHHH=31
    )
    assert oracle.method_reference_index(instruction) == (23 if opcode in {0xFA, 0xFB} else 17)


def test_real_graph_benchmark_preserves_both_polymorphic_operands(
    graph_benchmark, tmp_path_factory, tmp_path
):
    dex = assemble_smali(tmp_path_factory, ("oracle_polymorphic",))[0]
    apk, output = tmp_path / "polymorphic.apk", tmp_path / "receipt.json"
    with zipfile.ZipFile(apk, "w") as archive:
        archive.write(dex, "classes.dex")
    asyncio.run(
        graph_benchmark.benchmark(
            SimpleNamespace(
                apk=apk,
                output=output,
                expanded_mib=128,
                method_descriptor=(
                    "Ljava/lang/invoke/MethodHandle;"
                    "->invokeExact([Ljava/lang/Object;)Ljava/lang/Object;"
                ),
            )
        )
    )
    report = json.loads(output.read_text())
    assert report["status"] == "passed"
    for graph in (report["graph"], report["fanout_graph"]):
        assert graph["edge_count"] == 2 and graph["dynamic_sites"] == 2
        assert {row["opcode"] for row in graph["edges"]} == {
            "invoke-polymorphic",
            "invoke-polymorphic/range",
        }
        assert {row["call_site_prototype"] for row in graph["edges"]} == {"(I)I"}


@pytest.mark.parametrize("expanded_mib", [128, 512, 2048])
def test_graph_benchmark_uses_real_frontier_and_canonical_source_mapping(
    graph_benchmark, graph_dex_files, tmp_path, expanded_mib
):
    apk, output = tmp_path / "input.apk", tmp_path / "receipt.json"
    with zipfile.ZipFile(apk, "w") as archive:
        archive.write(graph_dex_files[0], "classes.dex")
        archive.write(graph_dex_files[1], "classes10.dex")
    args = SimpleNamespace(
        apk=apk,
        output=output,
        expanded_mib=expanded_mib,
        method_descriptor="Lgraph/A;->root()V",
    )
    asyncio.run(graph_benchmark.benchmark(args))
    report = json.loads(output.read_text())
    assert report["status"] == "passed"
    assert report["original_unchanged"] and report["runtime_unchanged"]
    assert report["verifier_unchanged"]
    assert report["oracle_unchanged"]
    assert report["sources"][1]["dex_entry"] == "classes2.dex"
    assert report["sources"][1]["container_entry"] == "classes10.dex"
    assert report["graph"]["backend"] == "native-dex-frontier"
    assert "index" not in report["graph"] and "index" not in report["fanout_graph"]
    assert report["fanout_graph"]["edge_count"] == 9
    assert report["fanout_graph"]["dynamic_sites"] == 1
    assert len(report["operations"]) == 7
    assert all(row["seconds"] <= row["response_from_start_seconds"] for row in report["operations"])
    budgets = report["configured_budgets"]
    reservation = (
        expanded_mib * 7 * 1024**2
        + int(budgets["DROIDASC_MCP_MAX_OUTPUT_BYTES"]) * 2
        + int(budgets["DROIDASC_MCP_MAX_XREF_INDEX_BYTES"])
        + 1024**2
    )
    assert int(budgets["DROIDASC_MCP_MAX_DEX_SESSION_BYTES"]) >= reservation


def test_failed_site_recheck_replaces_previous_pass(graph_benchmark, tmp_path, monkeypatch):
    output = tmp_path / "receipt.json"
    output.write_text(
        json.dumps({"status": "passed", "independent_emitted_site_oracle": {"status": "passed"}})
    )

    def failed(*args):
        pending = json.loads(output.read_text())
        assert pending["independent_emitted_site_oracle"]["status"] == "running"
        raise AssertionError("Injected independent-site mismatch")

    monkeypatch.setattr(graph_benchmark, "_verify_sites", failed)
    with pytest.raises(AssertionError, match="independent-site mismatch"):
        graph_benchmark.verify_sites(SimpleNamespace(output=output))
    receipt = json.loads(output.read_text())
    assert receipt["status"] == "passed"  # Transport evidence remains separate.
    assert receipt["independent_emitted_site_oracle"]["status"] == "failed"
    assert "mismatch" in receipt["independent_emitted_site_oracle"]["error"]


@pytest.mark.parametrize("damage", [None, "duplicate", "count"])
def test_site_verifier_rejects_duplicate_rows_without_hiding_cross_graph_overlap(
    graph_benchmark, damage
):
    row = {"dex_entry": "classes.dex", "caller": "La/A;->run()V", "instruction_offset": 0}
    graph = {"edge_count": 1, "edges": [row]}
    other = {"edge_count": 1, "edges": [row]}
    if damage == "duplicate":
        graph.update(edge_count=2, edges=[row, row])
    elif damage == "count":
        graph["edge_count"] = 0
    report = {"graph": graph, "fanout_graph": other}
    if damage:
        with pytest.raises(AssertionError):
            graph_benchmark.emitted_edges(report)
    else:
        assert graph_benchmark.emitted_edges(report) == [row, row]
