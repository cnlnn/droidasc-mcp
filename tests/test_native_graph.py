"""Frontiers must preserve the full-index graph, including ordering and diagnostics."""

import sqlite3
import zipfile
from dataclasses import replace

import pytest

from droidasc_mcp.call_graph import query_call_graph
from droidasc_mcp.config import Settings
from droidasc_mcp.native_dex import Dex, InvalidDex
from droidasc_mcp.native_graph import FrontierBudgetExceeded, FrontierGraph, query_frontier
from droidasc_mcp.native_index import build
from droidasc_mcp.service import _normalize_dex_query

ROOT = "Lgraph/A;->root()V"


@pytest.fixture(scope="module")
def indexed_graphs(tmp_path_factory, graph_dex_files):
    root = tmp_path_factory.mktemp("frontier-oracle")
    bundle = root / "analysis.apk"
    with zipfile.ZipFile(bundle, "w") as archive:
        for i, path in enumerate(graph_dex_files, 1):
            archive.write(path, "classes.dex" if i == 1 else f"classes{i}.dex")
    settings = Settings.from_env()
    indexes = []
    for calls_only in (False, True):
        target = root / f"index-{calls_only}.sqlite"
        build(settings, bundle, target, root, {}, calls_only)
        indexes.append(target)
    return settings, bundle, indexes


@pytest.mark.parametrize("direction", ["incoming", "outgoing", "both"])
@pytest.mark.parametrize("depth", [1, 2, 5])
@pytest.mark.parametrize("bounds", [{}, {"max_nodes": 1}, {"max_edges": 1}, {"max_edges": 9}])
@pytest.mark.parametrize(
    "root",
    [
        ROOT,
        "Lgraph/A;->recursive()V",
        "Lgraph/A;->custom()V",
        "Lgraph/A;->noCode()V",
        "Lexternal/Missing;->absent()V",
        "Lgraph/B;->step(J)V",
    ],
)
def test_frontier_exact_full_index_parity(indexed_graphs, direction, depth, bounds, root):
    settings, bundle, indexes = indexed_graphs
    query = _normalize_dex_query(
        {
            "operation": "get_call_graph",
            "method_descriptor": root,
            "direction": direction,
            "depth": depth,
            **bounds,
        }
    )
    actual = query_call_graph(None, query, source=FrontierGraph(settings, bundle, query))
    for target in indexes:
        with sqlite3.connect(target) as db:
            assert actual == query_call_graph(db, query)


def test_frontier_python_fallback_and_output_budget(indexed_graphs, monkeypatch):
    import droidasc_mcp.call_graph as graph_module
    import droidasc_mcp.native_graph as module

    monkeypatch.setattr(module, "class_selector", lambda *a, **kw: None)
    monkeypatch.setattr(graph_module, "MAX_GRAPH_BYTES", 5500)
    settings, bundle, indexes = indexed_graphs
    query = _normalize_dex_query(
        {"operation": "get_call_graph", "method_descriptor": ROOT, "depth": 5}
    )
    actual = query_call_graph(None, query, source=FrontierGraph(settings, bundle, query))
    with sqlite3.connect(indexes[0]) as db:
        assert actual == query_call_graph(db, query)
    assert actual["truncation_reasons"] == ["output_bytes"]


def test_frontier_is_bounded_and_does_not_publish_an_index(indexed_graphs):
    settings, bundle, _ = indexed_graphs
    query = _normalize_dex_query({"operation": "get_call_graph", "method_descriptor": ROOT})
    actual = query_frontier(settings, bundle, query)
    assert actual["status"] == "ok" and actual["backend"] == "native-dex-frontier"
    assert "index" not in actual
    assert not (bundle.parent / "calls.sqlite").exists()
    with pytest.raises(FrontierBudgetExceeded):
        query_frontier(replace(settings, max_output_bytes=128), bundle, query)


def test_frontier_root_pass_is_not_repeated(indexed_graphs):
    settings, bundle, _ = indexed_graphs
    query = _normalize_dex_query(
        {"operation": "get_call_graph", "method_descriptor": ROOT, "max_nodes": 1}
    )
    source = FrontierGraph(settings, bundle, query)
    result = query_call_graph(None, query, source=source)
    assert source.passes == 1
    assert result["truncation_reasons"] == ["max_nodes"]


@pytest.mark.parametrize("direction", ["incoming", "outgoing", "both"])
@pytest.mark.parametrize("accelerator", [False, True])
def test_frontier_second_scan_filters_incoming_operands(
    indexed_graphs, monkeypatch, direction, accelerator
):
    import droidasc_mcp.native_graph as module

    settings, bundle, indexes = indexed_graphs
    original_scan, scans = module.scanner, []

    def filtered(dex, targets, fields, incoming):
        scan = original_scan(dex, targets, fields, incoming, accelerator=accelerator)

        def run(code):
            scans.append((bool(targets), incoming))
            yield from scan(code)

        return run

    monkeypatch.setattr(module, "scanner", filtered)
    if not accelerator:
        monkeypatch.setattr(module, "class_selector", lambda *a, **kw: None)
    query = _normalize_dex_query(
        {
            "operation": "get_call_graph",
            "method_descriptor": ROOT,
            "direction": direction,
            "depth": 2,
        }
    )
    source = FrontierGraph(settings, bundle, query)
    actual = query_call_graph(None, query, source=source)
    with sqlite3.connect(indexes[0]) as db:
        assert actual == query_call_graph(db, query)
    assert any(targets and incoming for targets, incoming in scans), (
        "Incoming re-scans must select only frontier operands, not emit every call site"
    )


