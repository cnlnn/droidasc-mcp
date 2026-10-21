"""Real subprocess, transport, and optional real-APK acceptance checks."""

import hashlib
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
import zipfile
from contextlib import suppress
from dataclasses import replace
from pathlib import Path

import anyio
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
from droidasc_mcp.server import build_server


@pytest.fixture
def process_runner(settings, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).parent))
    return DroidAscRunner(
        replace(settings, timeout_seconds=2, max_output_bytes=32768), module_name="process_fixture"
    )


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_kotlin_r8_methods(transport, tmp_path, request, monkeypatch):
    apk, mapping = os.getenv("ASC_TEST_COMPLEX_APK"), os.getenv("ASC_TEST_COMPLEX_MAPPING")
    if not apk or not mapping:
        pytest.skip("Build the public complex release APK and provide its R8 mapping")
    if not os.getenv("DROIDASC_MCP_JADX_HOME"):
        pytest.skip("Configure JADX 1.5.5 and JDK 17 for exact method acceptance")
    # Mapping is an acceptance-side oracle; the tool sees only the compiled DEX files.
    blocks = {}
    current = None
    for line in Path(mapping).read_text(encoding="utf-8").splitlines():
        if line and not line.startswith((" ", "#")) and " -> " in line:
            original, renamed = line.removesuffix(":").split(" -> ")
            current = (renamed, [])
            blocks[original] = current
        elif current and line.startswith("    ") and not line.lstrip().startswith("#"):
            current[1].append(line)
    original = "org.example.complex.CoroutineCases"
    renamed, members = blocks[original]
    assert renamed != original, "R8 did not obfuscate the fixture"
    owner = "L" + renamed.replace(".", "/") + ";"

    def method(java_signature, dex_signature):
        names = {line.rsplit(" -> ", 1)[1] for line in members if java_signature in line}
        assert len(names) == 1, (java_signature, names)
        return owner + "->" + names.pop() + dex_signature

    integer = method("java.lang.String overload(int)", "(I)Ljava/lang/String;")
    string = method(
        "java.lang.String overload(java.lang.String)", "(Ljava/lang/String;)Ljava/lang/String;"
    )
    workflow = method(
        "java.lang.Object workflow(java.lang.String,kotlin.coroutines.Continuation)",
        "(Ljava/lang/String;Lkotlin/coroutines/Continuation;)Ljava/lang/Object;",
    )
    # R8 may rename the Continuation interface as well; use its mapping, not a guessed name.
    if "kotlin.coroutines.Continuation" in blocks:
        continuation = "L" + blocks["kotlin.coroutines.Continuation"][0].replace(".", "/") + ";"
        workflow = workflow.replace("Lkotlin/coroutines/Continuation;", continuation)
    state_name = blocks[original + "$workflow$1"][0]
    state_owner = "L" + state_name.replace(".", "/") + ";"
    paths = []
    with zipfile.ZipFile(apk) as archive:
        for name in sorted(archive.namelist()):
            if re.fullmatch(r"classes\d*\.dex", name):
                path = tmp_path / name
                path.write_bytes(archive.read(name))
                paths.append(str(path))
    assert paths
    monkeypatch.setenv("ASC_TEST_ROOT", str(tmp_path))
    env = {**os.environ, "DROIDASC_MCP_ALLOWED_ROOTS": str(tmp_path)}
    endpoint = (
        request.getfixturevalue("http_endpoint")
        if transport == "http"
        else StdioServerParameters(command=sys.executable, args=["-m", "droidasc_mcp"], env=env)
    )
    async with Client(endpoint) as client:
        opened = await client.call_tool("asc_open_dex_session", {"dex_paths": paths})
        assert not opened.is_error, opened
        key = opened.structured_content["session_id"]

        async def query(operation, **args):
            reply = await client.call_tool(
                "asc_query_dex_session", dict(session_id=key, operation=operation, **args)
            )
            assert not reply.is_error, reply
            result = reply.structured_content
            assert result["status"] == "ok", result
            return result

        listed = await query("list_methods", class_name=owner, limit=100)
        assert {integer, string, workflow} <= {r["descriptor"] for r in listed["items"]}
        for descriptor, marker, absent in (
            (integer, "R8_INTEGER:", "R8_STRING:"),
            (string, "R8_STRING:", "R8_INTEGER:"),
        ):
            for mode in ("auto", "smali"):
                result = await query(
                    "get_method_source",
                    method_descriptor=descriptor,
                    source_format=mode,
                    limit=1000,
                )
                assert marker in result["source"] and absent not in result["source"]
        body = await query(
            "get_method_source", method_descriptor=workflow, source_format="smali", limit=1000
        )
        assert "COROUTINE_MARKER:" in body["source"]
        state = await query("list_methods", class_name=state_owner, limit=100)
        assert any(r["has_code"] for r in state["items"])
        refs = await query("find_method_refs", method_descriptor=workflow, limit=1000)
        assert refs["instruction_scan_complete"] is True
        assert any(r["caller"].startswith(state_owner + "->") for r in refs["items"])
        for row in refs["items"]:
            calls = await query("get_method_calls", method_descriptor=row["caller"], limit=1000)
            assert row in calls["items"]
        closed = await client.call_tool("asc_close_dex_session", {"session_id": key})
        assert closed.structured_content["cleanup_pending"] is False


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_structured_method_references(
    transport, tmp_path, smali_dex_files, request, monkeypatch
):
    paths = [str(shutil.copy(p, tmp_path)) for p in smali_dex_files]
    monkeypatch.setenv("ASC_TEST_ROOT", str(tmp_path))
    env = {**os.environ, "DROIDASC_MCP_ALLOWED_ROOTS": str(tmp_path)}
    endpoint = (
        request.getfixturevalue("http_endpoint")
        if transport == "http"
        else StdioServerParameters(command=sys.executable, args=["-m", "droidasc_mcp"], env=env)
    )
    caller = "Lfixture/Caller;->run()V"
    target = "Lfixture/Target;->pick(I)V"
    async with Client(endpoint) as client:

        async def call(tool, **args):
            reply = await client.call_tool(tool, args)
            assert not reply.is_error, reply
            return reply.structured_content

        opened = await call("asc_open_dex_session", dex_paths=paths)
        key = opened["session_id"]

        async def query(operation, method_descriptor, **args):
            return await call(
                "asc_query_dex_session",
                session_id=key,
                operation=operation,
                method_descriptor=method_descriptor,
                **args,
            )

        outgoing = await query("get_method_calls", caller)
        assert outgoing["status"] == "ok", outgoing
        assert outgoing["backend"] == "dexlib2-instructions"
        assert outgoing["total"] == 3
        assert outgoing["scanned_methods"] == 1 and outgoing["scanned_instructions"] == 6
        assert outgoing["instruction_scan_complete"] is True
        assert outgoing["scan_errors"] == 0
        assert outgoing["unresolved_matches"] == 1
        assert outgoing["runtime_target_resolution"] == "not_performed"
        assert outgoing["reference_semantics"] == "declared_method_operand"
        rows = outgoing["items"]
        assert [r["instruction_offset"] for r in rows] == [1, 6, 9]
        assert [r["callee"] for r in rows] == [
            target,
            "Lfixture/Target;->pick(Ljava/lang/String;)V",
            "Lexternal/Missing;->absent()V",
        ]
        assert all(r["caller"] == caller and r["dex_entry"] == "classes.dex" for r in rows)
        assert all(r["offset_unit"] == "code_units_from_method_start" for r in rows)
        assert all(r["opcode"] == "invoke-static" for r in rows)
        assert rows[0]["target_dex_entry"] == "classes2.dex"
        assert rows[0]["target_resolution"] == "defined_in_input"
        assert rows[2]["target_dex_entry"] is None
        assert rows[2]["target_resolution"] == "not_defined_in_input"
        paged = await query("get_method_calls", caller, offset=1, limit=1)
        assert paged["items"] == rows[1:2] and paged["next_offset"] == 2
        beyond = await query("get_method_calls", caller, offset=10, limit=1)
        assert beyond["items"] == [] and beyond["has_more"] is False
        incoming = await query("find_method_refs", target)
        assert incoming["total"] == 1 and incoming["items"] == rows[:1]
        assert incoming["methods_without_code"] == 1
        assert incoming["dynamic_sites"] == 1
        assert incoming["unresolved_sites"][0]["reason"] == "dynamic_target_not_resolved"
        external = await query("find_method_refs", "Lexternal/Missing;->absent()V")
        assert external["total"] == 2 and external["unresolved_matches"] == 2
        assert (await query("get_method_calls", "Lexternal/Missing;->absent()V"))[
            "code"
        ] == "method_not_found"
        assert (await query("find_method_refs", "Lfixture/Target;->pick(J)V"))["total"] == 0
        dynamic = await query(
            "get_method_calls", "Lfixture/Caller;->dynamic(Ljava/lang/invoke/MethodHandle;)V"
        )
        assert dynamic["dynamic_sites"] == 1
        assert dynamic["items"][0]["instruction_offset"] == 1
        assert dynamic["items"][0]["call_site_prototype"] == "(I)I"
        native = await query("get_method_calls", "Lfixture/Caller;->noCode(JLjava/lang/String;)V")
        assert native["total"] == 0 and native["methods_without_code"] == 1
        once = await call(
            "asc_analyze_dex",
            dex_paths=paths,
            operation="get_method_calls",
            method_descriptor=caller,
        )
        assert {k: v for k, v in outgoing.items() if k != "session_id"} == once
        assert (await call("asc_close_dex_session", session_id=key))["cleanup_pending"] is False


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_structured_field_references(
    transport, tmp_path, smali_dex_files, request, monkeypatch
):
    paths = [str(shutil.copy(p, tmp_path)) for p in smali_dex_files]
    hashes = [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths]
    monkeypatch.setenv("ASC_TEST_ROOT", str(tmp_path))
    env = {**os.environ, "DROIDASC_MCP_ALLOWED_ROOTS": str(tmp_path)}
    endpoint = (
        request.getfixturevalue("http_endpoint")
        if transport == "http"
        else StdioServerParameters(command=sys.executable, args=["-m", "droidasc_mcp"], env=env)
    )
    target = "Lfixture/Target;->value:I"
    caller = "Lfixture/Caller;->fields(Lfixture/Target;)V"
    async with Client(endpoint) as client:

        async def call(tool, **args):
            reply = await client.call_tool(tool, args)
            assert not reply.is_error, reply
            return reply.structured_content

        ping = await call("asc_ping")
        assert "find_field_refs" in ping["method_backend"]["operations"]
        assert ping["method_backend"]["field_identity"] == "full_dex_field_descriptor"
        opened = await call("asc_open_dex_session", dex_paths=paths)
        key = opened["session_id"]

        async def query(descriptor=target, **args):
            return await call(
                "asc_query_dex_session",
                session_id=key,
                operation="find_field_refs",
                field_descriptor=descriptor,
                **args,
            )

        incoming = await query()
        assert incoming["status"] == "ok", incoming
        assert incoming["total"] == 2
        assert incoming["reference_semantics"] == "declared_field_operand"
        assert incoming["scan_scope"] == "supplied_dex_methods"
        assert incoming["instruction_scan_complete"] is True
        assert incoming["runtime_target_resolution"] == "not_performed"
        assert "inherited_field_resolution" in incoming["limitations"]
        assert incoming["unresolved_matches"] == 0
        assert incoming["field_descriptor"] == target
        assert incoming["field_access"] == "all"
        rows = incoming["items"]
        assert rows == [
            {
                "caller": caller,
                "field_descriptor": target,
                "access": access,
                "storage": "static",
                "dex_entry": "classes.dex",
                "instruction_offset": offset,
                "offset_unit": "code_units_from_method_start",
                "opcode": opcode,
                "target_resolution": "defined_in_input",
                "target_dex_entry": "classes2.dex",
            }
            for access, offset, opcode in (("read", 0, "sget"), ("write", 2, "sput"))
        ]
        for access, expected in (("read", rows[:1]), ("write", rows[1:])):
            filtered = await query(field_access=access)
            assert filtered["items"] == expected and filtered["total"] == 1
            assert filtered["field_access"] == access
            assert filtered["next_offset"] is None
        page = await query(limit=1)
        assert page["items"] == rows[:1] and page["next_offset"] == 1
        page2 = await query(offset=page["next_offset"], limit=1)
        assert page2["items"] == rows[1:] and page2["next_offset"] is None
        beyond = await query(offset=20, limit=1)
        assert beyond["items"] == [] and beyond["total"] == 2 and not beyond["has_more"]
        for descriptor, offsets, opcodes, storage in (
            ("Lfixture/Target;->value:J", [4, 6], ["iget-wide", "iput-wide"], "instance"),
            (
                "Lfixture/Target;->names:[Ljava/lang/String;",
                [8, 10],
                ["sget-object", "sput-object"],
                "static",
            ),
            ("Lexternal/Missing;->value:I", [12, 14], ["sget", "sput"], "static"),
        ):
            result = await query(descriptor)
            assert result["total"] == 2
            assert [r["instruction_offset"] for r in result["items"]] == offsets
            assert [r["opcode"] for r in result["items"]] == opcodes
            assert [r["access"] for r in result["items"]] == ["read", "write"]
            assert all(
                r["field_descriptor"] == descriptor and r["storage"] == storage
                for r in result["items"]
            )
            if descriptor.startswith("Lexternal/"):
                assert result["unresolved_matches"] == 2
                assert all(
                    r["target_dex_entry"] is None
                    and r["target_resolution"] == "not_defined_in_input"
                    for r in result["items"]
                )
        for descriptor in ("Lfixture/Target;->value:Z", "Lfixture/Target;->unused:I"):
            empty = await query(descriptor)
            assert empty["status"] == "ok" and empty["total"] == 0
        source = await call(
            "asc_query_dex_session",
            session_id=key,
            operation="get_method_source",
            method_descriptor=caller,
            source_format="smali",
        )
        assert source["status"] == "ok" and target in source["source"]
        # Source reads preserve the immutable input and its exact-reference page cache.
        repeated = await query()
        assert repeated["query_cache"]["hit"] is True
        assert {k: v for k, v in repeated.items() if k != "query_cache"} == {
            k: v for k, v in incoming.items() if k != "query_cache"
        }
        once = await call(
            "asc_analyze_dex", dex_paths=paths, operation="find_field_refs", field_descriptor=target
        )
        assert {k: v for k, v in incoming.items() if k != "session_id"} == once
        for bad in (
            {"field_descriptor": "value"},
            {"class_name": "Other"},
            {"field_access": "guess"},
        ):
            invalid = await client.call_tool(
                "asc_query_dex_session",
                {
                    "session_id": key,
                    "operation": "find_field_refs",
                    "field_descriptor": target,
                    **bad,
                },
            )
            assert invalid.is_error, invalid
        assert (await call("asc_query_dex_session", session_id=key))["status"] == "ok"
        assert (await call("asc_close_dex_session", session_id=key))["cleanup_pending"] is False
    assert [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths] == hashes


