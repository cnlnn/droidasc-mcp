"""Pipelined ownership parity, bounded handoff and fail-closed publication."""

import json
import threading
import zipfile

import psutil
import pytest
from test_dex import empty_dex
from test_native_directory import class_dex

from droidasc_mcp import dex_worker
from droidasc_mcp.class_directory import ClassDirectory
from droidasc_mcp.runner import DroidAscRunner
from droidasc_mcp.worker_runtime import WorkerSettings


def assert_process_stopped(pid):
    try:
        process = psutil.Process(pid)
        assert not process.is_running() or process.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        pass


@pytest.mark.parametrize("stage", ["construct", "running", "status", "stopped", "zombie", "live"])
def test_process_exit_observer_races(monkeypatch, stage):
    from types import SimpleNamespace

    def check(current, value):
        if current == stage:
            raise psutil.NoSuchProcess(123)
        return value

    def process(pid):
        check("construct", None)
        return SimpleNamespace(
            is_running=lambda: check("running", stage != "stopped"),
            status=lambda: check(
                "status", psutil.STATUS_ZOMBIE if stage == "zombie" else psutil.STATUS_RUNNING
            ),
        )

    monkeypatch.setattr(psutil, "Process", process)
    if stage == "live":
        with pytest.raises(AssertionError):
            assert_process_stopped(123)
    else:
        assert_process_stopped(123)


def request_for(settings, tmp_path, groups):
    paths = []
    for index, names in enumerate(groups):
        path = tmp_path / f"input-{index}.dex"
        path.write_bytes(class_dex(names) if names else empty_dex())
        paths.append(path)
    request = DroidAscRunner(settings)._dex_request(paths, {"offset": 0, "limit": 100})
    request["prepare"] = True
    return request


@pytest.mark.parametrize("duplicate", [False, True])
@pytest.mark.parametrize("accelerator", [False, True])
def test_pipeline_matches_serial_directory_and_common_metadata(
    settings, tmp_path, monkeypatch, duplicate, accelerator
):
    from droidasc_mcp import preparation_directory

    original_names = preparation_directory.class_names
    monkeypatch.setattr(
        preparation_directory,
        "class_names",
        lambda *args: original_names(*args, accelerator=accelerator),
    )
    groups = [["La/A;", "La/\U0001f600;"], [], ["Lz/Z;", "Lz/\ud800;"]]
    if duplicate:
        groups[-1].append("La/A;")
    request = request_for(settings, tmp_path, groups)
    serial, pipeline = tmp_path / "serial", tmp_path / "pipeline"
    serial.mkdir()
    pipeline.mkdir()
    common = {"sources": []}
    worker_settings = WorkerSettings(request)
    dex_worker.prepare_bundle(worker_settings, request, serial, common)
    serial_result = dex_worker.build_class_directory(
        serial / "analysis.apk",
        {record["dex_entry"]: record for record in common["sources"]},
        serial,
        worker_settings,
        False,
    )
    result = dex_worker.analyze(request, pipeline)
    assert result["sources"] == common["sources"]
    if duplicate:
        assert result["code"] == "duplicate_class"
        assert result["duplicates"] == serial_result[1]
        assert not (pipeline / "prepared.json").exists()
    else:
        assert result["status"] == "ok", result
        assert result["class_count"] == serial_result[0]
    with (
        ClassDirectory(serial / "owners.sqlite") as first,
        ClassDirectory(pipeline / "owners.sqlite") as second,
    ):
        assert first.page(None, 0, 100) == second.page(None, 0, 100)
    assert not (pipeline / "owners.pending.sqlite").exists()


def test_insertion_overlaps_next_snapshot_without_retaining_mapping(
    settings, tmp_path, monkeypatch
):
    from droidasc_mcp import preparation_directory

    request = request_for(settings, tmp_path, [["La/A;"], ["Lb/B;"], ["Lc/C;"]])
    root = tmp_path / "prepared"
    root.mkdir()
    insertion, copied_second = threading.Event(), threading.Event()
    original_add, original_copy = ClassDirectory.add, dex_worker.copy_dex_stream
    names_thread = []
    original_names = preparation_directory.class_names

    def names(*args, **kwargs):
        names_thread.append(threading.get_ident())
        return original_names(*args, **kwargs)

    def add(self, names, entry):
        assert threading.get_ident() != names_thread[-1]
        if entry == "classes.dex":
            insertion.set()
            assert copied_second.wait(5), "The next snapshot must not await this insertion"
        return original_add(self, names, entry)

    def copy(*args, **kwargs):
        if args[4] == "classes2.dex":
            assert insertion.wait(5)
            record = original_copy(*args, **kwargs)
            copied_second.set()
            return record
        return original_copy(*args, **kwargs)

    monkeypatch.setattr(preparation_directory, "class_names", names)
    monkeypatch.setattr(ClassDirectory, "add", add)
    monkeypatch.setattr(dex_worker, "copy_dex_stream", copy)
    assert dex_worker.analyze(request, root)["status"] == "ok"
    assert copied_second.is_set()
    assert len(set(names_thread)) == 1
    assert not any(thread.name.startswith("droidasc-owners") for thread in threading.enumerate())
    # No live SQLite connection or mapped snapshot prevents immediate cleanup on Windows.
    (root / "owners.sqlite").unlink()
    (root / "analysis.apk").unlink()


