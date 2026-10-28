"""Artifact handles share immutable input, lazy DEX and the existing lifetime owner."""

import hashlib
import io
import json
import os
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from test_dex import empty_dex

from droidasc_mcp.runner import DroidAscRunner
from droidasc_mcp.server import build_server
from droidasc_mcp.service import DroidAscService


@pytest.fixture
def service(settings):
    service = DroidAscService(settings)
    yield service
    service.close()


def artifact(tmp_path, suffix=".apk", *, dex=True):
    path = tmp_path / ("sample" + suffix)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("assets/value.txt", "original")
        if dex:
            archive.writestr("classes.dex", empty_dex())
        archive.writestr("AndroidManifest.xml", '<manifest package="test.sample"/>')
    return path


@pytest.mark.parametrize("raw_dex", [False, True])
def test_private_snapshot_roots_use_resolved_paths(settings, tmp_path, raw_dex):
    path = tmp_path / "original.dex" if raw_dex else artifact(tmp_path)
    if raw_dex:
        path.write_bytes(empty_dex())
    (tmp_path / "alias").mkdir()
    aliased = tmp_path / "alias" / ".." / path.name
    assert str(aliased.parent) != str(aliased.parent.resolve())
    analysis = SimpleNamespace(
        path=path,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        artifact_type="dex" if raw_dex else "apk",
    )
    runner = DroidAscRunner(settings)
    if not raw_dex:
        result = runner.query_archive(aliased, {"operation": "list_entries"}, analysis=analysis)
        assert result["status"] == "ok" and result["apk_sha256"] == analysis.sha256
    prepared = tmp_path / "prepared"
    prepared.mkdir()
    result = runner.prepare_analysis(aliased, prepared, 1024**2, None, analysis)
    assert result["status"] == "ok", result
    assert result["artifact_sha256"] == analysis.sha256


