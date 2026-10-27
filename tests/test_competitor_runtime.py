"""Receipt persistence must not contaminate MCP response and concurrent timings."""

import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def benchmark(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "matched_runtime", scripts / "benchmark_competitor_runtime.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module.psutil,
        "Process",
        lambda: SimpleNamespace(
            children=lambda **kw: [], memory_info=lambda: SimpleNamespace(rss=0)
        ),
    )
    return module


def test_temporary_usage_counts_regular_files_and_not_external_symlinks(benchmark, tmp_path):
    root = tmp_path / "owned"
    root.mkdir()
    nested = root / "nested"
    nested.mkdir()
    first, second = root / "snapshot.apk", nested / "index.sqlite"
    first.write_bytes(b"x" * 1025)
    second.write_bytes(b"y" * 513)
    logical, allocated, count = benchmark.temporary_usage(root)
    assert logical == 1538 and count == 2
    if hasattr(first.stat(), "st_blocks"):
        assert allocated == (first.stat().st_blocks + second.stat().st_blocks) * 512
    else:
        assert allocated is None
    outside = tmp_path / "external"
    outside.mkdir()
    (outside / "unrelated.bin").write_bytes(b"private" * 100)
    try:
        (root / "file-link").symlink_to(outside / "unrelated.bin")
        (root / "directory-link").symlink_to(outside, target_is_directory=True)
    except OSError:
        # Windows may not grant symlink privileges; regular-file accounting above
        # remains required rather than skipping the whole cross-platform test.
        return
    assert benchmark.temporary_usage(root) == (logical, allocated, count)


@pytest.mark.parametrize("damage", [None, "missing", "changed", "extra", "absent"])
def test_competitor_installed_sources_must_match_pinned_checkout(
    benchmark, tmp_path, monkeypatch, damage
):
    checkout, installed = tmp_path / "checkout", tmp_path / "installed"
    for root in (checkout / "asc_mcp", installed):
        (root / "analysis").mkdir(parents=True)
        (root / "__init__.py").write_text("", encoding="utf-8")
        (root / "analysis" / "scan.py").write_text("value = 1\n", encoding="utf-8")
    if damage == "missing":
        (installed / "analysis" / "scan.py").unlink()
    elif damage == "changed":
        (installed / "analysis" / "scan.py").write_text("value = 2\n", encoding="utf-8")
    elif damage == "extra":
        (installed / "extra.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(
        benchmark.importlib.util,
        "find_spec",
        lambda _: None if damage == "absent" else SimpleNamespace(origin=installed / "__init__.py"),
    )
    if damage:
        with pytest.raises(RuntimeError, match="pinned checkout|uv run --with"):
            benchmark.competitor_runtime_identity(checkout)
    else:
        result = benchmark.competitor_runtime_identity(checkout)
        assert set(result["python_sources_sha256"]) == {"__init__.py", "analysis/scan.py"}


@pytest.mark.parametrize(
    "field", ["total", "nodes", "truncation_reasons", "scan_errors", "instruction_scan_complete"]
)
def test_warm_consistency_includes_counts_nodes_truncation_and_diagnostics(benchmark, field):
    original = {"status": "ok", "items": [], "edges": [], field: "original"}
    changed = {**original, field: "changed"}
    assert benchmark.query_content(original) != benchmark.query_content(changed)


def test_warm_consistency_only_ignores_cache_lifecycle_not_index_identity(benchmark):
    original = {"items": [], "index": {"input_id": "one", "reused": False}}
    warm = {
        "items": [],
        "query_cache": {"hit": True},
        "index": {"input_id": "one", "reused": True, "durable_cache": "restored"},
    }
    assert benchmark.query_content(original) == benchmark.query_content(warm)
    warm["index"]["input_id"] = "different"
    assert benchmark.query_content(original) != benchmark.query_content(warm)


@pytest.mark.parametrize("implementation", ["ours", "competitor"])
def test_string_scenario_uses_literal_api_with_the_same_value(benchmark, implementation):
    [(tool, params)] = benchmark.queries(implementation, "key", "string", benchmark.GRAPH_ROOT, 3)
    assert params["value"] == "https://" and params["limit"] == 100
    if implementation == "ours":
        assert tool == "asc_query_dex_session" and params["operation"] == "find_string_refs"
        assert params["session_id"] == "key"
    else:
        assert tool == "apk_find_string_references" and params["analysis_id"] == "key"


