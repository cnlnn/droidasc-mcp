"""Static call-site graph oracle, independent of decompiler text and index queries."""

import json
import sqlite3
from dataclasses import replace

import pytest

from droidasc_mcp.call_graph import query_call_graph
from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService, _normalize_dex_query

ROOT = "Lgraph/A;->root()V"
STEP = "Lgraph/B;->step(I)V"
STRING = "Lgraph/B;->step(Ljava/lang/String;)V"
LOOP = "Lgraph/A;->loop()V"
ENTRY = "Lgraph/A;->entry()V"
DYNAMIC = "Lgraph/A;->dynamic(Ljava/lang/invoke/MethodHandle;)V"
EXTERNAL = "Lexternal/Missing;->absent()V"
POLY = "Ljava/lang/invoke/MethodHandle;->invokeExact([Ljava/lang/Object;)Ljava/lang/Object;"
# Offsets are counted directly from the public Smali instruction widths.
ORACLE = {
    (ROOT, STEP, 1),
    (ROOT, STEP, 4),
    (ROOT, STRING, 9),
    (ROOT, EXTERNAL, 12),
    (ROOT, DYNAMIC, 16),
    (STEP, LOOP, 0),
    (LOOP, ROOT, 0),
    (ENTRY, ROOT, 0),
    (DYNAMIC, POLY, 1),
}


@pytest.fixture
def graph_service(graph_dex_files):
    service = DroidAscService(
        replace(
            Settings.from_env(), allowed_roots=(graph_dex_files[0].parent,), timeout_seconds=120
        )
    )
    try:
        key = service.open_dex_session(list(map(str, graph_dex_files)))["session_id"]
        yield service, key
    finally:
        service.close()


def graph(service, key, descriptor=ROOT, **kwargs):
    result = service.query_dex_session(
        key,
        operation="get_call_graph",
        method_descriptor=descriptor,
        offset=0,
        limit=200,
        **kwargs,
    )
    assert result["status"] == "ok", result
    return result


def edge_set(result):
    return {(e["caller"], e["callee"], e["instruction_offset"]) for e in result["edges"]}


def test_graph_multidex_oracle_cycles_overloads_and_reuse(graph_service):
    service, key = graph_service
    result = graph(service, key, depth=5)
    assert result["backend"] == "native-dex-frontier" and "index" not in result
    assert edge_set(result) == ORACLE
    assert result["node_count"] == 8 and result["edge_count"] == 9
    assert not result["truncated"] and result["traversal_complete_within_depth"]
    assert result["runtime_target_resolution"] == "not_performed"
    assert result["dynamic_sites"] == 1 and not result["unresolved_sites_truncated"]
    assert result["unresolved_sites"][0]["reason"] == "dynamic_target_not_resolved"
    for e in result["edges"]:
        assert e["dex_entry"] == ("classes2.dex" if e["caller"] == STEP else "classes.dex")
        assert e["offset_unit"] == "code_units_from_method_start"
        if e["callee"] in {STEP, STRING}:
            assert e["target_dex_entry"] == "classes2.dex"
        if e["callee"] in {EXTERNAL, POLY}:
            assert e["target_resolution"] == "not_defined_in_input"
        if e["callee"] == POLY:
            assert e["call_site_prototype"] == "(I)I"
    source = service.query_dex_session(
        key,
        operation="get_method_source",
        method_descriptor=ROOT,
        source_format="smali",
        offset=0,
        limit=200,
    )
    assert source["status"] == "ok", source
    again = graph(service, key, depth=5)
    assert again["query_cache"]["hit"]
    assert again["edges"] == result["edges"] and again["nodes"] == result["nodes"]


