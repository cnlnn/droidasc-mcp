"""Cache identity, eviction and response budgets without launching an engine."""

from dataclasses import replace

import pytest

from droidasc_mcp import query_cache


@pytest.fixture
def cache(tmp_path, settings, monkeypatch):
    monkeypatch.setattr(query_cache, "backend_identity", lambda *args: "engine-1")
    calls = []

    def execute():
        calls.append(True)
        return {"status": "ok", "items": ["proof"], "total": 1}

    def run(query=None, identity="input-1", **overrides):
        return query_cache.cached_query(
            replace(settings, **overrides),
            tmp_path / "bundle.apk",
            {"input_id": identity},
            query or {"offset": 0},
            tmp_path,
            execute,
        )

    return run, calls


def test_cache_identity_and_exact_page(cache, monkeypatch):
    run, calls = cache
    assert run()["query_cache"] == {"hit": False, "stored": True, "scope": "exact_query_page"}
    assert run()["query_cache"]["hit"]
    assert len(calls) == 1
    assert not run({"offset": 1})["query_cache"]["hit"]
    assert not run(identity="input-2")["query_cache"]["hit"]
    assert not run(max_page_size=5)["query_cache"]["hit"]
    monkeypatch.setattr(query_cache, "backend_identity", lambda *args: "engine-2")
    assert not run()["query_cache"]["hit"]
    assert len(calls) == 5


def test_cache_lru_byte_budget_and_corruption(cache, tmp_path, monkeypatch):
    run, calls = cache
    monkeypatch.setattr(query_cache, "MAX_ENTRIES", 2)
    run({"offset": 1})
    run({"offset": 2})
    assert run({"offset": 1})["query_cache"]["hit"]
    run({"offset": 3})
    assert len(list((tmp_path / "query-cache").glob("*.json"))) == 2
    assert run({"offset": 1})["query_cache"]["hit"]
    assert not run({"offset": 2})["query_cache"]["hit"]
    query_cache.clear_cache(tmp_path)
    for offset in range(10):
        run({"offset": offset}, max_xref_index_bytes=80)
    pages = list((tmp_path / "query-cache").glob("*.json"))
    assert sum(p.stat().st_size for p in pages) <= 80
    assert len(pages) == 1
    pages[0].write_bytes(b"invalid JSON")
    assert not run({"offset": 9}, max_xref_index_bytes=80)["query_cache"]["hit"]
    (tmp_path / "xrefs.sqlite").write_bytes(bytes(100))
    before = len(calls)
    assert "query_cache" not in run(max_xref_index_bytes=100)
    assert len(calls) == before + 1


def test_cache_oversized_pages_and_failures(cache, tmp_path, settings, monkeypatch):
    run, _ = cache
    assert not run(max_xref_index_bytes=1)["query_cache"]["stored"]
    assert not (tmp_path / "query-cache").exists()
    result = query_cache.cached_query(
        settings,
        tmp_path / "bundle.apk",
        {"input_id": "x"},
        {},
        tmp_path,
        lambda: {"status": "error", "code": "failed"},
    )
    assert result["status"] == "error" and not (tmp_path / "query-cache").exists()
    monkeypatch.setattr(query_cache, "backend_identity", lambda *args: None)
    assert "query_cache" not in run()