@pytest.mark.parametrize("failure", ["insertion", "final_insertion", "late_input", "late_hash"])
def test_failed_pipeline_never_publishes_and_joins_writer(settings, tmp_path, monkeypatch, failure):
    from contextlib import contextmanager

    from droidasc_mcp import containers
    from droidasc_mcp.archive_errors import ArchiveError

    groups = [["La/A;"], ["Lb/B;"]]
    request = request_for(settings, tmp_path, groups)
    root = tmp_path / "prepared"
    root.mkdir()
    if failure in {"insertion", "final_insertion"}:
        original_add = ClassDirectory.add

        def broken(self, names, entry):
            if failure == "final_insertion" and entry != "classes2.dex":
                return original_add(self, names, entry)
            raise ArchiveError("metadata_limit", "Injected writer failure")

        monkeypatch.setattr(ClassDirectory, "add", broken)
    elif failure == "late_input":
        path = tmp_path / "input-1.dex"
        path.write_bytes(path.read_bytes()[:-1])
    else:
        artifact = tmp_path / "input.apk"
        with zipfile.ZipFile(artifact, "w") as archive:
            for index in range(2):
                archive.write(tmp_path / f"input-{index}.dex", f"classes{index}.dex")
        request.update(artifact_path=str(artifact), max_uncompressed_bytes=1024**2)
        original = containers.selected_dex

        @contextmanager
        def changed(*args):
            with original(*args) as selected:
                yield selected
                raise ArchiveError("input_changed", "Injected final source hash failure")

        monkeypatch.setattr(containers, "selected_dex", changed)
    result = dex_worker.analyze(request, root)
    assert result["status"] == "error", result
    assert not (root / "owners.sqlite").exists()
    assert not (root / "prepared.json").exists()
    progress = [json.loads(row) for row in (root / "progress.jsonl").read_text().splitlines()]
    assert all("ready" not in row["message"] for row in progress)
    assert not any(thread.name.startswith("droidasc-owners") for thread in threading.enumerate())
    (root / "owners.pending.sqlite").unlink()
    (root / "analysis.apk").unlink()


def test_directory_open_failure_joins_executor(tmp_path):
    from droidasc_mcp.preparation_directory import PreparationDirectory

    with (
        pytest.raises(ValueError, match="metadata exceeds budget"),
        PreparationDirectory(tmp_path, 1),
    ):
        pytest.fail("An invalid directory budget cannot be opened")
    assert not any(thread.name.startswith("droidasc-owners") for thread in threading.enumerate())


@pytest.mark.parametrize("accelerator", [False, True])
def test_closed_member_can_be_scanned_before_zip_close_and_then_appended(tmp_path, accelerator):
    from droidasc_mcp.native_directory import class_names

    bundle = tmp_path / "growing.apk"
    names = ["La/A;", "La/\U0001f600;"]
    with zipfile.ZipFile(bundle, "w") as archive:
        archive.writestr("classes.dex", class_dex(names))
        archive.fp.flush()
        assert class_names(bundle, archive.getinfo("classes.dex"), accelerator=accelerator) == names
        archive.writestr("classes2.dex", class_dex(["Lb/B;"]))
    with zipfile.ZipFile(bundle) as archive:
        assert class_names(bundle, archive.getinfo("classes.dex"), accelerator=accelerator) == names
        assert class_names(bundle, archive.getinfo("classes2.dex"), accelerator=accelerator) == [
            "Lb/B;"
        ]
    bundle.unlink()


