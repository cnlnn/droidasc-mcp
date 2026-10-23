"""Full-corpus comparison preserves duplicate sites and rejects equal-count corruption."""

import asyncio
import copy
import importlib
import subprocess
import sys
import threading
from pathlib import Path

import pytest


@pytest.fixture
def verifier(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("verify_reference_page_benchmark")


def test_external_deadline_runs_while_the_event_loop_is_blocked(verifier):
    benchmark = importlib.import_module("benchmark_competitor_runtime")
    aborted = threading.Event()

    async def blocked():
        with benchmark.CallDeadline(0.01, aborted.set) as deadline:
            assert aborted.wait(5), "External watchdog waited for async cancellation"
            assert deadline.expired.is_set()
        assert not deadline.thread.is_alive()

    asyncio.run(blocked())


@pytest.mark.parametrize("failure", [False, True])
def test_external_deadline_is_disarmed_on_success_and_failure(verifier, failure):
    benchmark = importlib.import_module("benchmark_competitor_runtime")
    aborted = threading.Event()
    deadline = benchmark.CallDeadline(60, aborted.set)
    try:
        with deadline:
            if failure:
                raise ValueError("fixture")
    except ValueError:
        assert failure
    assert not deadline.thread.is_alive()
    assert not deadline.expired.is_set() and not aborted.is_set()


def test_external_deadline_terminates_a_real_owned_process_without_async_cleanup(verifier):
    benchmark = importlib.import_module("benchmark_competitor_runtime")
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    try:
        with benchmark.CallDeadline(0.05, child.kill) as deadline:
            assert child.wait(timeout=5) != 0
            assert deadline.expired.is_set()
        assert not deadline.thread.is_alive()
    finally:
        if child.poll() is None:
            child.kill()
        child.wait(timeout=5)


@pytest.mark.anyio
async def test_collector_follows_byte_limited_prefix_then_unflagged_final_page(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    benchmark = importlib.import_module("benchmark_competitor_runtime")
    requested = []

    async def call(label, tool, arguments, *, allow_response_limit):
        assert tool == "asc_query_dex_session" and allow_response_limit
        assert arguments["limit"] == 1000
        offset = arguments["offset"]
        requested.append(offset)
        more = offset == 0
        return {
            "status": "ok",
            "total": 3,
            "scan_errors": 0,
            "items": [{"site": 0}, {"site": 1}] if more else [{"site": 2}],
            "offset": offset,
            "limit": 1000,
            "has_more": more,
            "truncated": more,
            "next_offset": 2 if more else None,
            **(
                {"page_limited_by": "response_bytes", "response_byte_limit": 262143} if more else {}
            ),
        }

    result, pages, recoveries = await benchmark.collect_reference_pages(
        call, "ours", "asc_query_dex_session", {}, "collection", 1000
    )
    assert requested == [0, 2] and len(pages) == 2 and recoveries == []
    assert result == {
        "status": "ok",
        "total": 3,
        "scan_errors": 0,
        "items": [{"site": 0}, {"site": 1}, {"site": 2}],
    }


@pytest.mark.parametrize("implementation", ["ours", "competitor"])
def test_full_concurrent_queries_retain_both_exact_targets(verifier, implementation):
    benchmark = importlib.import_module("benchmark_competitor_runtime")
    actual = benchmark.queries(implementation, "key", "full_concurrent", benchmark.GRAPH_ROOT, 3)
    expected = [
        benchmark.queries(implementation, "key", scenario, benchmark.GRAPH_ROOT, 3)[0]
        for scenario in ("full_method", "full_field")
    ]
    assert actual == expected


@pytest.mark.parametrize("scenario", ["full_method", "full_field", "full_concurrent"])
@pytest.mark.parametrize("repeats", [1, 2, 3])
@pytest.mark.parametrize("damage", [None, "missing", "duplicate", "unexpected"])
def test_collection_inventory_checks_every_repeat_and_concurrent_target(
    verifier, scenario, repeats, damage
):
    fields = [False, True] if scenario == "full_concurrent" else [scenario == "full_field"]
    pairs = [
        ({"label": f"query:{repeat}:{index}"}, field)
        for repeat in range(repeats)
        for index, field in enumerate(fields)
    ]
    pairs.reverse()  # Concurrent collections are recorded in completion order.
    collections = [dict(row) for row, _ in pairs]
    if damage == "missing":
        collections.pop()
    elif damage == "duplicate":
        collections.append(dict(collections[0]))
    elif damage == "unexpected":
        collections[0]["label"] = "query:99:99"
    trial = {"scenario": scenario, "reference_collections": collections}
    if damage:
        with pytest.raises(AssertionError, match="collection"):
            verifier.collection_fields(trial, repeats)
    else:
        assert verifier.collection_fields(trial, repeats) == pairs


@pytest.mark.parametrize("field", [False, True])
@pytest.mark.parametrize(
    "damage", [None, "target", "tool", "cursor", "duplicate", "missing", "empty", "recovery"]
)
def test_competitor_replay_binds_exact_requests_and_all_pages(verifier, field, damage):
    benchmark = importlib.import_module("benchmark_competitor_runtime")
    tool, params = benchmark.queries(
        "competitor", "key", "field" if field else "method", benchmark.GRAPH_ROOT, 1
    )[0]
    params["limit"] = 1
    operations = [
        {
            "label": f"query:0:0:page:{index}:attempt:0",
            "tool": tool,
            "arguments": {**params, "cursor": str(index) if index else None},
            "status": "ok",
            "result": {
                "hits": [{"site": index}],
                "total": 2,
                "next_cursor": "1" if index == 0 else None,
            },
        }
        for index in range(2)
    ]
    collection = {
        "label": "query:0:0",
        "page_labels": [op["label"] for op in operations],
        "response_limit_recoveries": [],
    }
    if damage == "target":
        operations[1]["arguments"]["class_name"] = "wrong.Owner"
    elif damage == "tool":
        operations[1]["tool"] = "wrong_tool"
    elif damage == "cursor":
        operations[1]["arguments"]["cursor"] = "2"
    elif damage == "duplicate":
        operations.append(copy.deepcopy(operations[-1]))
    elif damage == "missing":
        operations.pop()
    elif damage == "empty":
        operations[0]["result"]["hits"] = []
    elif damage == "recovery":
        collection["response_limit_recoveries"] = [{"offset": 0, "limit": 2}]
    if damage:
        with pytest.raises(AssertionError):
            verifier.competitor_collection(operations, collection, {"analysis_id": "key"}, field, 1)
    else:
        assert verifier.competitor_collection(
            operations, collection, {"analysis_id": "key"}, field, 1
        ) == ([{"site": 0}, {"site": 1}], 2)


@pytest.fixture
def sites():
    sources = [{"dex_entry": "classes2.dex", "container_entry": "classes10.dex"}]
    native = {
        "dex_entry": "classes2.dex",
        "caller": "LCaller;->run()V",
        "callee": "LTarget;->call(I)V",
        "instruction_offset": 42,
        "offset_unit": "code_units_from_method_start",
        "opcode": "invoke-static",
    }
    competitor = {
        "dex_name": "classes10.dex",
        "method_class": "LCaller;",
        "method_name": "run",
        "method_descriptor": "()V",
        "match_type": "method",
        "evidence": [
            {
                "offset": 84,
                "opcode": "invoke-static",
                "access": "invoke",
                "target_class": "LTarget;",
                "target_name": "call",
                "target_descriptor": "(I)V",
            }
        ],
    }
    return sources, native, competitor


@pytest.mark.parametrize("field", [False, True])
def test_exact_sites_normalize_units_sources_and_caller_groups(verifier, sites, field):
    sources, native, competitor = sites
    if field:
        native.pop("callee")
        native.update(field_descriptor="LTarget;->value:I", access="write", opcode="sput")
        competitor["match_type"] = "field"
        competitor["evidence"][0].update(
            target_name="value", target_descriptor="I", access="write", opcode="sput"
        )
    expected = verifier.native_sites([native, native], sources, field)
    competitor["evidence"] *= 2
    actual = verifier.competitor_sites([competitor], sources, field)
    assert actual == expected and len(actual) == 2
    assert verifier.compare_sites(expected, actual)["status"] == "passed"
    missing = verifier.compare_sites(expected, actual[:1])
    assert missing["status"] == "failed" and missing["missing_sites"] == 1


@pytest.mark.parametrize("damage", ["caller", "target", "offset", "opcode", "access", "dex"])
def test_equal_count_wrong_sites_fail_full_content_comparison(verifier, sites, damage):
    sources, native, competitor = sites
    expected = verifier.native_sites([native], sources, False)
    if damage == "caller":
        competitor["method_name"] = "wrong"
    elif damage == "target":
        competitor["evidence"][0]["target_descriptor"] = "(J)V"
    elif damage == "offset":
        competitor["evidence"][0]["offset"] += 2
    elif damage == "opcode":
        competitor["evidence"][0]["opcode"] = "invoke-virtual"
    elif damage == "access":
        native["callee"] = "LTarget;->field:I"
        native["field_descriptor"] = native.pop("callee")
        native.update(access="read", opcode="sget")
        expected = verifier.native_sites([native], sources, True)
        competitor["match_type"] = "field"
        competitor["evidence"][0].update(
            target_name="field", target_descriptor="I", access="write", opcode="sget"
        )
    else:
        sources.append({"dex_entry": "classes3.dex", "container_entry": "classes11.dex"})
        competitor["dex_name"] = "classes11.dex"
    actual = verifier.competitor_sites([competitor], sources, damage == "access")
    result = verifier.compare_sites(expected, actual)
    assert result["status"] == "failed"
    assert result["missing_sites"] == result["extra_sites"] == 1


@pytest.mark.parametrize("damage", ["odd", "negative", "empty", "kind", "access", "source"])
def test_malformed_competitor_evidence_is_not_accepted(verifier, sites, damage):
    sources, _, competitor = sites
    if damage in {"odd", "negative"}:
        competitor["evidence"][0]["offset"] = 3 if damage == "odd" else -2
    elif damage == "empty":
        competitor["evidence"] = []
    elif damage == "kind":
        competitor["match_type"] = "field"
    elif damage == "access":
        competitor["evidence"][0]["access"] = "read"
    else:
        competitor["dex_name"] = "missing.dex"
    with pytest.raises(AssertionError):
        verifier.competitor_sites([competitor], sources, False)


@pytest.mark.anyio
@pytest.mark.parametrize(
    "damage", [None, "provenance", "diagnostic", "target", "labels", "extra", "recovery"]
)
async def test_recorded_pages_replay_full_independent_acceptance(verifier, damage):
    opened = {
        "session_id": "session",
        "input_id": "input",
        "artifact_sha256": "hash",
        "sources": [],
    }
    query = {"operation": "find_method_refs", "method_descriptor": "LTarget;->call()V"}
    expected = {
        "status": "ok",
        "items": [{"value": 1}, {"value": 2}],
        "total": 2,
        "scanned_instructions": 123,
        "scan_errors": 0,
    }
    operations, labels = [], []
    for offset in range(2):
        label = f"query:0:0:page:{offset}:attempt:0"
        labels.append(label)
        operations.append(
            {
                "label": label,
                "tool": "asc_query_dex_session",
                "arguments": {**query, "session_id": "session", "offset": offset, "limit": 1},
                "result": {
                    **opened,
                    **expected,
                    "items": expected["items"][offset : offset + 1],
                    "offset": offset,
                    "limit": 1,
                    "has_more": not offset,
                    "truncated": not offset,
                    "next_offset": 1 if not offset else None,
                },
            }
        )
    collection = {"label": "query:0:0", "page_labels": labels, "response_limit_recoveries": []}
    if damage == "provenance":
        operations[1]["result"]["input_id"] = "wrong"
    elif damage == "diagnostic":
        operations[1]["result"]["scan_errors"] = 1
    elif damage == "target":
        operations[1]["arguments"]["method_descriptor"] = "LWrong;->target()V"
    elif damage == "labels":
        collection["page_labels"] = list(reversed(labels))
    elif damage == "extra":
        operations.append(copy.deepcopy(operations[-1]))
    elif damage == "recovery":
        collection["response_limit_recoveries"] = [{"offset": 0, "limit": 2}]
    if damage:
        with pytest.raises(AssertionError):
            await verifier.verify_native_collection(
                operations, collection, opened, query, expected, 1
            )
    else:
        result = await verifier.verify_native_collection(
            operations, collection, opened, query, expected, 1
        )
        assert result["status"] == "passed" and result["total"] == 2