def test_graph_directions_external_root_and_depth(graph_service):
    service, key = graph_service
    outgoing = graph(service, key, direction="outgoing", depth=5)
    assert edge_set(outgoing) == ORACLE - {(ENTRY, ROOT, 0)}
    assert not outgoing["truncated"]
    incoming = graph(service, key, direction="incoming", depth=1)
    assert edge_set(incoming) == {(LOOP, ROOT, 0), (ENTRY, ROOT, 0)}
    assert incoming["truncation_reasons"] == ["depth"]
    shallow = graph(service, key, direction="outgoing", depth=1)
    assert edge_set(shallow) == {e for e in ORACLE if e[0] == ROOT}
    assert shallow["truncation_reasons"] == ["depth"]
    assert shallow["traversal_complete_within_depth"]
    assert {
        n["method_descriptor"]
        for n in shallow["nodes"]
        if n["expansion_status"] == "depth_boundary"
    } == {STEP, DYNAMIC}
    external = graph(service, key, EXTERNAL, direction="incoming", depth=1)
    assert edge_set(external) == {(ROOT, EXTERNAL, 12)}
    leaf = graph(service, key, STRING, direction="outgoing", depth=1)
    assert leaf["edges"] == [] and not leaf["truncated"]
    native = graph(service, key, "Lgraph/A;->noCode()V", direction="outgoing")
    assert native["nodes"][0]["without_code"] and not native["truncated"]
    recursive = graph(service, key, "Lgraph/A;->recursive()V", depth=1)
    assert recursive["node_count"] == recursive["edge_count"] == 1
    assert not recursive["truncated"]
    custom = graph(service, key, "Lgraph/A;->custom()V", direction="outgoing")
    assert custom["edges"] == [] and custom["dynamic_sites"] == 1
    assert custom["unresolved_sites"][0]["opcode"] == "invoke-custom"
    assert custom["unresolved_sites"][0]["instruction_offset"] == 0
    missing = service.query_dex_session(
        key,
        operation="get_call_graph",
        method_descriptor="Lgraph/B;->step(J)V",
        offset=0,
        limit=200,
    )
    assert missing["code"] == "method_not_found"


@pytest.mark.parametrize("budget,value", [("max_nodes", 1), ("max_edges", 1)])
def test_graph_budgets_are_explicit_and_endpoints_present(graph_service, budget, value):
    service, key = graph_service
    result = graph(service, key, **{budget: value})
    assert result["truncation_reasons"] == [budget]
    assert not result["traversal_complete_within_depth"]
    assert any(n["expansion_status"] == "budget_boundary" for n in result["nodes"])
    names = {n["method_descriptor"] for n in result["nodes"]}
    assert all(e["caller"] in names and e["callee"] in names for e in result["edges"])
    if budget == "max_nodes":
        assert result["node_count"] == 1 and result["edge_count"] == 0
    else:
        assert result["edge_count"] == 1


@pytest.mark.parametrize(
    "args",
    [
        {"depth": 0},
        {"depth": 6},
        {"depth": True},
        {"max_nodes": 501},
        {"max_edges": 1001},
        {"max_edges": -1},
        {"direction": "sideways"},
        {"offset": 1},
        {"fuzzy_class": True},
        {"method_descriptor": "root"},
    ],
)
def test_graph_query_validation(args):
    with pytest.raises(ValueError):
        _normalize_dex_query({"operation": "get_call_graph", "method_descriptor": ROOT, **args})


def test_graph_output_byte_budget(monkeypatch):
    import droidasc_mcp.call_graph as module

    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE symbols (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE definitions (kind TEXT, name INTEGER, entry TEXT);
        CREATE TABLE methods (source INTEGER, without_code INTEGER);
        CREATE TABLE edges (id INTEGER PRIMARY KEY, kind TEXT, source INTEGER,
                            target INTEGER, relation TEXT, data BLOB);
        CREATE TABLE dynamic (id INTEGER, source INTEGER, data BLOB);
    """)
    db.execute("INSERT INTO symbols VALUES (1,?)", (ROOT,))
    db.execute("INSERT INTO methods VALUES (1,0)")
    db.execute("INSERT INTO definitions VALUES ('method',1,'classes.dex')")
    for i in range(2, 100):
        db.execute("INSERT INTO symbols VALUES (?,?)", (i, "L" + "a" * 500 + ";->x()V"))
        db.execute(
            "INSERT INTO edges VALUES (?,'method',1,?,'instruction',?)",
            (i, i, json.dumps([i, "invoke-static", None]).encode()),
        )
    monkeypatch.setattr(module, "MAX_GRAPH_BYTES", 8192)
    result = query_call_graph(
        db,
        _normalize_dex_query(
            {"operation": "get_call_graph", "method_descriptor": ROOT, "direction": "outgoing"}
        ),
    )
    db.close()
    assert result["truncation_reasons"] == ["output_bytes"]
    assert 0 < result["edge_count"] < 98
    assert len(json.dumps(result).encode()) < 8192


def test_graph_exact_budget_does_not_falsely_truncate(graph_service):
    service, key = graph_service
    result = graph(service, key, depth=5, max_nodes=8, max_edges=9)
    assert edge_set(result) == ORACLE and not result["truncated"]
