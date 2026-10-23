"""Parent-page reuse never mutates responses or crosses engine/index identities."""

from dataclasses import replace

import pytest

from droidasc_mcp import memory_cache
from droidasc_mcp.reference_page import reference_page


@pytest.fixture
def cache(settings, tmp_path, monkeypatch):
    identity = ["engine-1"]
    monkeypatch.setattr(memory_cache, "signature", lambda *args: identity[0])
    calls = []

    def execute():
        calls.append(True)
        return {"status": "ok", "items": [{"caller": "proof"}], "total": 1}

    pages = memory_cache.PageCache()

    def run(query=None, **options):
        return pages.execute(replace(settings, **options), tmp_path, query or {}, execute)

    return run, calls, identity, pages


def test_parent_cache_identity_page_and_copy(cache):
    run, calls, identity, _ = cache
    result = run()
    result["items"].clear()
    assert run()["items"] == [{"caller": "proof"}]
    assert run()["query_cache"]["hit"] and len(calls) == 1
    run({"offset": 1})
    assert len(calls) == 2
    identity[0] = "engine-2"
    run()
    assert len(calls) == 3
    identity[0] = None
    run()
    run()
    assert len(calls) == 5


def test_parent_cache_lru_and_bytes(cache, monkeypatch):
    run, calls, _, pages = cache
    monkeypatch.setattr(memory_cache, "MAX_ENTRIES", 2)
    run({"offset": 1})
    run({"offset": 2})
    run({"offset": 1})
    run({"offset": 3})
    assert len(pages.pages) == 2
    assert run({"offset": 1})["query_cache"]["hit"]
    run({"offset": 2})
    assert len(calls) == 4
    monkeypatch.setattr(memory_cache, "MAX_BYTES", 1)
    run({"offset": 4})
    assert len(pages.pages) == 2


@pytest.mark.parametrize(
    "result", [{"status": "error"}, {"status": "ok", "index": {"reused": False}}]
)
def test_errors_and_first_index_build_not_reused(cache, settings, tmp_path, result):
    _, _, _, pages = cache
    calls = []

    def execute():
        calls.append(True)
        return result

    for _ in range(2):
        assert pages.execute(settings, tmp_path, {}, execute) == result
    assert len(calls) == 2 and not pages.pages


def test_signature_tracks_implementation_and_index(settings, tmp_path, monkeypatch):
    home = tmp_path / "jadx"
    (home / "lib").mkdir(parents=True)
    jar = home / "lib" / "engine.jar"
    jar.write_bytes(b"one")
    java = tmp_path / "java"
    java.write_bytes(b"java")
    monkeypatch.setattr(memory_cache.shutil, "which", lambda command: str(java))
    settings = replace(settings, jadx_home=home, java_executable=str(java))
    first = memory_cache.signature(settings, tmp_path)
    jar.write_bytes(b"two")
    assert memory_cache.signature(settings, tmp_path) != first
    first = memory_cache.signature(settings, tmp_path)
    (tmp_path / "xrefs.sqlite").write_bytes(b"index")
    assert memory_cache.signature(settings, tmp_path) != first


@pytest.mark.parametrize("name", ["analysis.apk", "prepared.json", "owners.sqlite"])
def test_signature_tracks_prepared_input_replacement(settings, tmp_path, name):
    path = tmp_path / name
    path.write_bytes(b"one")
    before = memory_cache.signature(settings, tmp_path)
    path.write_bytes(b"two")
    assert memory_cache.signature(settings, tmp_path) != before


def test_exact_page_hit_preserves_the_reference_byte_limit(settings, tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(memory_cache, "signature", lambda *args: "same")
    settings = replace(settings, max_output_bytes=1024)
    pages = memory_cache.PageCache()
    query = {"operation": "find_method_refs", "offset": 0, "limit": 100}
    result = reference_page(
        {
            "status": "ok",
            "items": [{"value": "x" * 50} for _ in range(100)],
            "total": 100,
            "offset": 0,
            "limit": 100,
            "has_more": False,
            "truncated": False,
            "next_offset": None,
        },
        settings.max_output_bytes,
    )
    first = pages.execute(settings, tmp_path, query, lambda: result)

    def rescan():
        raise AssertionError("Exact-page hit must not run the worker")

    second = pages.execute(settings, tmp_path, query, rescan)
    assert second["items"] == first["items"]
    assert second["next_offset"] == len(second["items"])
    assert len(json.dumps(second).encode()) < 1024