def test_load_reuses_one_owner_and_dex_is_lazy(service, tmp_path):
    path = artifact(tmp_path)
    loaded = service.load_artifact(str(path), max_uncompressed_bytes=1024**2)
    assert loaded["status"] == "ok"
    key = loaded["analysis_id"]
    assert loaded["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert loaded["artifact_type"] == "apk"
    assert loaded["dex_count"] == 1
    assert set(loaded["capabilities"]) == {"archive", "dex", "manifest", "signing"}
    entry = service.sessions.entries[key]
    root = Path(entry.storage.name)
    assert not (root / "dex").exists()
    metadata = service.query_artifact(key, operation="read_entry", entry_path="assets/value.txt")
    assert metadata["content"] == "original"
    assert metadata["artifact_path"] == str(path)
    assert metadata["artifact_sha256"] == loaded["sha256"]
    assert not (root / "dex").exists()
    result = service.query_dex_session(key, operation="info", offset=0, limit=1)
    assert result["status"] == "ok", result
    assert result["artifact_sha256"] == loaded["sha256"]
    assert result["sources"][0]["path"] == str(path)
    assert (root / "dex" / "prepared.json").is_file()
    assert len(service.sessions.entries) == 1
    assert service.close_artifact(key)["closed"]
    assert not root.exists()
    assert not service.close_artifact(key)["closed"]


def test_original_replacement_does_not_change_handle(service, tmp_path):
    path = artifact(tmp_path)
    loaded = service.load_artifact(str(path), max_uncompressed_bytes=1024**2)
    path.unlink()
    path.write_bytes(b"replacement")
    key = loaded["analysis_id"]
    result = service.query_artifact(key, operation="read_entry", entry_path="assets/value.txt")
    assert result["content"] == "original"
    assert result["artifact_sha256"] == loaded["sha256"]
    result = service.query_dex_session(key, operation="info", offset=0, limit=1)
    assert result["status"] == "ok", result
    assert result["artifact_sha256"] == loaded["sha256"]


def test_archive_without_dex_remains_readable_after_dex_failure(service, tmp_path):
    loaded = service.load_artifact(
        str(artifact(tmp_path, ".jar", dex=False)), max_uncompressed_bytes=1024**2
    )
    key = loaded["analysis_id"]
    assert "dex" not in loaded["capabilities"]
    assert (
        service.query_dex_session(key, operation="info", offset=0, limit=1)["code"]
        == "no_analyzable_dex"
    )
    assert service.query_artifact(key, operation="list_entries")["total"] == 2
    assert service.sessions.reserved == service.sessions.opening == 0
    assert not (Path(service.sessions.entries[key].storage.name) / "dex").exists()


def test_raw_dex_handle_can_prepare_and_read(service, tmp_path):
    path = tmp_path / "input.dex"
    path.write_bytes(empty_dex())
    loaded = service.load_artifact(str(path), max_uncompressed_bytes=1024**2)
    assert loaded["capabilities"] == ["dex"]
    key = loaded["analysis_id"]
    result = service.query_dex_session(key, operation="info", offset=0, limit=1)
    assert result["status"] == "ok", result
    assert result["sources"][0]["path"] == str(path)
    assert result["artifact_sha256"] == loaded["sha256"]
    summary = service.query_artifact(key, operation="artifact_inventory", include_summary=True)
    assert summary["status"] == "ok" and summary["artifact_type"] == "dex"
    assert summary["items"][0]["path"] == path.name


def test_aar_nested_dex_is_discoverable_and_prepares_on_same_handle(service, tmp_path):
    jar = io.BytesIO()
    with zipfile.ZipFile(jar, "w") as archive:
        archive.writestr("classes.dex", empty_dex())
    path = tmp_path / "nested.aar"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("classes.jar", jar.getvalue())
    loaded = service.load_artifact(str(path), max_uncompressed_bytes=1024**2)
    assert loaded["status"] == "ok" and loaded["dex_count"] == 1
    assert "dex" in loaded["capabilities"]
    result = service.query_dex_session(loaded["analysis_id"], operation="info", offset=0, limit=1)
    assert result["status"] == "ok", result
    assert result["sources"][0]["container_entry"] == "classes.jar!/classes.dex"
    assert result["sources"][0]["path"] == str(path)


def test_snapshot_tampering_is_rejected(service, tmp_path):
    path = artifact(tmp_path)
    loaded = service.load_artifact(str(path), max_uncompressed_bytes=1024**2)
    entry = service.sessions.entries[loaded["analysis_id"]]
    snapshot = Path(entry.storage.name) / "input" / path.name
    with zipfile.ZipFile(snapshot, "a") as archive:
        archive.writestr("changed", b"changed")
    for result in (
        service.query_artifact(loaded["analysis_id"], operation="list_entries"),
        service.query_dex_session(loaded["analysis_id"], operation="info", offset=0, limit=1),
    ):
        assert result["code"] == "input_changed", result
    assert service.sessions.reserved == service.sessions.opening == 0


def test_snapshot_budget_shared_with_legacy_sessions(settings, tmp_path):
    service = DroidAscService(replace(settings, max_dex_sessions=1))
    try:
        loaded = service.load_artifact(str(artifact(tmp_path)), max_uncompressed_bytes=1024**2)
        root = Path(service.sessions.entries[loaded["analysis_id"]].storage.name)
        dex = tmp_path / "replacement.dex"
        dex.write_bytes(empty_dex())
        legacy = service.open_dex_session([str(dex)])
        assert legacy["status"] == "ok"
        assert not root.exists()
        assert (
            service.query_artifact(loaded["analysis_id"], operation="list_entries")["code"]
            == "session_not_found"
        )
    finally:
        service.close()


@pytest.mark.parametrize("failure", [RuntimeError("worker failure"), KeyboardInterrupt()])
def test_failed_snapshot_releases_reservation_and_files(service, tmp_path, monkeypatch, failure):
    original = service.runner.snapshot_artifact
    roots = []

    def fail(path, root, size):
        roots.append(root)
        assert original(path, root, size)["status"] == "ok"
        raise failure

    monkeypatch.setattr(service.runner, "snapshot_artifact", fail)
    with pytest.raises(type(failure)):
        service.load_artifact(str(artifact(tmp_path)), max_uncompressed_bytes=1024**2)
    assert not service.sessions.entries
    assert service.sessions.reserved == service.sessions.opening == 0
    assert roots and all(not root.exists() for root in roots)


@pytest.mark.parametrize("failure", [RuntimeError("worker failure"), KeyboardInterrupt()])
def test_failed_lazy_preparation_preserves_snapshot_for_retry(
    service, tmp_path, monkeypatch, failure
):
    loaded = service.load_artifact(str(artifact(tmp_path)), max_uncompressed_bytes=1024**2)
    key = loaded["analysis_id"]
    entry = service.sessions.entries[key]
    size = entry.size
    original = service.runner.prepare_analysis

    def fail(*args):
        assert original(*args)["status"] == "ok"
        raise failure

    monkeypatch.setattr(service.runner, "prepare_analysis", fail)
    with pytest.raises(type(failure)):
        service.query_dex_session(key, operation="info", offset=0, limit=1)
    assert entry.size == size and entry.users == 0 and not entry.prepared
    assert not entry.root.exists() and entry.snapshot.exists()
    assert service.sessions.reserved == service.sessions.opening == 0
    assert service.query_artifact(key, operation="list_entries")["total"] == 3
    monkeypatch.setattr(service.runner, "prepare_analysis", original)
    assert service.query_dex_session(key, operation="info", offset=0, limit=1)["status"] == "ok"


def test_lazy_capacity_failure_retains_readable_metadata(service, tmp_path):
    loaded = service.load_artifact(str(artifact(tmp_path)), max_uncompressed_bytes=1024**2)
    key = loaded["analysis_id"]
    service.sessions.settings = replace(service.settings, max_dex_session_bytes=4 * 1024**2)
    assert (
        service.query_dex_session(key, operation="info", offset=0, limit=1)["code"]
        == "session_capacity"
    )
    assert service.query_artifact(key, operation="list_entries")["total"] == 3
    assert service.sessions.reserved == service.sessions.opening == 0


def test_metadata_query_pins_snapshot_against_close_expiry_and_eviction(
    service, tmp_path, monkeypatch
):
    service.sessions.settings = replace(service.settings, max_dex_sessions=1)
    path = artifact(tmp_path)
    key = service.load_artifact(str(path), max_uncompressed_bytes=1024**2)["analysis_id"]
    entry = service.sessions.entries[key]
    root = Path(entry.storage.name)
    entered, release = threading.Event(), threading.Event()
    original = service.runner.query_archive

    def wait(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(service.runner, "query_archive", wait)
    with ThreadPoolExecutor() as pool:
        future = pool.submit(service.query_artifact, key, operation="list_entries")
        try:
            assert entered.wait(2)
            entry.touched -= 3600
            assert service.sessions.status()["open_count"] == 1
            assert (
                service.load_artifact(str(path), max_uncompressed_bytes=1024**2)["code"]
                == "session_capacity"
            )
            assert service.close_artifact(key)["cleanup_pending"]
            assert root.exists()
            assert (
                service.query_artifact(key, operation="list_entries")["code"] == "session_not_found"
            )
        finally:
            release.set()
        assert future.result()["status"] == "ok"
    assert not root.exists() and not service.sessions.entries


def test_concurrent_lazy_queries_prepare_once_and_close_waits(service, tmp_path, monkeypatch):
    key = service.load_artifact(str(artifact(tmp_path)), max_uncompressed_bytes=1024**2)[
        "analysis_id"
    ]
    entry = service.sessions.entries[key]
    root = Path(entry.storage.name)
    entered, release = threading.Event(), threading.Event()
    original = service.runner.prepare_analysis
    calls = []

    def wait(*args):
        calls.append(args)
        entered.set()
        assert release.wait(5)
        return original(*args)

    monkeypatch.setattr(service.runner, "prepare_analysis", wait)
    with ThreadPoolExecutor() as pool:
        first = pool.submit(service.query_dex_session, key, operation="info", offset=0, limit=1)
        try:
            assert entered.wait(2)
            second = pool.submit(
                service.query_dex_session, key, operation="info", offset=0, limit=1
            )
            deadline = time.monotonic() + 2
            while service.sessions.status()["active_queries"] != 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            assert service.sessions.status()["active_queries"] == 2
            assert service.close_artifact(key)["cleanup_pending"]
        finally:
            release.set()
        assert first.result()["status"] == second.result()["status"] == "ok"
    assert len(calls) == 1 and not root.exists()
    assert not service.sessions.entries and service.sessions.reserved == 0


def test_shutdown_during_snapshot_never_publishes_handle(service, tmp_path, monkeypatch):
    original = service.runner.snapshot_artifact
    entered, release = threading.Event(), threading.Event()
    roots = []

    def wait(path, root, size):
        roots.append(root)
        result = original(path, root, size)
        entered.set()
        assert release.wait(5)
        return result

    monkeypatch.setattr(service.runner, "snapshot_artifact", wait)
    with ThreadPoolExecutor() as pool:
        future = pool.submit(
            service.load_artifact, str(artifact(tmp_path)), max_uncompressed_bytes=1024**2
        )
        try:
            assert entered.wait(2)
            service.close()
        finally:
            release.set()
        assert future.result()["code"] == "session_store_closed"
    assert all(not root.exists() for root in roots)
    assert service.sessions.reserved == service.sessions.opening == 0


@pytest.mark.parametrize("name", ["../outside", "a\\b", "C:/absolute", "a/./b", "nul\x00tail"])
def test_load_preserves_stricter_zip_path_validation(service, tmp_path, name):
    path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(path, "w") as archive:
        info = zipfile.ZipInfo("raw-entry")
        # Retain the malformed on-wire name across Windows ZipInfo normalization.
        info.filename = info.orig_filename = name
        archive.writestr(info, b"invalid")
    assert path.read_bytes().count(name.encode()) == 2
    assert (
        service.load_artifact(str(path), max_uncompressed_bytes=1024**2)["code"] == "unsafe_entry"
    )
    assert not service.sessions.entries and service.sessions.reserved == 0


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["memory", "stdio"])
@pytest.mark.parametrize("profile", ["legacy", "artifact_preview", "artifact"])
async def test_handle_calls_work_over_mcp_with_legacy_compatibility(
    settings, tmp_path, transport, profile
):
    path = artifact(tmp_path)
    endpoint = (
        build_server(replace(settings, tool_profile=profile))
        if transport == "memory"
        else StdioServerParameters(
            command=sys.executable,
            args=["-m", "droidasc_mcp"],
            env={
                **os.environ,
                "DROIDASC_MCP_ALLOWED_ROOTS": str(tmp_path),
                "DROIDASC_MCP_TOOL_PROFILE": profile,
            },
        )
    )
    async with Client(endpoint) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        assert len(names) == {"legacy": 18, "artifact_preview": 11, "artifact": 34}[profile]
        assert ("load_artifact" in names) == (profile != "legacy")
        loaded = await client.call_tool(
            "load_artifact", {"path": str(path), "max_uncompressed_bytes": 1024**2}
        )
        assert not loaded.is_error
        key = loaded.structured_content["analysis_id"]
        summary = await client.call_tool("apk_get_summary", {"analysis_id": key})
        assert not summary.is_error
        assert summary.structured_content["summary"]["manifest"]["package_name"] == "test.sample"
        manifest = await client.read_resource(f"droidasc://analysis/{key}/manifest?limit=1")
        assert (
            json.loads(manifest.contents[0].text)["artifact_sha256"]
            == (loaded.structured_content["sha256"])
        )
        for tool, args in (
            ("apk_get_manifest", {"include_xml": True}),
            ("apk_list_entries", {"kind": "asset"}),
            ("apk_get_resource_content", {"path": "assets/value.txt"}),
            ("apk_get_signing_info", {}),
        ):
            result = await client.call_tool(tool, {"analysis_id": key, **args})
            assert not result.is_error, result
            assert (
                result.structured_content["artifact_sha256"] == loaded.structured_content["sha256"]
            )
        invalid = await client.call_tool(
            "apk_get_resource_content",
            {"analysis_id": key, "path": "assets/value.txt", "max_bytes": 1048576},
        )
        assert invalid.is_error
        code = await client.call_tool(
            "asc_query_dex_session", {"session_id": key, "operation": "info"}
        )
        assert not code.is_error and code.structured_content["status"] == "ok"
        old_manifest = await client.read_resource(
            "droidasc://artifact/manifest?" + urlencode({"apk_path": str(path)})
        )
        assert (
            json.loads(old_manifest.contents[0].text)["apk_sha256"]
            == (loaded.structured_content["sha256"])
        )
        closed = await client.call_tool("close_artifact", {"analysis_id": key})
        assert not closed.is_error and closed.structured_content["closed"]
