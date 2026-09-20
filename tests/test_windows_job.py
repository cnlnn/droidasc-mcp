"""Portable lifecycle/fault tests; native Job Object behavior is tested in integration."""

import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from droidasc_mcp import windows_job, worker_bootstrap


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
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parent)}
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