@pytest.mark.parametrize("damage", [None, "missing", "owner", "dictionary", "snapshot"])
def test_full_original_archive_oracle_detects_ownership_and_byte_mismatch(
    settings, tmp_path, monkeypatch, damage
):
    import sqlite3
    from contextlib import closing
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from verify_preparation_directory import verify_ownership

    artifact = tmp_path / "original.apk"
    with zipfile.ZipFile(artifact, "w") as archive:
        archive.writestr("classes.dex", class_dex(["La/A;", "La/\U0001f600;"]))
        archive.writestr("classes2.dex", class_dex(["Lb/B;"]))
    request = DroidAscRunner(settings)._dex_request([], {"offset": 0, "limit": 100})
    request.update(artifact_path=str(artifact), max_uncompressed_bytes=1024**2, prepare=True)
    root = tmp_path / "prepared"
    root.mkdir()
    prepared = dex_worker.analyze(request, root)
    assert prepared["status"] == "ok", prepared
    if damage in {"missing", "owner", "dictionary"}:
        with closing(sqlite3.connect(root / "owners.sqlite")) as db:
            if damage == "missing":
                db.execute(
                    "DELETE FROM classes WHERE entry=(SELECT id FROM entries "
                    "WHERE name='classes2.dex')"
                )
            elif damage == "dictionary":
                db.execute("UPDATE entries SET name='wrong.dex' WHERE name='classes2.dex'")
            else:
                db.execute("UPDATE classes SET entry='wrong.dex'")
            db.commit()
    elif damage == "snapshot":
        with (root / "analysis.apk").open("r+b") as stream:
            stream.seek(30 + len("classes.dex") + 112)
            original = stream.read(1)
            stream.seek(-1, 1)
            stream.write(bytes([original[0] ^ 1]))
    if damage:
        with pytest.raises((AssertionError, zipfile.BadZipFile)):
            verify_ownership(artifact, root, prepared)
    else:
        verified = verify_ownership(artifact, root, prepared)
        assert verified["exact_classes_and_owners"] == 3
        assert verified["snapshot_bytes_match_original"]


@pytest.mark.anyio
@pytest.mark.parametrize("cancel", [False, True])
async def test_live_owner_writer_termination_cleans_pending_storage_and_recovers(
    settings, tmp_path, monkeypatch, cancel
):
    import os
    import time
    from dataclasses import replace
    from pathlib import Path

    import anyio

    from droidasc_mcp.worker_errors import DroidAscError

    path = tmp_path / "input.dex"
    path.write_bytes(class_dex(["La/A;"]))
    marker = tmp_path / "owner-writer.json"
    runner = DroidAscRunner(replace(settings, timeout_seconds=20 if cancel else 3))
    command = runner._command
    monkeypatch.setenv(
        "PYTHONPATH",
        os.pathsep.join([str(Path(__file__).parent), os.environ.get("PYTHONPATH", "")]),
    )

    def slow_command(args, module_name):
        assert module_name == "droidasc_mcp.dex_worker"
        return command([*args, str(marker)], "preparation_worker")

    monkeypatch.setattr(runner, "_command", slow_command)
    scope = anyio.CancelScope()

    async def pending():
        if cancel:
            with scope:
                await anyio.to_thread.run_sync(
                    runner.analyze_dex, [path], {"operation": "info", "offset": 0, "limit": 1}
                )
        else:
            with pytest.raises(DroidAscError, match="timed out"):
                await anyio.to_thread.run_sync(
                    runner.analyze_dex, [path], {"operation": "info", "offset": 0, "limit": 1}
                )

    async with anyio.create_task_group() as tasks:
        tasks.start_soon(pending)
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            await anyio.sleep(0.01)
        assert marker.exists(), "Real SQLite owner thread did not start"
        # The marker may become visible before its single small write completes.
        while True:
            try:
                state = json.loads(marker.read_text())
                break
            except ValueError:
                assert time.monotonic() < deadline
                await anyio.sleep(0.01)
        root = Path(state["root"])
        assert (root / "owners.pending.sqlite").is_file()
        assert not (root / "owners.sqlite").exists()
        assert not (root / "prepared.json").exists()
        if cancel:
            scope.cancel()
    deadline = time.monotonic() + 3
    while root.exists() and time.monotonic() < deadline:
        await anyio.sleep(0.01)
    assert not root.exists(), "Killed owner writer left pending session storage"
    assert_process_stopped(state["pid"])
    monkeypatch.setattr(runner, "_command", command)
    recovered = runner.analyze_dex([path], {"operation": "info", "offset": 0, "limit": 1})
    assert recovered["status"] == "ok" and recovered["class_count"] == 1