@pytest.mark.anyio
async def test_native_asc_smali_without_jvm(settings, tmp_path, smali_dex_files):
    paths = [str(shutil.copy(p, tmp_path)) for p in smali_dex_files]
    server = build_server(
        replace(settings, timeout_seconds=60, jadx_home=None, java_executable="java-must-not-run")
    )
    async with Client(server) as client:

        async def query(signature, **args):
            reply = await client.call_tool(
                "asc_analyze_dex",
                dict(
                    dex_paths=paths,
                    operation="get_method_source",
                    method_descriptor="Lfixture/Caller;->" + signature,
                    source_format="smali",
                    limit=100,
                    **args,
                ),
            )
            assert not reply.is_error, reply
            return reply.structured_content

        plain = await query("run()V")
        debug = await query("run()V", debug_info=True)
        assert plain["backend"] == "droidasc" and plain["backend_version"] == "0.1.2.post3"
        assert "pick(I)V" in plain["source"] and "guarded()V" not in plain["source"]
        assert ".line 17" not in plain["source"] and ".line 17" in debug["source"]
        assert debug["debug_info"] is True
        missing = await query("run(I)V")
        assert missing["code"] == "method_not_found" and "source" not in missing
        native = await query("noCode(JLjava/lang/String;)V")
        assert "native noCode(JLjava/lang/String;)V" in native["source"]
        guarded = await query("guarded()V")
        assert ".catch Ljava/lang/Exception;" in guarded["source"]
        unavailable = await client.call_tool(
            "asc_analyze_dex",
            {
                "dex_paths": paths,
                "operation": "find_field_refs",
                "field_descriptor": "Lfixture/Target;->value:I",
            },
        )
        assert not unavailable.is_error
        assert unavailable.structured_content["code"] == "backend_unavailable"
        assert "items" not in unavailable.structured_content
        # Reassemble ASC's public output, not a simulated or name-matched source slice.
        for number, result in enumerate((debug, native, guarded)):
            source = tmp_path / f"roundtrip{number}.smali"
            source.write_text(result["source"], encoding="utf-8")
            output = tmp_path / f"roundtrip{number}.dex"
            home = Path(os.environ["DROIDASC_MCP_JADX_HOME"])
            jars = os.pathsep.join(str(p) for p in sorted((home / "lib").glob("*.jar")))
            java = os.getenv("DROIDASC_MCP_JAVA") or shutil.which("java")
            completed = subprocess.run(
                [
                    java,
                    "-cp",
                    jars,
                    "com.android.tools.smali.smali.Main",
                    "assemble",
                    str(source),
                    "-o",
                    str(output),
                ],
                capture_output=True,
                timeout=60,
            )
            assert completed.returncode == 0 and output.is_file(), completed.stderr.decode()


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


