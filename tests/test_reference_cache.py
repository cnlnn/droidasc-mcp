"""Selected reference sets share checked pages without repeating native scans."""

import hashlib
import json
import sqlite3
import threading
import time
import zlib
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import anyio
import pytest

from droidasc_mcp import reference_cache
from droidasc_mcp.config import Settings
from droidasc_mcp.reference_cache import ReferenceCache
from droidasc_mcp.reference_spool import (
    BLOCK_BYTES,
    BLOCK_ROWS,
    MAX_BLOCK_BYTES,
    MAX_STORED_BLOCK_BYTES,
    MAX_VALUE_BYTES,
    ReferenceSpool,
    checksum,
    decode_block,
)
from droidasc_mcp.runner import DroidAscError
from droidasc_mcp.service import DroidAscService


def test_real_session_new_page_reuses_complete_reference_scan(smali_dex_files, monkeypatch):
    settings = replace(Settings.from_env(), allowed_roots=(smali_dex_files[0].parent,))
    service = DroidAscService(settings)
    try:
        opened = service.open_dex_session([str(p) for p in smali_dex_files])
        assert opened["status"] == "ok", opened
        query = {
            "operation": "find_field_refs",
            "field_descriptor": "Lfixture/Target;->value:I",
            "limit": 1,
            "offset": 0,
        }
        first = service.query_dex_session(opened["session_id"], **query)
        assert first["status"] == "ok" and first["total"] > 1, first

        def rescan(*args, **kwargs):
            raise AssertionError("A new page must not invoke another full worker scan")

        monkeypatch.setattr(service.runner, "query_dex_session", rescan)
        second = service.query_dex_session(opened["session_id"], **{**query, "offset": 1})
        assert second["status"] == "ok" and second["offset"] == 1
        assert second["items"] != first["items"]
        assert second["query_cache"]["scope"] == "selected_reference_set"
    finally:
        service.close()


@pytest.mark.parametrize("kind", ["type", "string"])
@pytest.mark.parametrize("fits", [False, True])
def test_wide_operand_pages_preserve_every_site_with_or_without_cache(
    wide_operand_dex_file, monkeypatch, kind, fits
):
    monkeypatch.setattr(reference_cache, "MAX_ENTRY_BYTES", (1024 if fits else 64) * 1024)
    path, values, targets = wide_operand_dex_file
    service = DroidAscService(replace(Settings.from_env(), allowed_roots=(path.parent,)))
    try:
        key = service.open_dex_session([str(path)])["session_id"]
        query = (
            {
                "operation": "find_type_refs",
                "type_relation": "operand",
                "type_descriptor": "Lwide/",
                "type_match": "substring",
            }
            if kind == "type"
            else {"operation": "find_string_refs", "value": "literal[a.*]"}
        )
        rows, offset = [], 0
        while True:
            result = service.query_dex_session(key, **query, offset=offset, limit=100)
            assert result["status"] == "ok" and result["total"] == 100, result
            assert (
                len(json.dumps({k: v for k, v in result.items() if k != "session_id"}).encode()) + 1
                <= 256 * 1024
            )
            if offset and fits:
                assert result["query_cache"]["scope"] == "selected_reference_set"
            rows.extend(result["items"])
            if not result["has_more"]:
                break
            assert result["page_limited_by"] == "response_bytes"
            assert result["next_offset"] == offset + len(result["items"]) > offset
            offset = result["next_offset"]
        assert [row["instruction_offset"] for row in rows] == list(range(0, 200, 2))
        assert all(row["caller"] == f"Lwide/Caller;->{kind}s()V" for row in rows)
        assert all("target_resolution" not in row for row in rows)
        if kind == "string":
            assert [row["value"] for row in rows] == values
        else:
            assert [row["type_descriptor"] for row in rows] == targets
        references = service.sessions.entries[key].references
        assert bool(references.entries) == fits
        assert not references.pending
    finally:
        service.close()


QUERY = {"operation": "find_method_refs", "method_descriptor": "Lx;->m()V", "offset": 0, "limit": 1}
NEW_QUERIES = [
    {"operation": "find_string_refs", "value": "STRING_ARGUMENT", "offset": 0, "limit": 1},
    {
        "operation": "find_type_refs",
        "type_descriptor": "Lfixture/Target;",
        "type_relation": "operand",
        "offset": 0,
        "limit": 1,
    },
]
ROWS = [
    {"caller": "Lc;->run()V", "callee": "Lx;->m()V", "instruction_offset": offset}
    for offset in (0, 3, 3)
]


