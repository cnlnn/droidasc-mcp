"""Persistent copies must remain bounded, intact and independent of session storage."""

import json
import multiprocessing
import os
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.durable_index import DurableIndexes
from droidasc_mcp.runner import DroidAscError


@pytest.fixture
def cache(tmp_path):
    return DurableIndexes(
        Settings(
            allowed_roots=(tmp_path,),
            xref_cache_dir=tmp_path / "cache",
            max_xref_cache_bytes=12000,
            max_xref_index_bytes=8000,
        )
    )


def put(cache, tmp_path, key, content=b"sample" * 1000):
    source = tmp_path / (key + ".sqlite")
    source.write_bytes(content)
    identity = {"input_id": key, "schema": "3", "backend_id": "test"}
    return identity, cache.publish(identity, source)


def test_restore_hash_identity_quota_and_eviction(cache, tmp_path):
    identity, status = put(cache, tmp_path, "one")
    assert status == "stored"
    target = tmp_path / "restored.sqlite"
    assert cache.restore(identity, target, tmp_path)
    assert target.read_bytes() == b"sample" * 1000
    target.unlink()
    assert not cache.restore({**identity, "backend_id": "changed"}, target, tmp_path)
    assert not target.exists()
    directory = cache.root / cache._key(identity)
    (directory / "index.sqlite").write_bytes(b"tamper" * 1000)
    assert not cache.restore(identity, target, tmp_path)
    assert not directory.exists() and not target.exists()
    put(cache, tmp_path, "one")
    second, _ = put(cache, tmp_path, "two")
    assert not cache.restore(identity, target, tmp_path)
    assert cache.restore(second, target, tmp_path)
    assert sum(p.stat().st_size for p in cache.root.rglob("*") if p.is_file()) <= cache.budget + 1
    assert put(cache, tmp_path, "huge", b"x" * 13000)[1] == "too_large"


def test_expiry_partial_and_corrupt_manifest(cache, tmp_path):
    identity, _ = put(cache, tmp_path, "one")
    directory = cache.root / cache._key(identity)
    os.utime(directory, (time.time() - cache.ttl - 2,) * 2)
    pending = cache.root / "pending"
    pending.mkdir()
    (pending / "index.sqlite").write_bytes(b"interrupted write")
    assert not cache.restore(identity, tmp_path / "result", tmp_path)
    assert not pending.exists() and not directory.exists()
    put(cache, tmp_path, "one")
    (directory / "manifest.json").write_text("not json")
    assert not cache.restore(identity, tmp_path / "result", tmp_path)
    assert not directory.exists()


def test_manifest_size_and_reduced_session_quota(cache, tmp_path):
    identity, _ = put(cache, tmp_path, "one")
    directory = cache.root / cache._key(identity)
    cache.index_limit = 100
    assert not cache.restore(identity, tmp_path / "result", tmp_path)
    assert not directory.exists()
    cache.index_limit = 8000
    put(cache, tmp_path, "one")
    (directory / "manifest.json").write_bytes(b"x" * 5000)
    assert not cache.restore(identity, tmp_path / "result", tmp_path)


def test_restore_clears_page_reservation(cache, tmp_path):
    identity, _ = put(cache, tmp_path, "one")
    pages = tmp_path / "query-cache"
    pages.mkdir()
    (pages / "one.json").write_text("{}")
    assert cache.restore(identity, tmp_path / "result", tmp_path)
    assert not list(pages.iterdir())


def _hold_lock(root, ready):
    cache = DurableIndexes(Settings(allowed_roots=(root.parent,), xref_cache_dir=root))
    with cache._locked():
        pending = root / "pending"
        pending.mkdir()
        (pending / "index.sqlite").write_bytes(b"unfinished")
        ready.set()
        time.sleep(60)


def test_dead_writer_releases_process_lock(cache, tmp_path):
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    writer = context.Process(target=_hold_lock, args=(cache.root, ready))
    writer.start()
    try:
        assert ready.wait(15)
        writer.terminate()
        writer.join(15)
        assert not writer.is_alive()
        identity, status = put(cache, tmp_path, "one")
        assert status == "stored"
        assert cache.restore(identity, tmp_path / "result", tmp_path)
        assert not (cache.root / "pending").exists()
    finally:
        if writer.is_alive():
            writer.kill()
        writer.join(15)


def test_disabled_cache_and_unrelated_directory(tmp_path, cache):
    disabled = DurableIndexes(Settings(allowed_roots=(tmp_path,)))
    assert disabled.publish({}, tmp_path / "absent") == "disabled"
    assert not disabled.restore({}, tmp_path / "absent", tmp_path)
    cache.root.mkdir(mode=0o700)
    sentinel = cache.root / "unrelated.txt"
    sentinel.write_text("keep")
    with pytest.raises(DroidAscError, match="unrelated"):
        put(cache, tmp_path, "one")
    assert sentinel.read_text() == "keep"


def _publish_process(root, key):
    cache = DurableIndexes(
        Settings(allowed_roots=(root.parent,), xref_cache_dir=root, max_xref_cache_bytes=18000)
    )
    return put(cache, root.parent, key)[1]


def test_concurrent_process_publication_stays_bounded(cache, tmp_path):
    with ProcessPoolExecutor(
        max_workers=4, mp_context=multiprocessing.get_context("spawn")
    ) as pool:
        results = list(pool.map(_publish_process, [cache.root] * 4, ["a", "b", "c", "d"]))
    assert results == ["stored"] * 4
    assert not (cache.root / "pending").exists()
    assert sum(p.stat().st_size for p in cache.root.rglob("*") if p.is_file()) <= 18001
    for manifest in cache.root.glob("*/manifest.json"):
        data = json.loads(manifest.read_bytes())
        cache.budget = 18000
        assert cache.restore(data["identity"], tmp_path / "checked", tmp_path)
        (tmp_path / "checked").unlink()


def test_persistent_index_reused_by_new_service(smali_dex_files, tmp_path):
    from droidasc_mcp.service import DroidAscService

    settings = replace(
        Settings.from_env(),
        allowed_roots=(smali_dex_files[0].parent,),
        xref_cache_dir=tmp_path / "persistent",
    )
    first = DroidAscService(settings)
    try:
        key = first.open_dex_session(list(map(str, smali_dex_files)))["session_id"]
        built = first.query_dex_session(key, operation="build_xref_index", offset=0, limit=1000)
        assert built["status"] == "ok", built
        assert built["index"]["durable_cache"] == "stored"
        expected = first.query_dex_session(
            key,
            operation="find_field_refs",
            field_descriptor="Lfixture/Target;->value:I",
            offset=0,
            limit=1000,
        )
    finally:
        first.close()
    # A new service has no session paths or state inherited from the first.
    second = DroidAscService(replace(settings, java_executable="missing-java-for-reuse-test"))
    try:
        key = second.open_dex_session(list(map(str, smali_dex_files)))["session_id"]
        actual = second.query_dex_session(
            key,
            operation="find_field_refs",
            field_descriptor="Lfixture/Target;->value:I",
            offset=0,
            limit=1000,
        )
        assert actual["status"] == "ok", actual
        assert actual["index"]["durable_cache"] == "restored"
        assert actual["items"] == expected["items"] and actual["total"] == expected["total"]
        assert actual["index"]["reused"]
        manifests = list(settings.xref_cache_dir.glob("*/manifest.json"))
        assert len(manifests) == 1
        data = json.loads(manifests[0].read_bytes())
        assert data["identity"]["input_id"] == actual["input_id"]
    finally:
        second.close()