def test_worker_memory_limit_and_recovery(settings, tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).parent))
    subject = DroidAscRunner(
        replace(
            settings,
            timeout_seconds=10,
            max_worker_memory_bytes=96 * 1024 * 1024,
        ),
        module_name="process_fixture",
    )
    with pytest.raises(DroidAscError, match="worker memory limit"):
        subject._execute(["memory", str(tmp_path)])
    assert subject._execute(["info", str(tmp_path)])
    assert not any(t.name.startswith("droidasc-reader-") for t in threading.enumerate())


@pytest.mark.anyio
@pytest.mark.parametrize("mode", ["tree", "tree-delayed"])
async def test_anyio_cancellation_terminates_worker(process_runner, tmp_path, mode):
    subject = DroidAscRunner(
        replace(process_runner.settings, timeout_seconds=10), module_name="process_fixture"
    )
    async with anyio.create_task_group() as group:
        group.start_soon(anyio.to_thread.run_sync, subject._execute, [mode, str(tmp_path)])
        # File existence alone can observe an empty PID file during startup on Windows.
        with anyio.fail_after(5):
            while True:
                try:
                    pids = [
                        int((tmp_path / name).read_text()) for name in ("parent.pid", "child.pid")
                    ]
                except (FileNotFoundError, ValueError):
                    await anyio.sleep(0.01)
                    continue
                assert all(alive(pid) for pid in pids)
                break
        started = time.monotonic()
        group.cancel_scope.cancel()
    assert group.cancel_scope.cancel_called
    deadline = time.monotonic() + 2
    while any(alive(pid) for pid in pids) and time.monotonic() < deadline:
        await anyio.sleep(0.01)
    assert not any(alive(pid) for pid in pids)
    assert time.monotonic() - started < 3
    assert subject._execute(["info", str(tmp_path)])


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
        assert len(tools.tools) == 10
        result = await client.call_tool("asc_ping", {})
        assert not result.is_error
        result = await client.call_tool("asc_apk_info", {"apk_path": str(apk_file)})
        assert not result.is_error, result
        assert result.structured_content["has_manifest"]
        denied = await client.call_tool("asc_apk_info", {"apk_path": "/not-an-apk.txt"})
        assert denied.is_error