@pytest.fixture
def cached(tmp_path, settings, monkeypatch):
    identity = ["one"]
    monkeypatch.setattr(reference_cache, "signature", lambda *args: identity[0])
    cache = ReferenceCache(settings, tmp_path, 128 * 1024)
    monkeypatch.setattr(reference_cache, "MAX_ENTRY_BYTES", 64 * 1024)
    return cache, identity


def write_scan(cache, ticket, rows=ROWS, **extra):
    with ReferenceSpool(ticket, cache.root, cache.settings.max_output_bytes) as spool:
        for row in rows:
            spool(row)
        spool.scanned({"Lx;->m()V": "classes2.dex"})
        spool.finish({"status": "ok", "total": len(rows), "items": [], "diagnostic": 41, **extra})


def publish(cache, query=QUERY, rows=ROWS, **extra):
    ticket = cache.begin(query)
    assert ticket is not None
    write_scan(cache, ticket, rows, **extra)
    cache.finish(ticket, publish=True)
    assert cache.entries
    return ticket


def test_pages_preserve_duplicates_metadata_and_independent_responses(cached):
    cache, _ = cached
    publish(cache, selected_method="m", prototypes=["()V"])
    first = cache.read(QUERY)
    assert first["diagnostic"] == 41 and first["selected_method"] == "m"
    assert first["items"][0]["target_dex_entry"] == "classes2.dex"
    assert first["items"][0]["target_resolution"] == "defined_in_input"
    assert first["next_offset"] == 1
    first["items"].clear()
    first["prototypes"].clear()
    second = cache.read({**QUERY, "offset": 1, "limit": 2})
    assert [row["instruction_offset"] for row in second["items"]] == [3, 3]
    assert second["prototypes"] == ["()V"] and not second["has_more"]
    assert cache.read(QUERY)["items"]
    assert cache.read({**QUERY, "offset": 2**80})["items"] == []


def test_repeated_identities_fit_existing_quota_without_losing_page_boundaries(cached):
    cache, _ = cached
    cache.settings = replace(cache.settings, max_page_size=1000)
    query = {**NEW_QUERIES[1], "type_descriptor": "Ljava/lang/String;"}
    rows = [
        {
            "caller": (
                f"Lcom/example/application/SharedOwner{i // 4};->convert(Ljava/lang/Object;)V"
            ),
            "dex_entry": "classes.dex",
            "type_descriptor": "Ljava/lang/String;",
            "opcode": "check-cast",
            "offset_unit": "code_units_from_method_start",
            "instruction_offset": i % 4,
        }
        for i in range(2000)
    ]
    rows[128] = dict(rows[127])
    ticket = cache.begin(query)
    assert ticket["budget_bytes"] == 64 * 1024
    assert len(json.dumps(rows).encode()) > ticket["budget_bytes"] * 5
    write_scan(cache, ticket, rows)
    cache.finish(ticket, publish=True)
    assert cache.entries, "Repeated reference identities should fit the unchanged storage quota"
    assert cache.used == sum(p.stat().st_size for p in Path(ticket["directory"]).iterdir())
    assert cache.used <= ticket["budget_bytes"]
    for offset, limit in ((0, 129), (127, 3), (137, 311), (777, 700), (1999, 10), (2001, 10)):
        result = cache.read({**query, "offset": offset, "limit": limit})
        assert result["items"] == rows[offset : offset + limit]
        assert result["total"] == len(rows) and result["diagnostic"] == 41


