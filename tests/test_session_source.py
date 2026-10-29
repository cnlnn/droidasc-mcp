"""Complete-source snapshots share the CLI cache and the session lifetime owner."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from test_native_directory import class_dex

from droidasc_mcp.runner import DroidAscError, DroidAscRunner, Snapshot
from droidasc_mcp.service import DroidAscService
from droidasc_mcp.worker_errors import response_limit


@pytest.fixture
def source_session(settings, tmp_path):
    path = tmp_path / "input.dex"
    path.write_bytes(class_dex(["Lfixture/C;"]))
    service = DroidAscService(settings)
    try:
        key = service.open_dex_session([str(path)])["session_id"]
        yield service, key
    finally:
        service.close()


def query(service, key, offset=0, limit=1):
    return service.query_dex_session(
        key,
        operation="get_class_source",
        class_name="fixture.C",
        threads=1,
        offset=offset,
        limit=limit,
    )


def test_complete_pages_reuse_one_worker_and_release_on_close(source_session, monkeypatch):
    service, key = source_session
    calls = []
    original = service.runner._run_dex_request

    def execute(request, root):
        calls.append(request)
        return original(request, root)

    monkeypatch.setattr(service.runner, "_run_dex_request", execute)
    whole = query(service, key, limit=100)
    assert whole["status"] == "ok", whole
    pages = [query(service, key, offset) for offset in range(whole["total"])]
    assert "\n".join(p["source"] for p in pages) == whole["source"]
    assert len(calls) == 1 and calls[0]["source_snapshot"] is True
    for offset, page in enumerate(pages):
        assert set(page) == set(whole) and "items" not in page
        assert page["offset"] == offset and page["total"] == whole["total"]
        assert page["sources"] == whole["sources"]
        assert page["dex_entry"] == whole["dex_entry"] == "classes.dex"
    assert service.runner._cache
    assert service.sessions.close(key)["status"] == "ok"
    assert not service.runner._cache


def test_cached_responses_are_independent(source_session):
    service, key = source_session
    first = query(service, key)
    first["sources"].clear()
    first["source"] = "mutated"
    second = query(service, key)
    assert second["sources"] and second["source"] != "mutated"


@pytest.mark.parametrize("changed", ["prepared.json", "owners.sqlite", "analysis.apk"])
def test_preparation_identity_changes_invalidate_source(source_session, monkeypatch, changed):
    service, key = source_session
    assert query(service, key)["status"] == "ok"
    root = service.sessions.entries[key].root
    path = root / changed
    data = path.read_bytes()
    path.write_bytes(data)
    calls = []
    original = service.runner._run_dex_request

    def execute(request, workspace):
        calls.append(request)
        return original(request, workspace)

    monkeypatch.setattr(service.runner, "_run_dex_request", execute)
    assert query(service, key)["status"] == "ok"
    assert len(calls) == 1


def test_engine_mismatch_never_reuses_source(source_session):
    service, key = source_session
    assert query(service, key)["status"] == "ok"
    path = service.sessions.entries[key].root / "prepared.json"
    metadata = json.loads(path.read_text())
    metadata["common"]["engine_version"] = "changed"
    path.write_text(json.dumps(metadata))
    assert query(service, key)["code"] == "engine_changed"


def test_equal_concurrent_pages_coalesce_with_one_worker_slot(source_session, monkeypatch):
    service, key = source_session
    service.runner._slots = threading.BoundedSemaphore(1)
    original = service.runner._run_dex_request
    started, release = threading.Event(), threading.Event()
    calls = []

    def execute(request, workspace):
        calls.append(request)
        started.set()
        assert release.wait(5)
        return original(request, workspace)

    monkeypatch.setattr(service.runner, "_run_dex_request", execute)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(query, service, key, 0)
        assert started.wait(5)
        second = pool.submit(query, service, key, 1)
        release.set()
        one, two = first.result(5), second.result(5)
    assert one["status"] == two["status"] == "ok"
    assert one["source"] != two["source"] and len(calls) == 1


def test_snapshot_retention_failure_preserves_valid_page(source_session, monkeypatch):
    service, key = source_session
    expected = query(service, key)
    service.runner.forget_snapshots(service.sessions.entries[key].root)

    def fail(*args, **kwargs):
        raise DroidAscError("Decoded snapshot exceeds memory budget")

    monkeypatch.setattr(Snapshot, "build", fail)
    assert query(service, key) == expected
    assert not service.runner._cache


def test_missing_class_errors_are_not_cached(source_session):
    service, key = source_session
    for _ in range(2):
        result = service.query_dex_session(
            key, operation="get_class_source", class_name="absent.C", threads=1, offset=0, limit=1
        )
        assert result["code"] == "class_not_found"
    assert not service.runner._cache


def test_disk_capacity_falls_back_without_evicting_session(source_session, monkeypatch):
    service, key = source_session
    original = service.runner._run_dex_request
    requests = []
    service.sessions.settings = replace(service.settings, max_dex_session_bytes=1)

    def execute(request, workspace):
        requests.append(request)
        return original(request, workspace)

    monkeypatch.setattr(service.runner, "_run_dex_request", execute)
    assert query(service, key)["status"] == "ok"
    assert requests[0]["query"]["_source_snapshot"] is False
    assert "source_snapshot" not in requests[0]
    assert key in service.sessions.entries and service.sessions.reserved == 0


def test_source_export_retains_unicode_and_empty_lines(settings, tmp_path, monkeypatch):
    path = tmp_path / "input.apk"
    path.touch()
    subject = DroidAscRunner(settings)
    monkeypatch.setattr(subject, "_execute", lambda args: "one\n\n\U0001f600\nlast".encode())
    output = tmp_path / "source.txt"
    page = subject.get_class_source(
        path, class_name="Lfixture/C;", threads=1, offset=0, limit=100, snapshot_path=output
    )
    snapshot = Snapshot.build(output.read_bytes(), sort=False, budget=settings.max_output_bytes)
    assert page.items == list(snapshot.lines) == ["one", "", "\U0001f600", "last"]
    assert not output.with_suffix(".partial").exists()


def test_optional_export_io_failure_keeps_original_page(settings, tmp_path, monkeypatch):
    path = tmp_path / "input.apk"
    path.touch()
    subject = DroidAscRunner(settings)
    monkeypatch.setattr(subject, "_execute", lambda args: b"valid\n")
    output = tmp_path / "absent" / "source.txt"
    assert subject.get_class_source(
        path, class_name="Lfixture/C;", threads=1, offset=0, limit=1, snapshot_path=output
    ).items == ["valid"]
    assert not output.exists()


def test_close_waits_for_source_then_removes_cached_text(source_session, monkeypatch):
    service, key = source_session
    root = service.sessions.entries[key].root
    original = service.runner._run_dex_request
    started, release = threading.Event(), threading.Event()

    def execute(request, workspace):
        started.set()
        assert release.wait(5)
        return original(request, workspace)

    monkeypatch.setattr(service.runner, "_run_dex_request", execute)
    with ThreadPoolExecutor(1) as pool:
        pending = pool.submit(query, service, key)
        assert started.wait(5)
        assert service.sessions.close(key)["cleanup_pending"]
        assert root.exists()
        release.set()
        assert pending.result(5)["status"] == "ok"
    assert not root.exists() and not service.runner._cache
    assert not service.runner._inflight and service.sessions.reserved == 0


def test_cached_page_preserves_total_wire_response_limit(settings, tmp_path, monkeypatch):
    subject = DroidAscRunner(settings)
    (tmp_path / "analysis.apk").touch()
    query = {
        "operation": "get_class_source",
        "class_name": "Lfixture/C;",
        "threads": 1,
        "offset": 0,
        "limit": 1,
    }

    def execute(request, workspace):
        (workspace / "source.txt").write_bytes(b"small\n" + b"x" * 40000 + b"\n")
        return {
            "status": "ok",
            "class_name": query["class_name"],
            "dex_entry": "classes.dex",
            "sources": [{"path": "x" * 230000}],
            "source": "small",
            "total": 2,
            "offset": 0,
            "limit": 1,
            "truncated": True,
            "has_more": True,
            "next_offset": 1,
        }

    monkeypatch.setattr(subject, "_run_dex_request", execute)
    assert subject.query_dex_session(tmp_path, query)["status"] == "ok"
    assert subject.query_dex_session(tmp_path, {**query, "offset": 1}) == response_limit()


@pytest.mark.parametrize("invalid", [{"offset": -1}, {"limit": 0}, {"threads": 0}])
def test_invalid_source_bounds_keep_worker_error_envelope(source_session, invalid):
    service, key = source_session
    assert query(service, key)["status"] == "ok"
    result = service.query_dex_session(
        key,
        **{
            "operation": "get_class_source",
            "class_name": "fixture.C",
            "threads": 1,
            "offset": 0,
            "limit": 1,
            **invalid,
        },
    )
    assert result["status"] == "error" and result["code"] == "invalid_query"