@pytest.mark.anyio
async def test_mcp_request_cancellation_stops_worker_and_session_recovers(tmp_path):
    apk = tmp_path / "sleep.apk"
    apk.write_bytes(b"apk")
    env = {
        **os.environ,
        "DROIDASC_MCP_ALLOWED_ROOTS": str(tmp_path),
        "PYTHONPATH": os.pathsep.join(
            filter(None, (str(Path(__file__).parent), os.environ.get("PYTHONPATH")))
        ),
    }
    endpoint = StdioServerParameters(
        command=sys.executable,
        args=["-m", "cancellation_server"],
        env=env,
    )
    async with Client(endpoint) as client:
        started = time.monotonic()
        with anyio.move_on_after(0.5) as scope:
            await client.call_tool(
                "asc_get_manifest", {"apk_path": str(apk), "offset": 0, "limit": 1}
            )
        assert scope.cancel_called
        pid_file = tmp_path / "worker.pid"
        deadline = time.monotonic() + 2
        while not pid_file.exists() and time.monotonic() < deadline:
            await anyio.sleep(0.01)
        assert pid_file.exists()
        pid = int(pid_file.read_text())
        while alive(pid) and time.monotonic() < deadline:
            await anyio.sleep(0.01)
        assert not alive(pid)
        assert time.monotonic() - started < 3
        result = await client.call_tool("asc_ping", {})
        assert not result.is_error


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
        assert len((await client.list_tools()).tools) == 10
        if os.getenv("ASC_TEST_EXPECT_FIXTURE") == "1":

            async def refs_call(**kwargs):
                return await call("asc_find_refs", {"apk_path": apk, **kwargs})

            async def source_call(**kwargs):
                return await call("asc_get_class_source", {"apk_path": apk, **kwargs})

            await assert_reference_stability(refs_call, source_call)
            await assert_fixture_tools(call, apk)
            await assert_fixture_query_boundaries(client, apk, tmp_path)

            async def hierarchy_call(**kwargs):
                return await call("asc_find_refs", {"apk_path": apk, **kwargs})

            await assert_fixture_hierarchy(hierarchy_call, apk)
            print(f"fixture_apk transport={transport} tools=6 reference_kinds=6")
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


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_real_rust_backend(transport, tmp_path, request, monkeypatch):
    if not os.getenv("DROIDASC_MCP_RUST_ASC") or not os.getenv("ASC_TEST_APK"):
        pytest.skip("Configure Rust binary and acceptance APK")
    apk = str(Path(os.environ["ASC_TEST_APK"]).resolve())
    monkeypatch.setenv("ASC_TEST_ROOT", str(Path(apk).parent))
    env = {**os.environ, "DROIDASC_MCP_ALLOWED_ROOTS": str(Path(apk).parent)}
    endpoint = (
        request.getfixturevalue("http_endpoint")
        if transport == "http"
        else StdioServerParameters(command=sys.executable, args=["-m", "droidasc_mcp"], env=env)
    )
    async with Client(endpoint) as client:

        async def call(name, **args):
            result = await client.call_tool(name, {"apk_path": apk, "backend": "rust_asc", **args})
            assert not result.is_error, result
            assert result.structured_content["backend"] == "rust_asc"
            return result.structured_content

        before_hash = hashlib.sha256(Path(apk).read_bytes()).hexdigest()
        manifest = await call("asc_get_manifest", limit=100)
        assert "org.example.droidascfixture" in manifest["xml"]
        classes = await call("asc_list_classes", limit=1000)
        assert "Lorg/example/droidascfixture/Probe;" in classes["items"]
        page = await call("asc_list_classes", offset=1, limit=2)
        assert page["items"] == classes["items"][1:3]

        async def refs_call(**args):
            result = await call("asc_find_refs", **args)
            assert result["coverage"] == "not_verified"
            assert result["instruction_scan_complete"] is False
            return result

        async def source_call(**args):
            return await call("asc_get_class_source", **args)

        await assert_reference_stability(refs_call, source_call)
        empty = await refs_call(kind="string", value="MCP_ABSENT_13c942", limit=1)
        assert empty["total"] == 0
        for value in ("--threads", "-o", "--debug"):
            result = await refs_call(kind="string", value=value, limit=1)
            assert result["total"] == 0
        unsupported = await client.call_tool(
            "asc_find_refs",
            {
                "apk_path": apk,
                "backend": "rust_asc",
                "kind": "extends",
                "value": "java.lang.Object",
            },
        )
        assert unsupported.is_error
        denied = await client.call_tool(
            "asc_list_classes",
            {
                "apk_path": str(tmp_path / "outside.apk"),
                "backend": "rust_asc",
            },
        )
        assert denied.is_error
        assert hashlib.sha256(Path(apk).read_bytes()).hexdigest() == before_hash
        assert (await call("asc_list_classes", limit=1))["total"] == classes["total"]