@pytest.mark.parametrize(
    "encoded,count,raw_bytes",
    [
        (zlib.compress(b"[{}]"), 0, 4),
        (zlib.compress(b"[{}]"), True, 4),
        (zlib.compress(b"[{}]"), BLOCK_ROWS + 1, 4),
        (zlib.compress(b"[{}]"), 1, MAX_BLOCK_BYTES + 1),
        (zlib.compress(b"[{}]"), 1, 3),
        (zlib.compress(b"[{}]"), 1, 5),
        (zlib.compress(b"[{}]"), 2, 4),
        (zlib.compress(b"[{}]")[:-1], 1, 4),
        (zlib.compress(b"[{}]") + b"trailing", 1, 4),
        (zlib.compress(b"[{}]") * 2, 1, 4),
        (zlib.compress(b"x" * (MAX_BLOCK_BYTES * 8)), 1, 4),
        (b"x" * (MAX_STORED_BLOCK_BYTES + 1), 1, 4),
        (b"invalid", 1, 4),
        ("text", 1, 4),
        (zlib.compress(b"[\xff]"), 1, 3),
        (zlib.compress(b"oops"), 1, 4),
        (zlib.compress(b"{}"), 1, 2),
        (zlib.compress(b"[42]"), 1, 4),
    ],
    ids=[
        "zero-count",
        "bool-count",
        "too-many-rows",
        "raw-size-over-limit",
        "raw-size-too-small",
        "raw-size-too-large",
        "row-count-mismatch",
        "truncated-stream",
        "trailing-data",
        "concatenated-streams",
        "decompression-bomb",
        "stored-size-over-limit",
        "invalid-zlib",
        "text-not-blob",
        "invalid-utf8",
        "invalid-json",
        "non-array",
        "non-object-row",
    ],
)
def test_compressed_block_rejects_invalid_or_unbounded_input(encoded, count, raw_bytes):
    with pytest.raises(ValueError):
        decode_block(encoded, count, raw_bytes)


def test_spool_buffer_and_single_wide_row_remain_bounded(cached):
    cache, _ = cached
    ticket = cache.begin(NEW_QUERIES[0])
    rows = [{"value": "x" * 1000, "instruction_offset": i} for i in range(500)]
    rows.insert(233, {"value": "x" * (MAX_VALUE_BYTES - 12)})
    assert len(json.dumps(rows[233], separators=(",", ":")).encode()) == MAX_VALUE_BYTES
    with ReferenceSpool(ticket, cache.root, cache.settings.max_output_bytes) as spool:
        for row in rows:
            spool(row)
            assert spool.enabled
            assert len(spool.buffer) < BLOCK_ROWS
            assert spool.buffer_bytes < BLOCK_BYTES
        spool.scanned({})
        spool.finish({"status": "ok", "total": len(rows)})
    path = Path(ticket["directory"]) / "data.sqlite"
    with closing(sqlite3.connect(path)) as db:
        blocks = db.execute(
            "SELECT first_row,row_count,raw_bytes,value FROM sites ORDER BY first_row"
        )
        restored = []
        for first, count, raw_bytes, encoded in blocks:
            assert first == len(restored)
            assert raw_bytes <= MAX_BLOCK_BYTES
            restored.extend(decode_block(encoded, count, raw_bytes))
    assert restored == rows
    cache.finish(ticket, publish=True)
    assert cache.entries and not cache.pending
    assert cache.used == sum(p.stat().st_size for p in path.parent.iterdir())


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE sites SET first_row=-1 WHERE first_row=0",
        "UPDATE sites SET first_row=129 WHERE first_row=128",
        "UPDATE sites SET first_row=127 WHERE first_row=128",
        "DELETE FROM sites WHERE first_row=128",
        "UPDATE sites SET row_count=0 WHERE first_row=0",
        "UPDATE sites SET row_count=129 WHERE first_row=0",
        "UPDATE sites SET raw_bytes=300000 WHERE first_row=0",
        "UPDATE sites SET value=zeroblob(300000) WHERE first_row=0",
    ],
)
def test_invalid_block_layout_cannot_publish(cached, statement):
    cache, _ = cached
    ticket = cache.begin(QUERY)
    write_scan(cache, ticket, rows=ROWS * 100)
    directory = Path(ticket["directory"])
    path = directory / "data.sqlite"
    with closing(sqlite3.connect(path)) as db, db:
        db.execute(statement)
    receipt_path = directory / "complete.json"
    receipt = json.loads(receipt_path.read_text())
    receipt.update(size=path.stat().st_size, sha256=checksum(path))
    receipt_path.write_text(json.dumps(receipt))
    cache.finish(ticket, publish=True)
    assert not cache.entries and not cache.pending and not directory.exists()
    assert cache.used == 0


