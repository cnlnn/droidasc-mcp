"""Real subprocess, transport, and optional real-APK acceptance checks."""

import hashlib
import os
import socket
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from contextlib import suppress
from dataclasses import replace
from pathlib import Path

import psutil
import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from droidasc_mcp.runner import (
    DroidAscError,
    DroidAscRunner,
    _start_process,
    _terminate_process_tree,
)


@pytest.fixture
def process_runner(settings, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).parent))
    return DroidAscRunner(
        replace(settings, timeout_seconds=2, max_output_bytes=32768), module_name="process_fixture"
    )


def alive(pid):
    # Zombies have no executable workload; their reaper may run later.
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def test_real_live_tree_timeout_cleanup(process_runner, tmp_path):
    start = time.monotonic()
    try:
        with pytest.raises(DroidAscError, match="timed out"):
            process_runner._execute(["tree", str(tmp_path)])
        processes = []
        for name in ("parent.pid", "child.pid"):
            pid = int((tmp_path / name).read_text())
            with suppress(psutil.NoSuchProcess):
                processes.append(psutil.Process(pid))
        _, running = psutil.wait_procs(processes, timeout=2)
        for process in running:
            with suppress(psutil.NoSuchProcess):
                assert process.status() == psutil.STATUS_ZOMBIE
        assert time.monotonic() - start < 8
    finally:
        for name in ("child.pid", "parent.pid"):
            path = tmp_path / name
            if path.exists():
                with suppress(psutil.NoSuchProcess):
                    psutil.Process(int(path.read_text())).kill()


@pytest.mark.parametrize("mode", ["orphan", "orphan-tree"])
def test_real_orphan_cleanup(process_runner, tmp_path, mode):
    start = time.monotonic()
    try:
        with pytest.raises(DroidAscError, match="timed out"):
            process_runner._execute([mode, str(tmp_path)])
        names = ["parent.pid", "child.pid"]
        if mode == "orphan-tree":
            names.append("grandchild.pid")
        pids = [int((tmp_path / name).read_text()) for name in names]
        deadline = time.monotonic() + 2
        while any(alive(pid) for pid in pids) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not any(alive(pid) for pid in pids)
        assert not any(t.name.startswith("droidasc-reader-") for t in threading.enumerate())
        elapsed = time.monotonic() - start
        assert elapsed < 5
        print(f"orphan_cleanup elapsed={elapsed:.3f}s child_executing=false")
    finally:
        for path in tmp_path.glob("*.pid"):
            pid = int(path.read_text())
            if alive(pid):
                with suppress(psutil.NoSuchProcess):
                    psutil.Process(pid).kill()


@pytest.mark.parametrize("mode", ["detached", "tree-stdout"])
def test_descendant_cleanup_on_success_and_overflow(process_runner, tmp_path, mode):
    try:
        if mode == "detached":
            assert process_runner._execute([mode, str(tmp_path)]).strip() == b"ok"
        else:
            with pytest.raises(DroidAscError, match="output exceeds"):
                process_runner._execute([mode, str(tmp_path)])
        pids = [int((tmp_path / name).read_text()) for name in ("parent.pid", "child.pid")]
        deadline = time.monotonic() + 2
        while any(alive(pid) for pid in pids) and time.monotonic() < deadline:
            time.sleep(0.01)
        assert not any(alive(pid) for pid in pids)
        assert not any(t.name.startswith("droidasc-reader-") for t in threading.enumerate())
    finally:
        for path in tmp_path.glob("*.pid"):
            with suppress(psutil.NoSuchProcess):
                psutil.Process(int(path.read_text())).kill()


def test_repeated_operations_release_resources(process_runner, tmp_path):
    owner = psutil.Process()
    count = owner.num_handles if os.name == "nt" else owner.num_fds
    # Warm imports and the platform backend before measuring per-operation resources.
    process_runner._execute(["info", str(tmp_path)])
    baseline = count()
    for _ in range(12):
        process_runner._execute(["info", str(tmp_path)])
    assert count() <= baseline + 2
    assert not any(t.name.startswith("droidasc-reader-") for t in threading.enumerate())