async def assert_reference_stability(refs_call, source_call):
    probe = "Lorg/example/droidascfixture/Probe;"
    activity = "Lorg/example/droidascfixture/MainActivity;"
    # Ground truth comes from fixture Java, independently of the ASC CLI baseline.
    queries = [
        ("string", "ASC_FIXTURE_MARKER_v1", {probe + "->marker"}),
        ("type", "org.example.droidascfixture.Probe", {activity + "->onCreate"}),
        ("method", "marker", {probe + "->describe"}),
        ("field", "visits", {probe + "-><init>", probe + "->marker"}),
    ]
    before = []
    for kind, value, expected in queries:
        filters = {"class_name": probe} if kind in {"method", "field"} else {}
        result = await refs_call(kind=kind, value=value, threads=1, limit=100, **filters)
        assert result.get("status", "ok") == "ok", result
        assert not result["truncated"]
        assert {item["method"] for item in result["items"]} == expected
        assert all(item["dex"] == "classes2.dex" for item in result["items"])
        before.append(result)
    for name in (probe, activity):
        source = await source_call(class_name=name, threads=1, limit=1000)
        assert source.get("status", "ok") == "ok", source
        assert source["source"]
    for (kind, value, _), previous in zip(queries, before, strict=True):
        # A different thread count has a distinct APK snapshot key, forcing fresh analysis.
        filters = {"class_name": probe} if kind in {"method", "field"} else {}
        after = await refs_call(kind=kind, value=value, threads=2, limit=100, **filters)
        assert after == previous, (kind, previous, after)


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_real_exact_methods(transport, tmp_path, real_dex_files, request, monkeypatch):
    if not os.getenv("DROIDASC_MCP_JADX_HOME"):
        pytest.skip("Configure JADX 1.5.5 and JDK 17 for exact method acceptance")
    monkeypatch.setenv("ASC_TEST_ROOT", str(tmp_path))
    env = {**os.environ, "DROIDASC_MCP_ALLOWED_ROOTS": str(tmp_path)}
    endpoint = (
        request.getfixturevalue("http_endpoint")
        if transport == "http"
        else StdioServerParameters(command=sys.executable, args=["-m", "droidasc_mcp"], env=env)
    )
    owner = "Lorg/example/droidascfixture/MethodCases;"
    async with Client(endpoint) as client:

        async def call(tool, **args):
            reply = await client.call_tool(tool, args)
            assert not reply.is_error, reply
            return reply.structured_content

        opened = await call("asc_open_dex_session", dex_paths=[str(p) for p in real_dex_files])
        key = opened["session_id"]

        async def query(operation="get_method_source", **args):
            return await call("asc_query_dex_session", session_id=key, operation=operation, **args)

        listed = await query("list_methods", class_name=owner, limit=100)
        assert listed["status"] == "ok", listed
        assert listed["backend_version"] == "1.5.5"
        assert listed["dex_entry"] == "classes2.dex"
        methods = {item["descriptor"]: item for item in listed["items"]}
        expected = {
            "<init>()V",
            "choose(I)Ljava/lang/String;",
            "choose(Ljava/lang/String;)Ljava/lang/String;",
            "value()Ljava/lang/String;",
            "value()Ljava/lang/Object;",
            "arrays([[Ljava/lang/String;J)[I",
            "caf\u00e9()Ljava/lang/String;",
            "nativeCase()V",
        }
        assert set(methods) == {owner + "->" + item for item in expected}
        assert methods[owner + "->value()Ljava/lang/Object;"]["access_flags"] & 0x1040 == 0x1040
        assert methods[owner + "->nativeCase()V"]["has_code"] is False
        paged = await query("list_methods", class_name=owner, offset=1, limit=2)
        assert paged["items"] == listed["items"][1:3]
        assert paged["has_more"] is True

        for signature, marker, absent in [
            ("choose(I)Ljava/lang/String;", "INTEGER_OVERLOAD", "STRING_OVERLOAD"),
            ("choose(Ljava/lang/String;)Ljava/lang/String;", "STRING_OVERLOAD", "INTEGER_OVERLOAD"),
        ]:
            for mode in ("auto", "smali"):
                result = await query(method_descriptor=owner + "->" + signature, source_format=mode)
                assert result["status"] == "ok", result
                assert result["method_descriptor"] == owner + "->" + signature
                assert marker in result["source"] and absent not in result["source"]
                assert result["format"] == ("java" if mode == "auto" else "smali")
                assert result["fell_back"] is False
                assert result["input_id"] == opened["input_id"]
        # Empty default constructors are omitted from Java, never replaced by a different method.
        fallback = await query(method_descriptor=owner + "-><init>()V")
        assert fallback["format"] == "smali" and fallback["fell_back"] is True, fallback
        assert fallback["fallback_reason"] == "java_method_not_emitted"
        assert ".method public constructor <init>()V" in fallback["source"]
        strict = await query(method_descriptor=owner + "-><init>()V", source_format="java")
        assert strict["code"] == "java_unavailable"
        for signature in ("choose()V", "value()I"):
            missing = await query(method_descriptor=owner + "->" + signature)
            assert missing["code"] == "method_not_found" and "source" not in missing
        native = await query(method_descriptor=owner + "->nativeCase()V", source_format="smali")
        assert "native nativeCase()V" in native["source"]
        unicode_method = await query(method_descriptor=owner + "->caf\u00e9()Ljava/lang/String;")
        assert "UNICODE_METHOD" in unicode_method["source"]
        bridge = await query(
            method_descriptor=owner + "->value()Ljava/lang/Object;", source_format="smali"
        )
        assert "bridge synthetic value()Ljava/lang/Object;" in bridge["source"]
        once = await call(
            "asc_analyze_dex",
            dex_paths=[str(p) for p in real_dex_files],
            operation="list_methods",
            class_name=owner,
            limit=100,
        )
        assert {k: v for k, v in listed.items() if k != "session_id"} == once
        cancel = anyio.CancelScope()

        async def pending_query():
            with cancel:
                await query(method_descriptor=owner + "->choose(I)Ljava/lang/String;")

        java_pid = None
        java_temporary = None
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(pending_query)
            deadline = time.monotonic() + 15
            while java_pid is None and time.monotonic() < deadline:
                for child in psutil.Process().children(recursive=True):
                    with suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                        java_args = child.cmdline()
                        if any(arg.endswith("MethodBridge.java") for arg in java_args):
                            java_pid = child.pid
                            java_temporary = Path(
                                next(
                                    arg.split("=", 1)[1]
                                    for arg in java_args
                                    if arg.startswith("-Djava.io.tmpdir=")
                                )
                            )
                            (java_temporary / "cleanup-sentinel").write_text("temporary")
                            break
                await anyio.sleep(0.01)
            assert java_pid is not None, "Method JVM did not start"
            cancel.cancel()
        deadline = time.monotonic() + 3
        while (alive(java_pid) or java_temporary.exists()) and time.monotonic() < deadline:
            await anyio.sleep(0.01)
        assert not alive(java_pid), "Cancelled method JVM is still executing"
        assert not java_temporary.exists(), "Cancelled method temporary files remain"
        assert (await query("info"))["input_id"] == opened["input_id"]
        assert (await call("asc_close_dex_session", session_id=key))["cleanup_pending"] is False


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_real_dex_sessions(transport, tmp_path, real_dex_files, request, monkeypatch):
    monkeypatch.setenv("ASC_TEST_ROOT", str(tmp_path))
    env = {**os.environ, "DROIDASC_MCP_ALLOWED_ROOTS": str(tmp_path)}
    endpoint = (
        request.getfixturevalue("http_endpoint")
        if transport == "http"
        else StdioServerParameters(command=sys.executable, args=["-m", "droidasc_mcp"], env=env)
    )
    async with Client(endpoint) as client:

        async def call(tool, **args):
            reply = await client.call_tool(tool, args)
            assert not reply.is_error, reply
            return reply.structured_content

        opened = await call("asc_open_dex_session", dex_paths=[str(p) for p in real_dex_files])
        assert opened["status"] == "ok", opened
        key = opened["session_id"]
        assert len(opened["input_id"]) == 64
        assert opened["reuse"] == "validated_dex_bundle"

        async def query(**args):
            return await call("asc_query_dex_session", session_id=key, **args)

        classes = await query(operation="list_classes")
        assert classes["class_count"] == opened["class_count"]
        assert {item["dex_entry"] for item in classes["items"]} == {"classes.dex", "classes2.dex"}
        refs = await query(
            operation="find_refs",
            kind="method",
            value="marker",
            class_name="org.example.droidascfixture.Probe",
        )
        assert {item["method"] for item in refs["items"]} == {
            "Lorg/example/droidascfixture/Probe;->describe"
        }
        source = await query(
            operation="get_class_source", class_name="org.example.droidascfixture.Probe"
        )
        assert "ASC_FIXTURE_MARKER_v1" in source["source"]
        hierarchy = await query(operation="find_refs", kind="extends", value="Login")
        assert {item["class_name"] for item in hierarchy["items"]} == {"LLoginChild;"}
        assert (await query(operation="get_manifest"))["code"] == "no_manifest"
        cold, warm = [], []
        for _ in range(3):
            start = time.monotonic()
            once = await call(
                "asc_analyze_dex",
                dex_paths=[str(p) for p in real_dex_files],
                operation="list_classes",
            )
            cold.append(time.monotonic() - start)
            start = time.monotonic()
            reused = await query(operation="list_classes")
            warm.append(time.monotonic() - start)
            assert {k: v for k, v in reused.items() if k != "session_id"} == once
        # Replacing the source must not change an already-open evidence identity.
        real_dex_files[1].write_bytes(real_dex_files[0].read_bytes())
        other = await call("asc_open_dex_session", dex_paths=[str(real_dex_files[1])])
        assert other["input_id"] != opened["input_id"]
        results = {}

        async def read(label, session_id):
            results[label] = await call(
                "asc_query_dex_session", session_id=session_id, operation="list_classes"
            )

        async with anyio.create_task_group() as tasks:
            tasks.start_soon(read, "original", key)
            tasks.start_soon(read, "replacement", other["session_id"])
        assert results["original"] == classes
        assert results["replacement"]["class_count"] == opened["sources"][0]["class_count"]
        real_dex_files[0].unlink()
        assert (await query())["input_id"] == opened["input_id"]
        assert (await call("asc_close_dex_session", session_id=key))["cleanup_pending"] is False
        assert (await query())["code"] == "session_not_found"
        assert (await call("asc_query_dex_session", session_id=other["session_id"]))[
            "status"
        ] == "ok"
        await call("asc_close_dex_session", session_id=other["session_id"])
        print(f"dex_session transport={transport} cold_seconds={cold} warm_seconds={warm}")