def test_corrupt_block_payload_falls_back_without_escaping_cache(cached):
    cache, _ = cached
    ticket = cache.begin(QUERY)
    write_scan(cache, ticket)
    directory = Path(ticket["directory"])
    path = directory / "data.sqlite"
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("UPDATE sites SET value=?", (b"invalid zlib",))
    receipt_path = directory / "complete.json"
    receipt = json.loads(receipt_path.read_text())
    receipt.update(size=path.stat().st_size, sha256=checksum(path))
    receipt_path.write_text(json.dumps(receipt))
    cache.finish(ticket, publish=True)
    assert cache.entries
    assert cache.read(QUERY) is None
    assert not cache.entries and cache.used == 0 and not directory.exists()


@pytest.mark.parametrize("rows", [[], [{"field_descriptor": "Lz;->field:I"}]])
def test_empty_and_unresolved_field_results(cached, rows):
    cache, _ = cached
    publish(cache, rows=rows)
    result = cache.read(QUERY)
    assert result["total"] == len(rows)
    if rows:
        assert result["items"][0]["target_dex_entry"] is None
        assert result["items"][0]["target_resolution"] == "not_defined_in_input"


def test_selector_identity_covers_all_non_page_parameters(cached):
    cache, identity = cached
    publish(cache)
    for key, value in {
        "method_descriptor": "Lx;->other()V",
        "field_access": "read",
        "case_sensitive": False,
    }.items():
        assert cache.read({**QUERY, key: value}) is None
    identity[0] = "two"
    assert cache.read(QUERY) is None
    assert cache.used == 0 and not list(cache.directory.iterdir())


def test_identity_change_during_page_read_discards_cached_response(cached, monkeypatch):
    cache, _ = cached
    publish(cache)
    identities = iter(["one", "two"])
    monkeypatch.setattr(reference_cache, "signature", lambda *args: next(identities))
    assert cache.read(QUERY) is None and not cache.entries


def test_pending_reservations_deduplicate_and_bound_parallel_builds(cached):
    cache, _ = cached
    first = cache.begin(QUERY)
    assert cache.begin({**QUERY, "offset": 2}) is None
    second = cache.begin({**QUERY, "method_descriptor": "Ly;->m()V"})
    assert second is not None
    assert cache.begin({**QUERY, "method_descriptor": "Lz;->m()V"}) is None
    assert sum(lease[1] for lease in cache.pending.values()) == cache.budget
    cache.finish(first, publish=False)
    cache.finish(second, publish=False)
    assert cache.used == 0 and not cache.pending and not list(cache.directory.iterdir())


def test_lru_evicts_only_completed_sets(cached):
    cache, _ = cached
    publish(cache)
    other = {**QUERY, "method_descriptor": "Ly;->m()V"}
    publish(cache, other)
    # Tighten the private cache quota to make the next reservation evict one entry.
    cache.budget = cache.used + 64 * 1024 - 1
    assert cache.read(QUERY)
    ticket = cache.begin({**QUERY, "method_descriptor": "Lz;->m()V"})
    assert ticket and cache.read(other) is None and cache.read(QUERY)
    assert cache.used + sum(lease[1] for lease in cache.pending.values()) <= cache.budget
    cache.finish(ticket, publish=False)


def test_identity_change_cannot_publish_old_inflight_work(cached):
    cache, identity = cached
    old = cache.begin(QUERY)
    identity[0] = "two"
    new = cache.begin(QUERY)
    write_scan(cache, old)
    write_scan(cache, new)
    cache.finish(old, publish=True)
    assert not Path(old["directory"]).exists() and Path(new["directory"]).exists()
    cache.finish(new, publish=True)
    assert cache.read(QUERY) and not cache.pending


