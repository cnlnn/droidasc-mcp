"""Deterministic regression gates for the 0.1.1 supervisor and cache fixes."""

import io
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
from functools import partial
from types import SimpleNamespace

import anyio
import pytest

from droidasc_mcp import runner as module
from droidasc_mcp.runner import DroidAscError, DroidAscRunner


def test_reader_construction_failure_releases_worker(settings, monkeypatch):
    events = []
    process = SimpleNamespace(
        stdout=io.BytesIO(),
        stderr=io.BytesIO(),
        wait=lambda **kw: 0,
    )
    job = SimpleNamespace(close=lambda: events.append("job.close"))
    monkeypatch.setattr(module, "_start_process", lambda *a: (process, job))

    def fail(*args, **kwargs):
        raise OSError("reader construction failed")

    monkeypatch.setattr(module.threading, "Thread", fail)
    with pytest.raises(OSError, match="construction"):
        DroidAscRunner(settings)._execute(["unused"])
    assert events == ["job.close"]
    assert process.stdout.closed and process.stderr.closed


def test_late_overflow_is_not_returned_as_success(settings, monkeypatch):
    tasks = []

    class ControlledThread:
        def __init__(self, target, args, **kwargs):
            tasks.append(lambda: target(*args))

        def start(self):
            pass

        def is_alive(self):
            return False

        def join(self, **kwargs):
            pass

    def poll():
        # Finish the readers after the supervisor's first exceeded.is_set().
        while tasks:
            tasks.pop(0)()
        return 0

    process = SimpleNamespace(
        stdout=io.BytesIO(b"x" * (settings.max_output_bytes + 1)),
        stderr=io.BytesIO(),
        poll=poll,
        returncode=0,
        wait=lambda **kw: 0,
    )
    monkeypatch.setattr(module.threading, "Thread", ControlledThread)
    monkeypatch.setattr(module, "_start_process", lambda *a: (process, None))
    monkeypatch.setattr(module, "_terminate_process_tree", lambda *a: None)
    with pytest.raises(DroidAscError, match="output exceeds"):
        DroidAscRunner(settings)._execute(["unused"])


def test_reader_failure_is_not_success(settings, monkeypatch):
    class BrokenStream(io.BytesIO):
        def read(self, *args):
            raise OSError("synthetic read failure")

    process = SimpleNamespace(
        stdout=BrokenStream(),
        stderr=io.BytesIO(),
        poll=lambda: 0,
        returncode=0,
        wait=lambda **kw: 0,
    )
    monkeypatch.setattr(module, "_start_process", lambda *a: (process, None))
    monkeypatch.setattr(module, "_terminate_process_tree", lambda *a: None)
    with pytest.raises(DroidAscError, match="read"):
        DroidAscRunner(settings)._execute(["unused"])


def test_distinct_queries_run_concurrently(settings, apk_file, monkeypatch):
    subject = DroidAscRunner(settings)
    rendezvous = threading.Barrier(2)

    def execute(args):
        rendezvous.wait(timeout=1)
        return b"ok\n"

    monkeypatch.setattr(subject, "_execute", execute)
    with ThreadPoolExecutor(2) as pool:
        futures = [
            pool.submit(subject._run_paged, [name, str(apk_file)], offset=0, limit=1)
            for name in ("getmanifest", "listclass")
        ]
        assert [f.result(timeout=3).items for f in futures] == [["ok"], ["ok"]]


def test_next_offset_uses_returned_count(settings, apk_file, monkeypatch):
    subject = DroidAscRunner(settings)
    monkeypatch.setattr(subject, "_execute", lambda args: (b"x" * 40000 + b"\n") * 3)
    first = subject.get_manifest(apk_file, offset=0, limit=3)
    assert len(first.items) < 3
    assert first.as_dict()["next_offset"] == len(first.items)
    last = subject.get_manifest(apk_file, offset=first.as_dict()["next_offset"], limit=3)
    assert last.as_dict()["next_offset"] is None


def test_same_query_shares_one_fill(settings, apk_file, monkeypatch):
    waiter = threading.Event()
    calls = []

    class ObservedFuture(Future):
        def result(self, *args, **kwargs):
            waiter.set()
            return super().result(*args, **kwargs)

    monkeypatch.setattr(module, "Future", ObservedFuture)
    subject = DroidAscRunner(settings)

    def execute(args):
        calls.append(args)
        assert waiter.wait(2)
        return b"same\n"

    monkeypatch.setattr(subject, "_execute", execute)
    with ThreadPoolExecutor(2) as pool:
        tasks = [pool.submit(subject.get_manifest, apk_file, offset=0, limit=1) for _ in range(2)]
        assert [f.result(3).items for f in tasks] == [["same"], ["same"]]
    assert len(calls) == 1
    assert not subject._inflight