async def assert_fixture_hierarchy(call, apk):
    for kind, value, expected in (
        ("extends", "HierarchyBase", {"LHierarchyChild;"}),
        ("extends", "Login", {"LLoginChild;"}),
        ("extends", "LLogin;", {"LLoginChild;"}),
        ("extends", "android.app.Activity", {"Lorg/example/droidascfixture/MainActivity;"}),
        ("impl", "InterfaceBase", {"LInterfaceChild;", "LHierarchyDirect;"}),
        ("impl", "InterfaceChild", {"LHierarchyBase;"}),
        ("extends", "MissingBase", set()),
        ("impl", "--output=sentinel.txt", set()),
    ):
        result = await call(kind=kind, value=value, limit=100)
        assert result.get("status", "ok") == "ok", result
        assert result["relation_scope"] == "direct"
        assert result["total"] == len(expected), (kind, value, result)
        assert {item["class_name"] for item in result["items"]} == expected
        # Query the CLI with a descriptor: its bare Login normalization loses the leading L.
        descriptor = (
            value
            if value.startswith("L") and value.endswith(";")
            else ("L" + value.replace(".", "/") + ";")
        )
        baseline = subprocess.run(
            [sys.executable, "-m", "droidasc", "findrefs", apk, kind, "--", descriptor],
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        assert [item["raw"] for item in result["items"]] == sorted(baseline.stdout.splitlines())
        pages = []
        for offset in range(result["total"]):
            page = await call(kind=kind, value=value, limit=1, offset=offset)
            pages.extend(page["items"])
        assert pages == result["items"]


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
    assert set(classes["items"]) == {
        probe,
        activity,
        "Lorg/example/droidascfixture/R;",
        "Lorg/example/droidascfixture/MethodCases;",
        "Lorg/example/droidascfixture/GenericValue;",
    }
    assert classes["total"] == 5
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


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_real_dex_operations(transport, tmp_path, real_dex_files, request):
    env = {**os.environ, "DROIDASC_MCP_ALLOWED_ROOTS": str(tmp_path)}
    endpoint = (
        request.getfixturevalue("http_endpoint")
        if transport == "http"
        else StdioServerParameters(command=sys.executable, args=["-m", "droidasc_mcp"], env=env)
    )
    paths = [str(path) for path in real_dex_files]
    hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in real_dex_files]
    probe = "Lorg/example/droidascfixture/Probe;"
    marker = "ASC_FIXTURE_MARKER_v1"
    async with Client(endpoint) as client:

        async def call(operation="info", **kwargs):
            reply = await client.call_tool(
                "asc_analyze_dex", {"dex_paths": paths, "operation": operation, **kwargs}
            )
            assert not reply.is_error, reply
            return reply.structured_content

        async def refs_call(**kwargs):
            return await call("find_refs", **kwargs)

        async def source_call(**kwargs):
            return await call("get_class_source", **kwargs)

        await assert_reference_stability(refs_call, source_call)
        info = await call()
        assert info["status"] == "ok"
        assert info["coverage"] == "supplied_files_only"
        assert info["runtime_completeness"] == "unknown"
        assert [s["sha256"] for s in info["sources"]] == hashes
        assert [s["path"] for s in info["sources"]] == paths
        assert (await call("get_manifest"))["status"] == "not_applicable"
        classes = await call("list_classes")
        assert classes["status"] == "ok"
        assert classes["total"] == info["class_count"]
        assert any(
            item == {"class_name": probe, "dex_entry": "classes2.dex"} for item in classes["items"]
        )
        combined = []
        for offset in range(classes["total"]):
            page = await call("list_classes", offset=offset, limit=1)
            combined.extend(page["items"])
            assert page["next_offset"] == (offset + 1 if offset + 1 < classes["total"] else None)
        assert combined == classes["items"]
        source = await call(
            "get_class_source", class_name="org.example.droidascfixture.Probe", limit=1000
        )
        assert source["status"] == "ok"
        assert source["dex_entry"] == "classes2.dex"
        assert marker in source["source"]
        assert (await call("get_class_source", class_name="missing.Class"))[
            "code"
        ] == "class_not_found"

        async def hierarchy_call(**kwargs):
            return await call("find_refs", **kwargs)

        await assert_fixture_hierarchy(hierarchy_call, os.environ["ASC_TEST_APK"])
        for kind, value in (
            ("string", marker),
            ("type", "org.example.droidascfixture.Probe"),
            ("method", "marker"),
            ("field", "visits"),
        ):
            result = await call("find_refs", kind=kind, value=value)
            assert result["status"] == "ok", result
            assert result["total"] > 0
            assert all(
                item.get("dex") in {"classes.dex", "classes2.dex"} for item in result["items"]
            )
            baseline = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "droidasc",
                    "findrefs",
                    os.environ["ASC_TEST_APK"],
                    kind,
                    "--",
                    value,
                ],
                capture_output=True,
                check=True,
                text=True,
                encoding="utf-8",
                timeout=60,
            )
            assert [item["raw"] for item in result["items"]] == sorted(baseline.stdout.splitlines())
        empty = await call("find_refs", value="NONEXISTENT_SENTINEL_8394582")
        assert empty["status"] == "ok" and empty["total"] == 0
        invalid = await call("find_refs", value="[")
        assert invalid["status"] == "error" and invalid["code"] == "engine_error"
        assert (await call("find_refs", value="--gui"))["code"] == "invalid_query"
        sentinel = tmp_path / "sentinel.txt"
        sentinel.write_text("preserve", encoding="utf-8")
        flagged = await call("find_refs", value="--output=" + sentinel.as_posix())
        assert flagged["status"] == "ok"
        assert sentinel.read_text(encoding="utf-8") == "preserve"
        assert (await call("list_classes", offset=-1))["code"] == "invalid_query"
        assert (await call())["status"] == "ok"
    assert [hashlib.sha256(path.read_bytes()).hexdigest() for path in real_dex_files] == hashes