@pytest.mark.anyio
@pytest.mark.parametrize("implementation", ["ours", "competitor"])
@pytest.mark.parametrize("count", [0, 1, 5])
async def test_full_reference_collection_follows_every_cursor(benchmark, implementation, count):
    calls = []
    rows = [{"value": i} for i in range(count)]

    async def call(label, tool, params, **kwargs):
        calls.append((label, params))
        ours = implementation == "ours"
        offset = params["offset"] if ours else int(params["cursor"] or 0)
        page = rows[offset : offset + params["limit"]]
        more = offset + len(page) < count
        if ours:
            return {
                "status": "ok",
                "items": page,
                "total": count,
                "offset": offset,
                "limit": params["limit"],
                "has_more": more,
                "truncated": more,
                "next_offset": offset + len(page) if more else None,
                "scanned_instructions": 100,
                "query_cache": {"hit": bool(offset)},
            }
        return {
            "hits": page,
            "total": count,
            "next_cursor": str(offset + len(page)) if more else None,
        }

    result, pages, recoveries = await benchmark.collect_reference_pages(
        call, implementation, "tool", {}, "query:0:0", 2
    )
    assert result["items" if implementation == "ours" else "hits"] == rows
    assert len(pages) == max(1, (count + 1) // 2) == len(calls)
    assert not recoveries


@pytest.mark.anyio
async def test_full_reference_recovery_preserves_offset_and_retry_cost(benchmark):
    calls = []

    async def call(label, tool, params, **kwargs):
        offset, limit = params["offset"], params["limit"]
        calls.append((offset, limit))
        if (offset, limit) == (2, 2):
            return {"status": "error", "code": "response_limit"}
        items = list(range(offset, min(offset + limit, 5)))
        more = offset + len(items) < 5
        return {
            "status": "ok",
            "items": items,
            "total": 5,
            "offset": offset,
            "limit": limit,
            "has_more": more,
            "truncated": more,
            "next_offset": offset + len(items) if more else None,
        }

    result, pages, recoveries = await benchmark.collect_reference_pages(
        call, "ours", "tool", {}, "query:0:0", 2
    )
    assert result["items"] == list(range(5)) and len(pages) == 4
    assert recoveries == [{"offset": 2, "limit": 2}]
    assert calls == [(0, 2), (2, 2), (2, 1), (3, 1), (4, 1)]


@pytest.mark.anyio
@pytest.mark.parametrize("damage", ["cursor", "total", "diagnostic", "empty", "error", "limit"])
async def test_full_reference_collection_rejects_incomplete_or_changed_pages(benchmark, damage):
    async def call(label, tool, params, **kwargs):
        offset = params["offset"]
        result = {
            "status": "ok",
            "items": [offset],
            "total": 3,
            "offset": offset,
            "limit": 1,
            "has_more": offset < 2,
            "truncated": offset < 2,
            "next_offset": offset + 1 if offset < 2 else None,
            "scan_errors": 0,
        }
        if offset:
            if damage == "cursor":
                result["next_offset"] = 0
            elif damage == "total":
                result["total"] = 2
            elif damage == "diagnostic":
                result["scan_errors"] = 1
            elif damage == "empty":
                result["items"] = []
            elif damage == "error":
                result = {"status": "error", "code": "timeout"}
            elif damage == "limit":
                result["items"] = [1, 2]
        return result

    with pytest.raises(AssertionError):
        await benchmark.collect_reference_pages(call, "ours", "tool", {}, "q", 1)


@pytest.mark.parametrize("implementation", ["ours", "competitor"])
@pytest.mark.parametrize("scenario", ["full_method", "full_field", "full_string", "full_type"])
def test_full_reference_scenarios_preserve_exact_target(benchmark, implementation, scenario):
    full = benchmark.queries(implementation, "key", scenario, benchmark.GRAPH_ROOT, 3)
    normal = benchmark.queries(
        implementation, "key", scenario.removeprefix("full_"), benchmark.GRAPH_ROOT, 3
    )
    assert full == normal


@pytest.mark.parametrize("implementation", ["ours", "competitor"])
def test_full_operand_concurrent_uses_equivalent_literal_selectors(benchmark, implementation):
    commands = benchmark.queries(implementation, "key", "full_operands", benchmark.GRAPH_ROOT, 3)
    assert commands == [
        benchmark.queries(implementation, "key", kind, benchmark.GRAPH_ROOT, 3)[0]
        for kind in ("string", "type")
    ]
    if implementation == "ours":
        assert commands[1][1]["type_relation"] == "operand"
        assert commands[1][1]["type_match"] == "substring"
        assert commands[1][1]["type_descriptor"] == "Ljava/lang/String;"
    else:
        assert commands[1][0] == "apk_find_type_instructions"
        assert commands[1][1]["type_name"] == "Ljava/lang/String;"


@pytest.mark.anyio
async def test_benchmark_preserves_existing_receipts(benchmark, tmp_path):
    receipt = tmp_path / "receipt.json"
    receipt.write_text("previous evidence", encoding="utf-8")
    with pytest.raises(AssertionError, match="Preserve"):
        await benchmark.main(SimpleNamespace(output=receipt))
    assert receipt.read_text(encoding="utf-8") == "previous evidence"


def test_receipt_writer_spills_completed_operations_without_retaining_them(benchmark, tmp_path):
    import json

    output = tmp_path / "receipt.json"
    writer = benchmark.ReceiptWriter(output)
    operations = [{"result": {"items": [{"value": "text"}]}}]
    report = {"status": "running", "trials": [{"operations": operations, "status": "passed"}]}
    writer.save(report)
    trial = report["trials"][0]
    assert "operations" not in trial
    assert benchmark.trial_operations(output, trial) == operations
    first = json.loads(output.read_text(encoding="utf-8"))
    report["trials"].append({"operations": [], "status": "passed"})
    report["status"] = "passed"
    writer.save(report)
    final = json.loads(output.read_text(encoding="utf-8"))
    assert final["trials"][0] == first["trials"][0]
    assert final["status"] == "passed"
    assert benchmark.trial_operations(output, final["trials"][1]) == []
    with pytest.raises(AssertionError, match="Preserve"):
        benchmark.ReceiptWriter(output)


@pytest.mark.parametrize("damage", ["content", "size", "path", "missing"])
def test_spilled_receipt_validation_rejects_changed_evidence(benchmark, tmp_path, damage):
    output = tmp_path / "receipt.json"
    writer = benchmark.ReceiptWriter(output)
    report = {"trials": [{"operations": [{"result": 1}]}]}
    writer.save(report)
    trial = report["trials"][0]
    reference = trial["operations_file"]
    path = benchmark.operation_receipt_path(output, trial)
    if damage == "content":
        path.write_text('[{"result":2}]\n', encoding="utf-8")
    elif damage == "size":
        reference["size_bytes"] += 1
    elif damage == "path":
        reference["name"] = "../outside.json"
    else:
        path.unlink()
    with pytest.raises((AssertionError, OSError)):
        benchmark.trial_operations(output, trial)


def test_legacy_inline_operations_remain_readable(benchmark, tmp_path):
    operations = [{"result": "legacy"}]
    assert (
        benchmark.trial_operations(tmp_path / "old.json", {"operations": operations}) is operations
    )


@pytest.mark.anyio
@pytest.mark.parametrize("implementation", ["ours", "competitor"])
async def test_full_reference_trial_measures_last_response_and_all_recovery_attempts(
    benchmark, tmp_path, monkeypatch, implementation
):
    calls = []
    ours = implementation == "ours"
    elapsed = 0.0
    monkeypatch.setattr(benchmark, "time", SimpleNamespace(monotonic=lambda: elapsed))

    class Client:
        def __init__(self, endpoint):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def call_tool(self, name, params, **kwargs):
            nonlocal elapsed
            await asyncio.sleep(0)
            elapsed += 0.125
            calls.append((name, params))
            if name in {"asc_open_artifact_session", "load_artifact"}:
                result = {"status": "ok", "session_id": "s", "analysis_id": "s"}
            elif name in {"asc_close_dex_session", "close_artifact"}:
                result = {"status": "ok"}
            elif ours and params["limit"] == 2:
                result = {"status": "error", "code": "response_limit"}
            else:
                offset = params["offset"] if ours else int(params["cursor"] or 0)
                rows = list(range(offset, min(offset + params["limit"], 3)))
                more = offset + len(rows) < 3
                result = (
                    {
                        "status": "ok",
                        "items": rows,
                        "total": 3,
                        "offset": offset,
                        "limit": params["limit"],
                        "has_more": more,
                        "truncated": more,
                        "next_offset": offset + len(rows) if more else None,
                    }
                    if ours
                    else {
                        "hits": rows,
                        "total": 3,
                        "next_cursor": str(offset + len(rows)) if more else None,
                    }
                )
            return SimpleNamespace(is_error=False, structured_content=result)

    monkeypatch.setattr(benchmark, "Client", Client)
    args = SimpleNamespace(
        cpu_affinity=[0, 1],
        workers=2,
        apk=tmp_path / "fixture.apk",
        timeout=5,
        session_disk_mib=8192,
        expanded_mib=128,
        memory_mib=4096,
        graph_root=benchmark.GRAPH_ROOT,
        graph_depth=3,
        repeats=2,
        page_size=2,
    )
    report = {"trials": []}

    def save():
        assert calls[-1][0] == ("asc_close_dex_session" if ours else "close_artifact")

    await benchmark.trial(args, implementation, "full_method", 0, report, save)
    metric = report["trials"][0]
    assert metric["status"] == "passed", metric
    assert len(metric["reference_collections"]) == len(metric["batch_seconds"]) == 2
    first_collection = metric["reference_collections"][0]
    first_ops = [op for op in metric["operations"] if op["label"].startswith("query:0:0:")]
    assert len(first_collection["page_labels"]) == (3 if ours else 2)
    assert len(first_ops) == (4 if ours else 2)
    assert (
        metric["first_result_from_process_start_seconds"]
        == first_ops[-1]["response_from_process_start_seconds"]
    )
    assert (
        metric["first_result_from_process_start_seconds"]
        > first_ops[0]["response_from_process_start_seconds"]
    )
    assert [op["seconds"] for op in first_ops] == [0.125] * len(first_ops)
    assert metric["batch_seconds"][0] == sum(op["seconds"] for op in first_ops)
    assert metric["first_result_from_process_start_seconds"] == (1 + len(first_ops)) * 0.125
    assert first_collection["response_limit_recoveries"] == (
        [{"offset": 0, "limit": 2}] if ours else []
    )


@pytest.mark.anyio
@pytest.mark.parametrize("implementation", ["ours", "competitor"])
@pytest.mark.parametrize("scenario", ["method", "concurrent"])
@pytest.mark.parametrize("disk_limited", [False, True])
async def test_full_receipt_only_saved_after_measured_responses(
    benchmark, implementation, scenario, disk_limited, tmp_path, monkeypatch
):
    calls, persisted = [], []

    class Client:
        def __init__(self, endpoint):
            self.file = Path(endpoint.env["TMPDIR"]) / "owned-snapshot.apk"
            assert endpoint.args[-1] == ("droidasc_mcp" if implementation == "ours" else "asc_mcp")
            assert endpoint.args[-3:-1] == ["--cpus", "0,1"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def call_tool(self, name, params, **kwargs):
            await asyncio.sleep(0)
            calls.append(name)
            result = {"status": "ok", "items": []}
            if name in {"load_artifact", "asc_open_artifact_session"}:
                self.file.write_bytes(b"x" * 1025)
                await asyncio.sleep(0.25)
                result.update(session_id="key", analysis_id="key")
            elif name in {"close_artifact", "asc_close_dex_session"}:
                self.file.unlink()
            return SimpleNamespace(is_error=False, structured_content=result)

    monkeypatch.setattr(benchmark, "Client", Client)
    if disk_limited:
        monkeypatch.setattr(benchmark, "temporary_usage", lambda root: (2 * 1024**2, None, 1))
    report = {"trials": []}
    args = SimpleNamespace(
        cpu_affinity=[0, 1],
        workers=2,
        apk=tmp_path / "fixture.apk",
        timeout=5,
        session_disk_mib=1 if disk_limited else 8192,
        expanded_mib=128,
        memory_mib=4096,
        graph_root=benchmark.GRAPH_ROOT,
        graph_depth=3,
    )
    close_tool = "asc_close_dex_session" if implementation == "ours" else "close_artifact"

    def save():
        assert calls[-1] == close_tool, "No full report writes within the measured path"
        persisted.append(list(calls))

    await benchmark.trial(args, implementation, scenario, 0, report, save)
    metric = report["trials"][0]
    assert metric["status"] == ("failed" if disk_limited else "passed"), metric
    if disk_limited:
        assert metric["safety_stop"] == "temporary_logical_bytes"
    assert len(persisted) == 1
    assert len(metric["batch_seconds"]) == 3
    assert metric["sampled_peak_temporary_logical_bytes"] == (2 * 1024**2 if disk_limited else 1025)
    assert metric["sampled_peak_temporary_file_count"] == 1
    assert metric["temporary_usage_samples"] > 0
    assert metric["temporary_usage_errors"] == 0
    first_responses = [
        operation["response_from_process_start_seconds"]
        for operation in metric["operations"]
        if operation["label"].startswith("query:0:")
    ]
    assert metric["first_result_from_process_start_seconds"] == max(first_responses)
    assert (
        metric["ready_from_process_start_seconds"]
        == metric["operations"][0]["response_from_process_start_seconds"]
    )
    assert (
        metric["first_result_from_process_start_seconds"]
        >= metric["ready_from_process_start_seconds"]
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "condition",
    ["valid", "escaped", "empty", "denied", "unsupported", "exited", "client_memory", "deadline"],
)
async def test_descendant_cpu_monitor_stops_unmatched_or_unverifiable_trials(
    benchmark, tmp_path, monkeypatch, condition
):
    state = {"inventory_calls": 0, "affinity_calls": 0, "killed": False, "closed": False}

    class Child:
        pid = 12345

        def memory_info(self):
            return SimpleNamespace(rss=0)

        def cpu_affinity(self):
            state["affinity_calls"] += 1
            if condition == "denied":
                raise benchmark.psutil.AccessDenied(self.pid)
            if condition == "unsupported":
                raise NotImplementedError("No affinity readback")
            if condition == "exited":
                raise benchmark.psutil.NoSuchProcess(self.pid)
            return {
                "valid": [1],
                "escaped": [0, 2],
                "empty": [],
                "client_memory": [1],
                "deadline": [1],
            }[condition]

        def kill(self):
            state["killed"] = True

    child = Child()

    def inventory(**kwargs):
        state["inventory_calls"] += 1
        return [] if state["inventory_calls"] == 1 else [child]

    monkeypatch.setattr(
        benchmark.psutil,
        "Process",
        lambda: SimpleNamespace(
            children=inventory, memory_info=lambda: SimpleNamespace(rss=2 * 1024**2)
        ),
    )

    class Client:
        def __init__(self, endpoint):
            pass

        async def __aenter__(self):
            assert state["affinity_calls"] == 0
            return self

        async def __aexit__(self, *args):
            pass

        async def call_tool(self, name, params, **kwargs):
            if name == "asc_open_artifact_session":
                # Let the actual monitor sample after the transport handshake.
                await asyncio.sleep(0.3)
            if state["killed"]:
                raise RuntimeError("Owned trial process was stopped")
            if name == "asc_close_dex_session":
                state["closed"] = True
            return SimpleNamespace(
                is_error=False, structured_content={"status": "ok", "session_id": "key"}
            )

    monkeypatch.setattr(benchmark, "Client", Client)
    args = SimpleNamespace(
        cpu_affinity=[0, 1],
        workers=2,
        apk=tmp_path / "fixture.apk",
        timeout=5,
        session_disk_mib=8192,
        expanded_mib=128,
        memory_mib=4096,
        graph_root=benchmark.GRAPH_ROOT,
        graph_depth=3,
    )
    report, persisted = {"trials": []}, []
    args.client_memory_mib = 1 if condition == "client_memory" else 1024
    args.trial_timeout = 0.05 if condition == "deadline" else 600
    await benchmark.trial(args, "ours", "field", 0, report, lambda: persisted.append(True))
    metric = report["trials"][0]
    assert persisted == [True] and state["affinity_calls"] > 0
    assert state["killed"], "Even successful trials must clean only their owned descendants"
    if condition in {"valid", "exited"}:
        assert metric["status"] == "passed" and state["closed"], metric
        assert "safety_stop" not in metric
        assert bool(metric["cpu_affinity_samples"]) == (condition == "valid")
    else:
        assert metric["status"] == "failed" and not state["closed"], metric
        assert metric["safety_stop"] == (
            "descendant_cpu_affinity"
            if condition in {"escaped", "empty"}
            else "benchmark_client_rss"
            if condition == "client_memory"
            else "complete_trial_deadline"
            if condition == "deadline"
            else "unverifiable_cpu_affinity"
        )