@pytest.mark.parametrize(
    "mutation",
    [
        "checksum",
        "key",
        "schema",
        "count",
        "extra_file",
        "missing_receipt",
        "invalid_db",
        "large_receipt",
    ],
)
def test_incomplete_or_corrupt_publication_never_reused(cached, mutation):
    cache, _ = cached
    ticket = cache.begin(QUERY)
    write_scan(cache, ticket)
    directory = Path(ticket["directory"])
    receipt_path = directory / "complete.json"
    receipt = json.loads(receipt_path.read_text())
    path = directory / "data.sqlite"
    if mutation in {"checksum", "key", "schema"}:
        receipt[{"checksum": "sha256", "key": "key", "schema": "schema"}[mutation]] = "wrong"
    elif mutation == "count":
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("UPDATE sites SET row_count=row_count+1 WHERE rowid=0")
        with pytest.raises(sqlite3.ProgrammingError, match="closed database"):
            db.execute("SELECT 1")
        receipt.update(size=path.stat().st_size, sha256=checksum(path))
    elif mutation == "extra_file":
        (directory / "unaccounted").touch()
    elif mutation == "missing_receipt":
        receipt_path.unlink()
    elif mutation == "invalid_db":
        path.write_bytes(b"invalid database")
        receipt.update(size=path.stat().st_size, sha256=checksum(path))
    elif mutation == "large_receipt":
        receipt["padding"] = "x" * 8192
    if mutation != "missing_receipt":
        receipt_path.write_text(json.dumps(receipt))
    cache.finish(ticket, publish=True)
    assert cache.read(QUERY) is None and not cache.pending and not directory.exists()


@pytest.mark.parametrize("mutation", ["delete_file", "delete_directory", "replace", "symlink"])
def test_post_publication_changes_invalidate_without_breaking_query(cached, mutation):
    cache, _ = cached
    ticket = publish(cache)
    directory = Path(ticket["directory"])
    path = directory / "data.sqlite"
    if mutation == "replace":
        path.write_bytes(b"changed")
    else:
        path.unlink()
        if mutation == "delete_directory":
            (directory / "complete.json").unlink()
            directory.rmdir()
        elif mutation == "symlink":
            target = cache.root / "outside"
            target.write_bytes(b"preserved")
            path.symlink_to(target)
    assert cache.read(QUERY) is None and not cache.entries and cache.used == 0
    if mutation == "symlink":
        assert target.read_bytes() == b"preserved"


class Cancelled(BaseException):
    pass


def test_cancellation_during_verification_cleans_owned_lease(cached, monkeypatch):
    cache, _ = cached
    ticket = cache.begin(QUERY)
    write_scan(cache, ticket)

    def cancel(*args):
        raise Cancelled()

    monkeypatch.setattr(reference_cache, "checksum", cancel)
    with pytest.raises(Cancelled):
        cache.finish(ticket, publish=True)
    assert not cache.pending and not cache.entries and not Path(ticket["directory"]).exists()


def test_failed_cleanup_keeps_disk_reservation_and_cancellation(cached, monkeypatch):
    cache, _ = cached
    ticket = cache.begin(QUERY)
    write_scan(cache, ticket)

    def fail(*args):
        raise OSError("sharing violation")

    def cancel(*args):
        raise Cancelled()

    monkeypatch.setattr(reference_cache.shutil, "rmtree", fail)
    monkeypatch.setattr(reference_cache, "checksum", cancel)
    with pytest.raises(Cancelled):
        cache.finish(ticket, publish=True)
    assert len(cache.pending) == 1 and not cache.entries


def test_concurrent_publications_remain_bounded_and_separate(cached):
    cache, _ = cached
    barrier = threading.Barrier(2)

    def run(query):
        ticket = cache.begin(query)
        assert ticket is not None
        write_scan(cache, ticket)
        barrier.wait(timeout=5)
        cache.finish(ticket, publish=True)
        return cache.read(query)

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(run, {**QUERY, "method_descriptor": owner})
            for owner in ("La;->m()V", "Lb;->m()V")
        ]
        assert all(future.result(timeout=10)["total"] == 3 for future in futures)
    assert len(cache.entries) == 2 and not cache.pending and cache.used <= cache.budget


@pytest.mark.parametrize(
    "failure", ["unfinished", "error", "count", "row_limit", "metadata_limit", "disk_limit"]
)
def test_worker_discards_ineligible_or_over_budget_sets(cached, failure):
    cache, _ = cached
    ticket = cache.begin(QUERY)
    with ReferenceSpool(ticket, cache.root, cache.settings.max_output_bytes) as spool:
        if failure == "disk_limit":
            for index in range(128):
                spool(
                    {
                        "callee": "Lx;->m()V",
                        "padding": hashlib.shake_256(str(index).encode()).hexdigest(2048),
                    }
                )
        else:
            spool(
                {
                    "callee": "Lx;->m()V",
                    "padding": "x" * (256 * 1024 if failure == "row_limit" else 1),
                }
            )
        if failure != "unfinished":
            spool.scanned({})
        spool.finish(
            {
                "status": "error" if failure == "error" else "ok",
                "total": 2 if failure == "count" else spool.rows,
                "padding": "x" * (256 * 1024 if failure == "metadata_limit" else 1),
            }
        )
    assert (
        sum(path.stat().st_size for path in Path(ticket["directory"]).iterdir())
        <= ticket["budget_bytes"]
    )
    cache.finish(ticket, publish=True)
    assert not cache.entries and not cache.pending and not Path(ticket["directory"]).exists()