def test_operation_cleanup_does_not_kill_another_tree(tmp_path):
    operations = []
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parent)}
    try:
        for index in range(2):
            root = tmp_path / str(index)
            root.mkdir()
            operations.append(
                _start_process([sys.executable, "-m", "process_fixture", "child", str(root)], env)
            )
        deadline = time.monotonic() + 5
        while not all((tmp_path / str(i) / "child.pid").exists() for i in range(2)):
            assert time.monotonic() < deadline, "Workers did not start"
            time.sleep(0.01)
        first, first_job = operations[0]
        second, _ = operations[1]
        _terminate_process_tree(first, first_job)
        first.wait(timeout=2)
        assert second.poll() is None
    finally:
        for process, job in operations:
            _terminate_process_tree(process, job)
            process.wait(timeout=2)
            process.stdout.close()
            process.stderr.close()


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_real_stream_limit(process_runner, tmp_path, stream):
    started = time.monotonic()
    owner = psutil.Process()
    baseline = owner.memory_info().rss
    samples = [baseline]
    stopped = threading.Event()

    def sample():
        while not stopped.wait(0.002):
            samples.append(owner.memory_info().rss)

    sampler = threading.Thread(target=sample)
    sampler.start()
    try:
        with pytest.raises(DroidAscError, match="output exceeds"):
            process_runner._execute([stream, str(tmp_path)])
    finally:
        stopped.set()
        sampler.join(timeout=2)
    elapsed = time.monotonic() - started
    assert elapsed < 2
    assert not list(tmp_path.iterdir())
    delta = max(samples) - baseline
    assert delta < 16 * 1024 * 1024
    print(f"{stream}_limit elapsed={elapsed:.3f}s result_files=0 host_rss_delta={delta}")


def test_real_reordered_output_pages(process_runner, tmp_path, apk_file, monkeypatch):
    execute = process_runner._execute
    monkeypatch.setattr(process_runner, "_execute", lambda args: execute(["refs", str(tmp_path)]))
    args = ["findrefs", str(apk_file)]
    full = process_runner._run_paged(args, offset=0, limit=100)
    pages = [process_runner._run_paged(args, offset=i, limit=2) for i in (0, 2, 4)]
    assert [line for page in pages for line in page.items] == full.items
    assert len(set(full.items)) == full.total == 6
    assert (tmp_path / "count").read_text() == "1"
    # Expire the real snapshot without waiting 60 seconds.
    key = next(iter(process_runner._cache))
    process_runner._cache[key] = replace(
        process_runner._cache[key], created_at=time.monotonic() - 61
    )
    renewed = process_runner._run_paged(args, offset=0, limit=100)
    assert renewed.items == full.items
    assert (tmp_path / "count").read_text() == "2"
    print("reordered_pages rows=6 duplicates=0 missing=0 initial_executions=1 expired_executions=2")


def test_metadata_uses_worker_and_semaphore(process_runner, tmp_path, monkeypatch):
    execute = process_runner._execute
    monkeypatch.setattr(
        process_runner, "_execute", lambda args, **kwargs: execute(["info", str(tmp_path)])
    )
    assert process_runner.apk_info(tmp_path, False)["pid"] != os.getpid()
    for _ in range(process_runner.settings.max_parallel):
        process_runner._slots.acquire()
    try:
        with pytest.raises(DroidAscError, match="queue timed out"):
            process_runner.apk_info(tmp_path, False)
    finally:
        for _ in range(process_runner.settings.max_parallel):
            process_runner._slots.release()


