"""Session identity, quotas, lifecycle and concurrent pinning."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest
from mcp import Client

from droidasc_mcp.server import build_server
from droidasc_mcp.sessions import DexSessions


@pytest.fixture
def store(settings, tmp_path):
    runner = Mock()

    def prepare(paths, root, input_bytes):
        (root / "analysis.apk").write_bytes(b"immutable")
        return {"status": "ok", "input_id": "hash", "sources": [{"path": str(p)} for p in paths]}

    runner.prepare_dex.side_effect = prepare
    runner.query_dex_session.return_value = {"status": "ok"}
    store = DexSessions(replace(settings, max_dex_sessions=2), runner)
    yield store
    store.shutdown()


@pytest.fixture
def paths(tmp_path):
    path = tmp_path / "input.dex"
    path.write_bytes(b"data")
    return [path]


def test_capacity_evicts_idle_and_shutdown_cleans(store, paths):
    first = store.open(paths)["session_id"]
    root = Path(store.entries[first].storage.name)
    second = store.open(paths)["session_id"]
    third = store.open(paths)["session_id"]
    assert not root.exists()
    assert store.query(first, {})["code"] == "session_not_found"
    assert set(store.entries) == {second, third}
    roots = [Path(e.storage.name) for e in store.entries.values()]
    store.shutdown()
    assert not store.reaper.is_alive()
    assert all(not p.exists() for p in roots)
    assert store.open(paths)["code"] == "session_store_closed"


@pytest.mark.parametrize("refresh_first", [False, True])
def test_lru_is_ordered_even_when_clock_readings_tie(store, paths, monkeypatch, refresh_first):
    monkeypatch.setattr("droidasc_mcp.sessions.time.monotonic", lambda: 100.0)
    first = store.open(paths)["session_id"]
    second = store.open(paths)["session_id"]
    # Force UUID order opposite to insertion order without depending on random UUIDs.
    store.entries["z"] = store.entries.pop(first)
    store.entries["a"] = store.entries.pop(second)
    if refresh_first:
        store.query("z", {})
    third = store.open(paths)["session_id"]
    assert set(store.entries) == ({"z", third} if refresh_first else {"a", third})


def test_capacity_reservations_include_imports(store, paths):
    store.settings = replace(store.settings, max_dex_session_bytes=1)
    assert store.open(paths)["code"] == "session_capacity"
    store.runner.prepare_dex.assert_not_called()


@pytest.mark.parametrize(
    "operation,format,multiplier",
    [("get_class_source", "auto", 1), ("get_method_source", "java", 7), ("find_refs", "auto", 7)],
)
def test_041_handoff_reserves_and_releases_only_bounded_query_space(
    store, paths, operation, format, multiplier
):
    key = store.open(paths)["session_id"]
    store.entries[key].info["sources"] = [
        {
            "dex_version": "041",
            "size_bytes": 4096,
            "stored_size_bytes": 4096,
            "logical_header_offset": 0,
        },
        {
            "dex_version": "041",
            "size_bytes": 4096,
            "stored_size_bytes": 0,
            "logical_header_offset": 512,
        },
    ]
    reservation = 4096 * multiplier + 1024**2

    def query(root, query):
        assert store.reserved == query["_source_view_budget"] == reservation
        assert store.entries[key].users == 1
        return {"status": "ok"}

    store.runner.query_dex_session.side_effect = query
    assert store.query(key, {"operation": operation, "source_format": format})["status"] == "ok"
    assert store.reserved == 0 and store.entries[key].users == 0
    store.settings = replace(
        store.settings, max_dex_session_bytes=store.entries[key].size + reservation - 1
    )
    store.runner.query_dex_session.reset_mock()
    assert (
        store.query(key, {"operation": operation, "source_format": format})["code"]
        == "session_capacity"
    )
    store.runner.query_dex_session.assert_not_called()
    assert store.reserved == 0 and store.entries[key].users == 0


@pytest.mark.parametrize("failure", [RuntimeError("handoff failed"), KeyboardInterrupt()])
def test_041_handoff_failure_or_cancellation_releases_reservation(store, paths, failure):
    key = store.open(paths)["session_id"]
    store.entries[key].info["sources"] = [
        {"dex_version": "041", "size_bytes": 4096, "logical_header_offset": 512}
    ]
    store.runner.query_dex_session.side_effect = failure
    with pytest.raises(type(failure)):
        store.query(key, {"operation": "get_class_source"})
    assert store.reserved == 0 and store.entries[key].users == 0


def test_concurrent_041_handoff_pins_and_accounts_until_close(store, paths):
    key = store.open(paths)["session_id"]
    entry = store.entries[key]
    entry.info["sources"] = [
        {"dex_version": "041", "size_bytes": 4096, "logical_header_offset": 512}
    ]
    reservation = 4096 + 1024**2
    store.settings = replace(store.settings, max_dex_session_bytes=entry.size + reservation)
    entered, release = threading.Event(), threading.Event()

    def query(root, query):
        entered.set()
        assert release.wait(3)
        assert root.exists()
        return {"status": "ok"}

    store.runner.query_dex_session.side_effect = query
    with ThreadPoolExecutor() as pool:
        future = pool.submit(store.query, key, {"operation": "get_class_source"})
        try:
            assert entered.wait(2)
            assert store.query(key, {"operation": "get_class_source"})["code"] == "session_capacity"
            assert store.reserved == reservation and store.close(key)["cleanup_pending"]
        finally:
            release.set()
        assert future.result()["status"] == "ok"
    assert store.reserved == 0 and not store.entries


@pytest.mark.parametrize("failure", [RuntimeError("failed"), KeyboardInterrupt()])
def test_failed_or_cancelled_open_leaves_no_storage(store, paths, failure):
    roots = []

    def fail(paths, root, input_bytes):
        roots.append(root)
        (root / "partial").write_bytes(b"partial")
        raise failure

    store.runner.prepare_dex.side_effect = fail
    with pytest.raises(type(failure)):
        store.open(paths)
    assert not store.entries
    assert store.reserved == store.opening == 0
    assert all(not root.exists() for root in roots)


def test_idle_ttl_reaper_removes_files_without_new_requests(store, paths):
    store.settings = replace(store.settings, dex_session_ttl_seconds=0.05)
    key = store.open(paths)["session_id"]
    root = Path(store.entries[key].storage.name)
    deadline = time.monotonic() + 2
    while root.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert not root.exists()
    assert store.query(key, {})["code"] == "session_not_found"


def test_inflight_query_pins_files_against_close_eviction_and_ttl(store, paths):
    store.settings = replace(store.settings, max_dex_sessions=1)
    key = store.open(paths)["session_id"]
    root = Path(store.entries[key].storage.name)
    entered, release = threading.Event(), threading.Event()

    def query(root, query):
        entered.set()
        assert release.wait(3)
        assert (root / "analysis.apk").read_bytes() == b"immutable"
        return {"status": "ok"}

    store.runner.query_dex_session.side_effect = query
    with ThreadPoolExecutor() as pool:
        future = pool.submit(store.query, key, {})
        try:
            assert entered.wait(2)
            store.entries[key].touched -= 3600
            assert store.open(paths)["code"] == "session_capacity"
            assert store.close(key)["cleanup_pending"]
            assert store.query(key, {})["code"] == "session_not_found"
            assert root.exists()
        finally:
            release.set()
        assert future.result()["status"] == "ok"
    assert not root.exists()


@pytest.mark.parametrize("same", [False, True])
def test_revision_comparison_pins_both_sessions_until_completion(store, paths, same):
    old = store.open(paths)["session_id"]
    new = old if same else store.open(paths)["session_id"]
    roots = [Path(store.entries[key].storage.name) for key in {old, new}]
    entered, release = threading.Event(), threading.Event()

    def compare(root, query):
        entered.set()
        assert release.wait(3)
        assert root.exists() and Path(query["other_prepared_root"]).exists()
        return {"status": "ok"}

    store.runner.query_dex_session.side_effect = compare
    with ThreadPoolExecutor() as pool:
        future = pool.submit(store.compare, old, new, {})
        try:
            assert entered.wait(2)
            assert all(entry.users == 1 for entry in store.entries.values())
            assert all(store.close(key)["cleanup_pending"] for key in {old, new})
            assert all(root.exists() for root in roots)
        finally:
            release.set()
        assert future.result()["status"] == "ok"
    assert not store.entries and all(not root.exists() for root in roots)


@pytest.mark.parametrize("failure", [RuntimeError("worker killed"), KeyboardInterrupt()])
def test_query_failure_unpins_and_other_session_is_unchanged(store, paths, failure):
    a = store.open(paths)["session_id"]
    b = store.open(paths)["session_id"]
    store.runner.query_dex_session.side_effect = failure
    with pytest.raises(type(failure)):
        store.query(a, {})
    assert store.entries[a].users == 0
    assert not store.close(a)["cleanup_pending"]
    assert Path(store.entries[b].storage.name).exists()
    assert store.query("../outside", {})["code"] == "session_not_found"


def test_concurrent_open_reserves_capacity_before_worker_starts(store, paths):
    store.settings = replace(store.settings, max_dex_sessions=1)
    entered, release = threading.Event(), threading.Event()
    original = store.runner.prepare_dex.side_effect

    def prepare(*args):
        entered.set()
        assert release.wait(3)
        return original(*args)

    store.runner.prepare_dex.side_effect = prepare
    with ThreadPoolExecutor() as pool:
        future = pool.submit(store.open, paths)
        try:
            assert entered.wait(2)
            assert store.open(paths)["code"] == "session_capacity"
        finally:
            release.set()
        assert future.result()["status"] == "ok"
    assert store.opening == store.reserved == 0


@pytest.mark.anyio
async def test_server_lifespan_removes_session_storage(store, settings, paths):
    roots = []
    original = store.runner.prepare_dex.side_effect

    def prepare(paths, root, input_bytes):
        roots.append(root)
        return original(paths, root, input_bytes)

    store.runner.prepare_dex.side_effect = prepare
    async with Client(build_server(settings, store.runner)) as client:
        result = await client.call_tool(
            "asc_open_dex_session", {"dex_paths": [str(p) for p in paths]}
        )
        assert not result.is_error
        assert result.structured_content["status"] == "ok"
        assert roots[0].exists()
    assert not roots[0].exists()