@pytest.mark.parametrize("kind", ["string", "type"])
@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("[", "unterminated character set"),
        (r"--output=C:\Users\runner\sentinel.txt", r"bad escape \U"),
    ],
)
def test_real_invalid_regex_reports_engine_error(settings, kind, value, message):
    apk = os.getenv("ASC_TEST_APK")
    if not apk:
        pytest.skip("Set ASC_TEST_APK for real APK acceptance")
    runner = DroidAscRunner(settings)
    with pytest.raises(DroidAscError) as error:
        runner.find_refs(
            Path(apk),
            kind=kind,
            value=value,
            class_name=None,
            fuzzy_class=False,
            threads=8,
            offset=0,
            limit=100,
        )
    assert message in str(error.value)


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_persistent_index_transport(
    transport, tmp_path, smali_dex_files, request, monkeypatch
):
    paths = [str(shutil.copy(p, tmp_path)) for p in smali_dex_files]
    hashes = [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths]
    monkeypatch.setenv("ASC_TEST_ROOT", str(tmp_path))
    endpoint = (
        request.getfixturevalue("http_endpoint")
        if transport == "http"
        else StdioServerParameters(
            command=sys.executable,
            args=["-m", "droidasc_mcp"],
            env={**os.environ, "DROIDASC_MCP_ALLOWED_ROOTS": str(tmp_path)},
        )
    )
    async with Client(endpoint) as client:
        assert {p.name for p in (await client.list_prompts()).prompts} == {
            "triage_apk",
            "trace_exact_method",
        }
        assert (
            "16-bit code units"
            in (await client.read_resource("droidasc://analysis-guide")).contents[0].text
        )
        prompt = await client.get_prompt("triage_apk", {"apk_path": paths[0]})
        assert "not instructions" in prompt.messages[0].content.text
        opened = await client.call_tool("asc_open_dex_session", {"dex_paths": paths})
        key = opened.structured_content["session_id"]

        async def query(operation, **args):
            response = await client.call_tool(
                "asc_query_dex_session",
                {
                    "session_id": key,
                    "operation": operation,
                    **args,
                },
            )
            assert not response.is_error, response
            result = response.structured_content
            assert result["status"] == "ok", result
            return result

        early = await query("search_members", kind="method", value="->pick(", limit=1)
        assert early["backend"] == "dexlib2-discovery" and "index" not in early
        assert early["total"] == 2 and early["next_offset"] == 1
        warm = await query("search_members", kind="method", value="->pick(", limit=1)
        assert warm["query_cache"]["hit"] and warm["items"] == early["items"]
        strings = await query("search_strings", value="Caller.java")
        assert strings["total"] == 1 and not strings["instruction_scan_complete"]

        cancel = anyio.CancelScope()

        async def pending_index():
            with cancel:
                await query("build_xref_index")

        java_pid = None
        java_temporary = None
        async with anyio.create_task_group() as tasks:
            tasks.start_soon(pending_index)
            deadline = time.monotonic() + 15
            while java_pid is None and time.monotonic() < deadline:
                for child in psutil.Process().children(recursive=True):
                    with suppress(psutil.NoSuchProcess, psutil.AccessDenied):
                        args = child.cmdline()
                        if any(arg.endswith("IndexBridge.java") for arg in args):
                            java_pid = child.pid
                            java_temporary = Path(
                                next(
                                    arg.split("=", 1)[1]
                                    for arg in args
                                    if arg.startswith("-Djava.io.tmpdir=")
                                )
                            )
                            (java_temporary / "cleanup-sentinel").write_text("temporary")
                            break
                await anyio.sleep(0.01)
            assert java_pid is not None, "Index JVM did not start"
            cancel.cancel()
        deadline = time.monotonic() + 3
        while (alive(java_pid) or java_temporary.exists()) and time.monotonic() < deadline:
            await anyio.sleep(0.01)
        assert not alive(java_pid), "Cancelled index JVM is still executing"
        assert not java_temporary.exists(), "Cancelled index temporary files remain"

        annotation = await query(
            "find_type_refs",
            type_descriptor="Lfixture/Target;",
            type_relation="annotation",
            limit=2,
        )
        assert annotation["total"] == 5 and annotation["has_more"]
        assert annotation["index"]["reused"] is False
        assert (await query("build_xref_index"))["index"]["reused"] is True
        discovered = await query("search_members", kind="method", value="->pick(", limit=1)
        assert discovered["total"] == 2 and discovered["next_offset"] == 1
        assert (
            await query("find_method_refs", method_descriptor=discovered["items"][0]["descriptor"])
        )["total"] == 1
        more = await query(
            "find_type_refs",
            type_descriptor="Lfixture/Target;",
            type_relation="annotation",
            offset=2,
            limit=10,
        )
        assert len(more["items"]) == 3 and not more["has_more"]
        refs = await query("find_field_refs", field_descriptor="Lfixture/Target;->value:I")
        assert refs["total"] == 2 and refs["index"]["reused"] is True
        invalid = await client.call_tool(
            "asc_query_dex_session",
            {
                "session_id": key,
                "operation": "find_type_refs",
                "type_descriptor": "fixture.Target",
            },
        )
        assert invalid.is_error
        assert (await query("get_method_calls", method_descriptor="Lfixture/Caller;->run()V"))[
            "total"
        ] == 3
        await client.call_tool("asc_close_dex_session", {"session_id": key})
        closed = await client.call_tool("asc_query_dex_session", {"session_id": key})
        assert closed.structured_content["code"] == "session_not_found"
    assert [hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths] == hashes


