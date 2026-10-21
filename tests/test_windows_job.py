"""Portable lifecycle/fault tests; native Job Object behavior is tested in integration."""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from droidasc_mcp import windows_job, worker_bootstrap


def test_pipe_reader_short_data_eof_and_cancellation(monkeypatch):
    if os.name == "nt":
        # Native read must be interruptible even while a writer still owns its handle.
        read_fd, write_fd = os.pipe()
        stop = threading.Event()
        with os.fdopen(read_fd, "rb") as pipe, os.fdopen(write_fd, "wb") as writer:
            writer.write(b"abc")
            writer.flush()
            assert windows_job.read_pipe(pipe, stop) == b"abc"
            results = []
            reader = threading.Thread(
                target=lambda: results.append(windows_job.read_pipe(pipe, stop))
            )
            reader.start()
            stop.set()
            reader.join(timeout=1)
            assert not reader.is_alive()
            assert results == [b""]

    stopped = threading.Event()
    state = [3]

    class PipeError(Exception):
        winerror = 109

    def peek(handle, size):
        assert handle == 42
        if state[0] == -1:
            raise PipeError("broken pipe")
        return b"", state[0], 0

    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(get_osfhandle=lambda fd: fd))
    monkeypatch.setitem(
        sys.modules, "win32pipe", SimpleNamespace(PeekNamedPipe=peek, error=PipeError)
    )
    stream = SimpleNamespace(fileno=lambda: 42, read1=lambda size: b"abc"[:size])
    assert windows_job.read_pipe(stream, stopped) == b"abc"
    state[0] = -1
    assert windows_job.read_pipe(stream, stopped) == b""
    state[0] = 0
    results = []
    reader = threading.Thread(target=lambda: results.append(windows_job.read_pipe(stream, stopped)))
    reader.start()
    stopped.set()
    reader.join(timeout=1)
    assert not reader.is_alive()
    assert results == [b""]


@pytest.fixture
def fake_win32(monkeypatch):
    events = []

    class Handle:
        def __init__(self, name):
            self.name = name

        def Close(self):
            events.append(self.name + ".close")

    api = SimpleNamespace(OpenProcess=lambda access, inherit, pid: Handle("process"))

    def create_job(security, name):
        assert security is None
        assert name == ""  # pywin32 requires a Unicode name, not None.
        return Handle("job")

    jobs = SimpleNamespace(
        CreateJobObject=create_job,
        QueryInformationJobObject=lambda *a: {"BasicLimitInformation": {"LimitFlags": 0}},
        SetInformationJobObject=lambda handle, kind, info: events.append(info),
        AssignProcessToJobObject=lambda *a: events.append("assign"),
        JobObjectExtendedLimitInformation=9,
        JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE=0x2000,
        JOB_OBJECT_LIMIT_JOB_MEMORY=0x200,
    )
    monkeypatch.setitem(sys.modules, "win32api", api)
    monkeypatch.setitem(sys.modules, "win32job", jobs)
    monkeypatch.setitem(
        sys.modules,
        "win32con",
        SimpleNamespace(
            PROCESS_SET_QUOTA=0x100,
            PROCESS_TERMINATE=1,
        ),
    )
    return api, jobs, events


def test_job_limits_assignment_and_idempotent_close(fake_win32):
    _, _, events = fake_win32
    job = windows_job.WindowsJob()
    job.assign(12345)
    job.close()
    job.close()
    assert events == [
        {"BasicLimitInformation": {"LimitFlags": 0x2000}},
        "assign",
        "process.close",
        "job.close",
    ]


def test_job_applies_aggregate_memory_limit(fake_win32):
    _, _, events = fake_win32
    job = windows_job.WindowsJob(128 * 1024 * 1024)
    job.close()
    assert events[0] == {
        "BasicLimitInformation": {"LimitFlags": 0x2200},
        "JobMemoryLimit": 128 * 1024 * 1024,
    }
    assert events[1] == "job.close"


@pytest.mark.parametrize("stage", ["QueryInformationJobObject", "SetInformationJobObject"])
def test_job_configuration_failure_closes_handle(fake_win32, monkeypatch, stage):
    _, jobs, events = fake_win32

    def fail(*args):
        raise OSError("job configuration failed")

    monkeypatch.setattr(jobs, stage, fail)
    with pytest.raises(OSError, match="configuration"):
        windows_job.WindowsJob()
    assert events == ["job.close"]


@pytest.mark.parametrize("stage", ["OpenProcess", "AssignProcessToJobObject"])
def test_failed_assignment_does_not_start_work(fake_win32, monkeypatch, tmp_path, stage):
    api, jobs, events = fake_win32

    def fail(*args):
        raise OSError("job assignment failed")

    monkeypatch.setattr(api if stage == "OpenProcess" else jobs, stage, fail)
    popen = subprocess.Popen
    children = []

    def launch(*args, **kwargs):
        child = popen(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(windows_job.subprocess, "Popen", launch)
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parent)}
    with pytest.raises(OSError, match="assignment"):
        windows_job.start_process(
            [sys.executable, "-m", "process_fixture", "touch", str(tmp_path)], env
        )
    assert not (tmp_path / "touched").exists()
    assert events[-1] == "job.close"
    assert events.count("process.close") == (stage == "AssignProcessToJobObject")
    assert len(children) == 1
    assert children[0].poll() is not None
    assert all(s.closed for s in (children[0].stdin, children[0].stdout, children[0].stderr))


@pytest.mark.parametrize("gate", [b"", b"x", b"\x01"])
def test_bootstrap_waits_for_assignment_handshake(tmp_path, gate):
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(__file__).parent),
        "DROIDASC_MCP_START_GATE": "1",
    }
    with subprocess.Popen(
        [sys.executable, worker_bootstrap.__file__, "process_fixture", "touch", str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    ) as child:
        try:
            time.sleep(0.15)
            assert child.poll() is None
            assert not (tmp_path / "touched").exists()
            _, stderr = child.communicate(input=gate, timeout=5)
            assert (tmp_path / "touched").exists() == (gate == b"\x01")
            if gate == b"\x01":
                assert child.returncode == 0, stderr
            else:
                assert child.returncode != 0
                assert b"handshake failed" in stderr
        finally:
            if child.poll() is None:
                child.kill()
                child.wait(timeout=2)