@pytest.fixture
def real_session(smali_dex_files):
    settings = replace(Settings.from_env(), allowed_roots=(smali_dex_files[0].parent,))
    service = DroidAscService(settings)
    opened = service.open_dex_session([str(path) for path in smali_dex_files])
    assert opened["status"] == "ok", opened
    entry = service.sessions.entries[opened["session_id"]]
    root = Path(entry.storage.name)
    yield service, opened["session_id"], entry, root
    service.close()
    assert not root.exists()


@pytest.mark.parametrize(
    "params",
    [
        {"operation": "find_method_refs", "method_descriptor": "Lexternal/Missing;->absent()V"},
        {"operation": "find_field_refs", "field_descriptor": "Lfixture/Target;->value:I"},
        {"operation": "get_method_calls", "method_descriptor": "Lfixture/Caller;->run()V"},
        {"operation": "search_refs", "kind": "method", "value": "pick", "member_match": "name"},
        {"operation": "search_refs", "kind": "field", "value": "value", "field_access": "write"},
        {"operation": "get_method_calls", "class_name": "fixture.Caller", "method_name": "run"},
        {"operation": "find_string_refs", "value": "STRING_ARGUMENT"},
        {
            "operation": "find_type_refs",
            "type_descriptor": "Lfixture/Target;",
            "type_relation": "operand",
        },
    ],
    ids=[
        "method",
        "field",
        "outgoing",
        "fuzzy-method",
        "fuzzy-field",
        "named-method",
        "string",
        "type",
    ],
)
def test_real_cached_full_pages_equal_uncached_query(real_session, monkeypatch, params):
    service, session_id, entry, root = real_session
    first = service.query_dex_session(session_id, offset=0, limit=1, **params)
    assert first["status"] == "ok" and first["total"] > 0, first
    from droidasc_mcp.service import _normalize_dex_query

    query = _normalize_dex_query({**params, "offset": 0, "limit": 100})
    expected = service.runner.query_dex_session(root, query)
    expected["session_id"] = session_id
    calls = []

    def unexpected_scan(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Reference page rescanned input")

    monkeypatch.setattr(service.runner, "query_dex_session", unexpected_scan)
    second = service.query_dex_session(session_id, offset=0, limit=100, **params)
    assert second.pop("query_cache")["scope"] == "selected_reference_set"
    assert second == expected and not calls
    assert entry.references.used <= entry.references.budget


def test_cache_space_reserved_in_global_session_budget(real_session, smali_dex_files):
    service, session_id, entry, root = real_session
    before = entry.size
    result = service.query_dex_session(session_id, **QUERY)
    assert result["status"] == "ok"
    assert entry.size == before + entry.references.budget
    assert entry.references.budget == reference_cache.MAX_SESSION_BYTES
    assert sum(p.stat().st_size for p in root.rglob("*") if p.is_file()) <= entry.size
    reservation = (
        sum(path.stat().st_size for path in smali_dex_files) * 2
        + service.settings.max_output_bytes * 2
        + 1024**2
        + service.settings.max_xref_index_bytes
    )
    service.sessions.settings = replace(
        service.settings, max_dex_session_bytes=entry.size + reservation - 1
    )
    entry.users += 1
    try:
        assert (
            service.open_dex_session([str(p) for p in smali_dex_files])["code"]
            == "session_capacity"
        )
    finally:
        entry.users -= 1
    assert service.sessions.reserved == 0


@pytest.mark.parametrize("query", [QUERY, *NEW_QUERIES])
def test_insufficient_cache_budget_preserves_correct_uncached_queries(real_session, query):
    service, session_id, entry, _ = real_session
    service.sessions.settings = replace(service.settings, max_dex_session_bytes=entry.size)
    result = service.query_dex_session(session_id, **query)
    assert result["status"] == "ok" and entry.references is None


@pytest.mark.parametrize("failure", [DroidAscError("worker failed"), Cancelled()])
@pytest.mark.parametrize("query", [QUERY, *NEW_QUERIES])
def test_worker_failure_or_cancellation_releases_cache_lease(
    real_session, monkeypatch, failure, query
):
    service, session_id, entry, _ = real_session

    def fail(root, query, *, reference_cache):
        (Path(reference_cache["directory"]) / "partial").write_bytes(b"partial")
        raise failure

    monkeypatch.setattr(service.runner, "query_dex_session", fail)
    with pytest.raises(type(failure)):
        service.query_dex_session(session_id, **query)
    assert entry.users == 0 and not entry.references.pending
    assert not list(entry.references.directory.iterdir())


@pytest.mark.parametrize("query", [QUERY, *NEW_QUERIES])
def test_close_waits_for_cache_writer_and_removes_owned_files(real_session, monkeypatch, query):
    service, session_id, entry, root = real_session
    entered, release = threading.Event(), threading.Event()
    original = service.runner.query_dex_session

    def blocked(root, query, *, reference_cache):
        entered.set()
        assert release.wait(5)
        return original(root, query, reference_cache=reference_cache)

    monkeypatch.setattr(service.runner, "query_dex_session", blocked)
    with ThreadPoolExecutor() as pool:
        future = pool.submit(service.query_dex_session, session_id, **query)
        try:
            assert entered.wait(3)
            assert service.sessions.close(session_id)["cleanup_pending"]
            assert root.exists() and entry.references.pending
        finally:
            release.set()
        assert future.result(timeout=10)["status"] == "ok"
    assert not root.exists() and session_id not in service.sessions.entries


@pytest.mark.parametrize("params", [None, *NEW_QUERIES])
def test_same_selector_pages_share_one_real_worker_scan(real_session, monkeypatch, params):
    service, session_id, entry, _ = real_session
    entered, release = threading.Event(), threading.Event()
    original = service.runner.query_dex_session
    calls = []

    def blocked(root, query, **options):
        calls.append(query["offset"])
        entered.set()
        assert release.wait(5)
        return original(root, query, **options)

    query = {
        "operation": "find_field_refs",
        "field_descriptor": "Lfixture/Target;->value:I",
        "limit": 1,
    }
    if params:
        query = {key: value for key, value in params.items() if key != "offset"}
    monkeypatch.setattr(service.runner, "query_dex_session", blocked)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(service.query_dex_session, session_id, offset=0, **query)
        assert entered.wait(3)
        second = pool.submit(service.query_dex_session, session_id, offset=1, **query)
        try:
            deadline = time.monotonic() + 3
            while entry.users != 2 and time.monotonic() < deadline:
                time.sleep(0.01)
            assert entry.users == 2
        finally:
            release.set()
        assert first.result(timeout=10)["status"] == "ok"
        assert second.result(timeout=10)["query_cache"]["scope"] == "selected_reference_set"
    assert calls == [0] and entry.users == 0 and not entry.references.pending


@pytest.mark.anyio
async def test_cancelled_page_waiter_keeps_leader_lease_and_session_usable(
    real_session, monkeypatch
):
    service, session_id, entry, _ = real_session
    entered, release = threading.Event(), threading.Event()
    original = service.runner.query_dex_session
    query = {
        "operation": "find_field_refs",
        "field_descriptor": "Lfixture/Target;->value:I",
        "limit": 1,
    }

    def blocked(root, query, **options):
        entered.set()
        assert release.wait(5)
        return original(root, query, **options)

    monkeypatch.setattr(service.runner, "query_dex_session", blocked)
    with ThreadPoolExecutor(max_workers=1) as pool:
        leader = pool.submit(service.query_dex_session, session_id, offset=0, **query)
        assert entered.wait(3)
        scope = anyio.CancelScope()

        async def wait_for_page():
            with scope:
                await anyio.to_thread.run_sync(
                    lambda: service.query_dex_session(session_id, offset=1, **query)
                )

        try:
            async with anyio.create_task_group() as tasks:
                tasks.start_soon(wait_for_page)
                with anyio.fail_after(3):
                    while entry.users != 2:
                        await anyio.sleep(0.01)
                scope.cancel()
            assert entry.users == 1 and len(entry.references.pending) == 1
        finally:
            release.set()
        assert leader.result(timeout=10)["status"] == "ok"
    result = service.query_dex_session(session_id, offset=1, **query)
    assert result["query_cache"]["scope"] == "selected_reference_set"
    assert entry.users == 0 and not entry.references.pending


@pytest.mark.parametrize("count,padding", [(300, 1000), (400, 550)])
def test_oversized_page_returns_complete_bounded_prefix_without_rescanning(
    cached, monkeypatch, count, padding
):
    cache, _ = cached
    # More than the response cap, but comfortably within the selected-set disk quota.
    rows = [{"callee": "Lx;->m()V", "padding": "x" * padding} for _ in range(count)]
    cache.budget = 1024**2
    cache.settings = replace(cache.settings, max_page_size=1000)
    monkeypatch.setattr(reference_cache, "MAX_ENTRY_BYTES", cache.budget)
    publish(cache, rows=rows)
    offset, actual = 0, []
    while True:
        result = cache.read({**QUERY, "offset": offset, "limit": count})
        assert result["status"] == "ok", result
        assert result["limit"] == count and result["offset"] == offset
        assert len(json.dumps(result).encode()) < 256 * 1024
        actual.extend(result["items"])
        if result["next_offset"] is None:
            break
        assert result["page_limited_by"] == "response_bytes"
        assert result["has_more"] and result["truncated"]
        assert result["next_offset"] == offset + len(result["items"]) > offset
        offset = result["next_offset"]
    assert [{k: v for k, v in row.items() if not k.startswith("target_")} for row in actual] == rows
    assert cache.begin(QUERY) is None
    assert cache.read(QUERY)["total"] == count


def test_optional_cache_diagnostics_do_not_reject_an_otherwise_valid_page(cached, monkeypatch):
    cache, _ = cached
    publish(cache, rows=ROWS[:1])
    result = cache.read(QUERY)
    result.pop("query_cache")
    monkeypatch.setattr(reference_cache, "MAX_VALUE_BYTES", len(json.dumps(result).encode()) + 1)
    assert cache.read(QUERY) == result


def test_cache_directory_symlink_is_not_followed(cached, tmp_path):
    cache, _ = cached
    target = tmp_path / "outside"
    target.mkdir()
    cache.directory.symlink_to(target, target_is_directory=True)
    assert cache.begin(QUERY) is None
    assert not list(target.iterdir())


@pytest.mark.parametrize("mutation", ["outside", "symlink", "nonempty", "invalid_name"])
def test_worker_rejects_unowned_ticket_directories(cached, mutation):
    cache, _ = cached
    ticket = cache.begin(QUERY)
    directory = Path(ticket["directory"])
    altered = dict(ticket)
    outside = cache.root / "outside"
    outside.mkdir()
    if mutation == "outside":
        altered["directory"] = str(outside)
    elif mutation == "symlink":
        directory.rmdir()
        directory.symlink_to(outside, target_is_directory=True)
    elif mutation == "nonempty":
        (directory / "keep").write_text("preserved")
    elif mutation == "invalid_name":
        altered["directory"] = str(cache.directory / "invalid.pending")
        Path(altered["directory"]).mkdir()
    with ReferenceSpool(altered, cache.root, cache.settings.max_output_bytes) as spool:
        assert not spool.enabled
    assert not list(outside.iterdir())
    assert not list(cache.root.rglob("data.sqlite"))


def test_read_connection_is_closed_when_setup_fails(tmp_path, monkeypatch):
    db = Mock()
    db.execute.side_effect = sqlite3.DatabaseError("invalid database")
    monkeypatch.setattr(reference_cache.sqlite3, "connect", lambda *args, **kwargs: db)
    with pytest.raises(sqlite3.DatabaseError):
        reference_cache._connect(tmp_path / "data.sqlite")
    db.close.assert_called_once()


def test_worker_cache_close_failure_leaves_analysis_available(tmp_path):
    spool = ReferenceSpool(None, tmp_path, 1024)
    db = spool.db = Mock()
    db.close.side_effect = sqlite3.Error("close failed")
    spool.close()
    assert not spool.enabled and spool.db is None
    db.close.assert_called_once()