async def assert_fixture_query_boundaries(client, apk, tmp_path):
    sentinel = tmp_path / "outside-root-sentinel.txt"
    original = "READ_ONLY_SENTINEL\n"
    sentinel.write_text(original, encoding="utf-8")
    assert not sentinel.resolve().is_relative_to(Path(apk).parent)
    # Forward slashes remain a valid Windows output path without regex escapes.
    output_path = sentinel.as_posix()
    for kind in ("string", "type", "method", "field"):
        for value in ("--help", "--output=" + output_path, "-o" + output_path, "--"):
            args = {"apk_path": apk, "kind": kind, "value": value}
            if kind in {"method", "field"}:
                args["class_name"] = "org.example.droidascfixture.Probe"
            result = await client.call_tool("asc_find_refs", args)
            assert sentinel.read_text(encoding="utf-8") == original
            assert not result.is_error, result
            assert result.structured_content["total"] == 0, result
        if kind in {"string", "type"}:
            for value in ("[", r"--output=C:\Users\runner\sentinel.txt"):
                invalid = await client.call_tool(
                    "asc_find_refs", {"apk_path": apk, "kind": kind, "value": value}
                )
                assert invalid.is_error, invalid
                assert sentinel.read_text(encoding="utf-8") == original
                assert not (await client.call_tool("asc_ping", {})).is_error
        reserved = await client.call_tool(
            "asc_find_refs", {"apk_path": apk, "kind": kind, "value": "--gui"}
        )
        assert reserved.is_error

    for prefix in ("--help", "--gui", "--output=" + output_path):
        result = await client.call_tool("asc_list_classes", {"apk_path": apk, "prefix": prefix})
        assert not result.is_error, result
        assert result.structured_content["items"] == []
        assert sentinel.read_text(encoding="utf-8") == original

    for kind, value in (("method", "marker"), ("field", "visits")):
        args = {"apk_path": apk, "kind": kind, "value": value}
        descriptor = await client.call_tool("asc_find_refs", {**args, "class_name": "LLogin;"})
        assert not descriptor.is_error, descriptor
        assert descriptor.structured_content["total"] > 0
        for name, fuzzy in (("Login", False), ("Log", True)):
            result = await client.call_tool(
                "asc_find_refs", {**args, "class_name": name, "fuzzy_class": fuzzy}
            )
            assert not result.is_error, result
            assert result.structured_content["items"] == descriptor.structured_content["items"]
    assert not (await client.call_tool("asc_ping", {})).is_error