@pytest.fixture
def http_endpoint(tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    env = os.environ.copy()
    env["DROIDASC_MCP_ALLOWED_ROOTS"] = os.getenv("ASC_TEST_ROOT", str(tmp_path))
    with (tmp_path / "http.log").open("wb") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "droidasc_mcp",
                "--transport",
                "streamable-http",
                "--port",
                str(port),
            ],
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    pytest.fail("HTTP startup failed: " + (tmp_path / "http.log").read_text())
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                        break
                except OSError:
                    time.sleep(0.05)
            else:
                pytest.fail("HTTP readiness timed out")
            yield f"http://127.0.0.1:{port}/mcp"
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_transport_roundtrip(transport, request, apk_file):
    env = os.environ.copy()
    env["DROIDASC_MCP_ALLOWED_ROOTS"] = str(apk_file.parent)
    endpoint = (
        request.getfixturevalue("http_endpoint")
        if transport == "http"
        else StdioServerParameters(command=sys.executable, args=["-m", "droidasc_mcp"], env=env)
    )
    async with Client(endpoint) as client:
        tools = await client.list_tools()
        assert len(tools.tools) == 6
        result = await client.call_tool("asc_ping", {})
        assert not result.is_error
        result = await client.call_tool("asc_apk_info", {"apk_path": str(apk_file)})
        assert not result.is_error, result
        assert result.structured_content["has_manifest"]
        denied = await client.call_tool("asc_apk_info", {"apk_path": "/not-an-apk.txt"})
        assert denied.is_error


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_real_apk_all_tools(transport, tmp_path, request, monkeypatch):
    apk = os.getenv("ASC_TEST_APK")
    if not apk:
        pytest.skip("Set ASC_TEST_APK to a built fixture or a local APK")
    apk = str(Path(apk).resolve())
    monkeypatch.setenv("ASC_TEST_ROOT", str(Path(apk).parent))
    env = os.environ.copy()
    env["DROIDASC_MCP_ALLOWED_ROOTS"] = str(Path(apk).parent)
    endpoint = (
        request.getfixturevalue("http_endpoint")
        if transport == "http"
        else StdioServerParameters(command=sys.executable, args=["-m", "droidasc_mcp"], env=env)
    )
    async with Client(endpoint) as client:

        async def call(name, args):
            result = await client.call_tool(name, args)
            assert not result.is_error, result
            return result.structured_content

        assert (await call("asc_ping", {}))["status"] == "ok"
        assert len((await client.list_tools()).tools) == 6
        if os.getenv("ASC_TEST_EXPECT_FIXTURE") == "1":
            await assert_fixture_tools(call, apk)
            print(f"fixture_apk transport={transport} tools=6 reference_kinds=4")
            return
        info = await call("asc_apk_info", {"apk_path": apk})
        assert len(info["sha256"]) == 64
        manifest = await call("asc_get_manifest", {"apk_path": apk, "limit": 2})
        assert "manifest" in manifest["xml"]
        classes = await call("asc_list_classes", {"apk_path": apk, "limit": 2})
        source = await call(
            "asc_get_class_source", {"apk_path": apk, "class_name": classes["items"][0], "limit": 2}
        )
        assert source["source"]
        refs = await call(
            "asc_find_refs", {"apk_path": apk, "kind": "string", "value": "android", "limit": 2}
        )
        assert "total" in refs
        print(f"real_apk transport={transport} tools=6 classes={classes['total']}")


async def assert_fixture_tools(call, apk):
    package = "org.example.droidascfixture"
    probe = "Lorg/example/droidascfixture/Probe;"
    activity = "Lorg/example/droidascfixture/MainActivity;"
    marker = "ASC_FIXTURE_MARKER_v1"
    info = await call("asc_apk_info", {"apk_path": apk})
    assert info["sha256"] == hashlib.sha256(Path(apk).read_bytes()).hexdigest()
    assert info["size_bytes"] == Path(apk).stat().st_size
    assert info["dex_entries"] == ["classes.dex", "classes2.dex"]
    assert info["has_manifest"]

    manifest = await call("asc_get_manifest", {"apk_path": apk, "limit": 1000})
    assert manifest["next_offset"] is None
    root = ET.fromstring(manifest["xml"])
    assert root.tag == "manifest"
    assert root.attrib["package"] == package
    assert root.find("uses-permission") is None
    android = "{http://schemas.android.com/apk/res/android}"
    assert root.find("application/activity").attrib[android + "name"] == package + ".MainActivity"

    query = {"apk_path": apk, "prefix": package}
    classes = await call("asc_list_classes", {**query, "limit": 100})
    assert set(classes["items"]) == {probe, activity, "Lorg/example/droidascfixture/R;"}
    assert classes["total"] == 3
    paged = []
    for offset in range(classes["total"]):
        page = await call("asc_list_classes", {**query, "limit": 1, "offset": offset})
        assert page["next_offset"] == (offset + 1 if offset < classes["total"] - 1 else None)
        paged.extend(page["items"])
    assert paged == classes["items"]

    source = await call(
        "asc_get_class_source",
        {"apk_path": apk, "class_name": package + ".Probe", "limit": 1000},
    )
    assert source["class_name"] == probe
    assert source["next_offset"] is None
    assert all(value in source["source"] for value in ("marker", "visits", marker))

    for kind, value, caller in (
        ("string", marker, probe + "->marker"),
        ("type", package + ".Probe", activity + "->onCreate"),
        ("method", "marker", probe + "->describe"),
        ("field", "visits", probe + "->marker"),
    ):
        args = {"apk_path": apk, "kind": kind, "value": value, "limit": 100}
        if kind in {"method", "field"}:
            args["class_name"] = package + ".Probe"
        refs = await call("asc_find_refs", args)
        assert refs["total"] > 0, (kind, refs)
        assert refs["next_offset"] is None
        assert any(
            caller in item.get("method", "") and item.get("dex") == "classes2.dex"
            for item in refs["items"]
        ), (kind, refs)
        if kind == "string":
            assert any(marker in item.get("matched", "") for item in refs["items"])