@pytest.mark.parametrize("accelerator", [False, True])
def test_frontier_checks_unreachable_instructions(
    indexed_graphs, tmp_path, monkeypatch, accelerator
):
    import droidasc_mcp.native_graph as module

    settings, original, _ = indexed_graphs
    bundle = tmp_path / "corrupt.apk"
    changed = False
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(bundle, "w") as archive:
        for entry in source.namelist():
            data = bytearray(source.read(entry))
            dex = Dex(bytes(data))
            try:
                for _owner, cls in dex.classes():
                    for index, _flags, code in dex.raw_members(cls)[1]:
                        if dex.method(index) == "Lgraph/A;->custom()V":
                            data[code + 16] = 0x3E
                            changed = True
            finally:
                dex.close()
            archive.writestr(entry, data)
    assert changed
    if not accelerator:
        monkeypatch.setattr(module, "class_selector", lambda *a, **kw: None)
    query = _normalize_dex_query(
        {
            "operation": "get_call_graph",
            "method_descriptor": "Lgraph/A;->noCode()V",
            "direction": "outgoing",
        }
    )
    with pytest.raises(InvalidDex, match="instruction"):
        query_frontier(settings, bundle, query)


def test_dense_frontier_falls_back_to_atomic_index(indexed_graphs, tmp_path, monkeypatch):
    import droidasc_mcp.native_graph as module
    from droidasc_mcp.xref_index import query_index

    settings, original, _ = indexed_graphs
    bundle = tmp_path / "analysis.apk"
    bundle.write_bytes(original.read_bytes())
    query = _normalize_dex_query({"operation": "get_call_graph", "method_descriptor": ROOT})
    expected = query_frontier(settings, bundle, query)

    def overflow(*args):
        raise FrontierBudgetExceeded

    monkeypatch.setattr(module, "query_frontier", overflow)
    result = query_index(settings, bundle, {"input_id": "fixture"}, query, tmp_path)
    assert result["status"] == "ok" and result["backend"] == "native-dex-index"
    assert result["index"]["reused"] is False
    assert (tmp_path / "calls.sqlite").exists()
    assert result["edges"] == expected["edges"] and result["nodes"] == expected["nodes"]
    monkeypatch.setattr(module, "query_frontier", lambda *a: pytest.fail("Existing index bypassed"))
    assert query_index(settings, bundle, {"input_id": "fixture"}, query, tmp_path)["index"][
        "reused"
    ]


def test_dense_batch_splits_without_losing_bfs_nodes(indexed_graphs, monkeypatch):
    settings, bundle, indexes = indexed_graphs
    query = _normalize_dex_query(
        {"operation": "get_call_graph", "method_descriptor": ROOT, "depth": 5}
    )
    source = FrontierGraph(settings, bundle, query)
    prepare, attempts = source._prepare, []

    def bounded(identities, **kwargs):
        attempts.append(len(identities))
        if len(identities) > 1:
            raise FrontierBudgetExceeded
        return prepare(identities, **kwargs)

    monkeypatch.setattr(source, "_prepare", bounded)
    actual = query_call_graph(None, query, source=source)
    with sqlite3.connect(indexes[0]) as db:
        assert actual == query_call_graph(db, query)
    assert any(size > 1 for size in attempts)


def test_explicit_durable_graph_cache_keeps_build_and_restore(
    indexed_graphs, tmp_path, monkeypatch
):
    import droidasc_mcp.native_graph as module
    from droidasc_mcp.xref_index import query_index

    settings, original, _ = indexed_graphs
    settings = replace(settings, xref_cache_dir=tmp_path / "durable")
    query = _normalize_dex_query({"operation": "get_call_graph", "method_descriptor": ROOT})
    monkeypatch.setattr(module, "query_frontier", lambda *a: pytest.fail("Cache opt-in ignored"))
    expected = None
    for label in ("first", "reopened"):
        root = tmp_path / label
        root.mkdir()
        bundle = root / "analysis.apk"
        bundle.write_bytes(original.read_bytes())
        result = query_index(settings, bundle, {"input_id": "fixture"}, query, root)
        assert result["status"] == "ok" and result["backend"] == "native-dex-index"
        assert result["index"]["durable_cache"] == ("stored" if label == "first" else "restored")
        assert result["index"]["reused"] is (label != "first")
        if expected is None:
            expected = result
        else:
            assert result["nodes"] == expected["nodes"] and result["edges"] == expected["edges"]