@pytest.mark.anyio
async def test_cancelled_snapshot_leader_does_not_poison_waiter(settings, apk_file, monkeypatch):
    first_entered = threading.Event()
    waiter_entered = threading.Event()
    calls = 0

    class ObservedFuture(Future):
        def result(self, *args, **kwargs):
            waiter_entered.set()
            return super().result(*args, **kwargs)

    monkeypatch.setattr(module, "Future", ObservedFuture)
    subject = DroidAscRunner(settings)

    def execute(args):
        nonlocal calls
        calls += 1
        if calls == 1:
            first_entered.set()
            while True:
                module._check_cancelled()
                time.sleep(0.01)
        return b"recovered\n"

    monkeypatch.setattr(subject, "_execute", execute)
    leader_scope = anyio.CancelScope()
    result = []

    async def leader():
        with leader_scope:
            await anyio.to_thread.run_sync(
                partial(subject.get_manifest, apk_file, offset=0, limit=1)
            )

    async def waiter():
        page = await anyio.to_thread.run_sync(
            partial(subject.get_manifest, apk_file, offset=0, limit=1)
        )
        result.extend(page.items)

    async with anyio.create_task_group() as group:
        group.start_soon(leader)
        while not first_entered.wait(0.01):
            await anyio.sleep(0)
        group.start_soon(waiter)
        while not waiter_entered.wait(0.01):
            await anyio.sleep(0)
        leader_scope.cancel()

    assert result == ["recovered"]
    assert calls == 2
    assert not subject._inflight


def test_cache_hit_does_not_wait_for_other_fill(settings, apk_file, monkeypatch):
    subject = DroidAscRunner(settings)
    monkeypatch.setattr(subject, "_execute", lambda args: b"cached\n")
    subject.get_manifest(apk_file, offset=0, limit=1)
    entered, release = threading.Event(), threading.Event()

    def execute(args):
        entered.set()
        assert release.wait(3)
        return b"other\n"

    monkeypatch.setattr(subject, "_execute", execute)
    with ThreadPoolExecutor(2) as pool:
        miss = pool.submit(subject._run_paged, ["listclass", str(apk_file)], offset=0, limit=1)
        try:
            assert entered.wait(2)
            hit = pool.submit(subject.get_manifest, apk_file, offset=0, limit=1)
            assert hit.result(1).items == ["cached"]
        finally:
            release.set()
        assert miss.result(2).items == ["other"]


def test_snapshot_decoded_sorted_once(settings, apk_file, monkeypatch):
    subject = DroidAscRunner(settings)
    monkeypatch.setattr(subject, "_execute", lambda args: b"z\na\nm\n")
    args = ["findrefs", str(apk_file)]
    subject._run_paged(args, offset=0, limit=1)
    snapshot = next(iter(subject._cache.values()))
    assert snapshot.lines == ("a", "m", "z")
    monkeypatch.setattr(
        module.Snapshot, "build", lambda *a, **kw: pytest.fail("rebuilding snapshot")
    )
    assert subject._run_paged(args, offset=1, limit=1).items == ["m"]
    assert subject._get_snapshot(args) is snapshot


def test_decoded_memory_budget(settings, apk_file, monkeypatch):
    subject = DroidAscRunner(replace(settings, max_output_bytes=4096))
    # Wire bytes fit, but thousands of small Python strings must not bypass the cache budget.
    monkeypatch.setattr(subject, "_execute", lambda args: b"a\n" * 1000)
    with pytest.raises(DroidAscError, match="memory budget"):
        subject.get_manifest(apk_file, offset=0, limit=1)
    assert not subject._cache
    assert not subject._inflight
    monkeypatch.setattr(subject, "_execute", lambda args: b"ok\n")
    assert subject.get_manifest(apk_file, offset=0, limit=1).items == ["ok"]


def test_cache_accounts_for_decoded_objects(settings, apk_file, monkeypatch):
    subject = DroidAscRunner(replace(settings, max_output_bytes=4096))
    monkeypatch.setattr(subject, "_execute", lambda args: b"a\n" * 50)
    for index in range(3):
        subject._run_paged(["listclass", str(apk_file), str(index)], offset=0, limit=1)
    assert len(subject._cache) == 1
    assert sum(entry.size_bytes for entry in subject._cache.values()) <= 4096
