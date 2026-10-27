"""Caller grouping preserves the flat reference stream, including repeated evidence."""

import copy
import json
from dataclasses import replace
from pathlib import Path

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService


def flatten(groups):
    rows = []
    for group in groups:
        for evidence in group["evidence"]:
            row = {"dex_entry": group["dex_entry"], "caller": group["caller"], **evidence}
            row[group["target_field"]] = group["matches"][row.pop("target_index")]
            if "offset_unit" in group:
                row["offset_unit"] = group["offset_unit"]
            rows.append(row)
    return rows


@pytest.mark.parametrize("target_key", ["callee", "field_descriptor", "value", "type_descriptor"])
def test_grouped_references_round_trip_every_field_and_duplicate(target_key):
    from droidasc_mcp.reference_groups import group_reference_rows

    rows = [
        {"dex_entry": "classes.dex", "caller": "La;->m()V", target_key: "z", "offset": 3},
        {"dex_entry": "classes.dex", "caller": "La;->m()V", target_key: "a", "offset": 6},
        {"dex_entry": "classes.dex", "caller": "La;->m()V", target_key: "a", "offset": 6},
        {"dex_entry": "classes.dex", "caller": "Lb;->m()V", target_key: "z", "offset": 0},
        {"dex_entry": "classes.dex", "caller": "La;->m()V", target_key: "z", "offset": 9},
        {"dex_entry": "classes2.dex", "caller": "La;->m()V", target_key: "z", "offset": 3},
    ]
    rows[0]["target_resolution"] = "not_defined_in_input"
    rows[0]["target_dex_entry"] = None
    original = copy.deepcopy(rows)
    groups = group_reference_rows(rows)
    assert rows == original
    assert len(groups) == 4
    assert groups[0]["matches"] == ["z", "a"]
    assert groups[0]["target_field"] == target_key
    assert all(target_key not in row for group in groups for row in group["evidence"])
    assert len(groups[0]["evidence"]) == 3
    restored = flatten(groups)
    assert restored == original
    groups[0]["evidence"][0]["offset"] = -1
    assert rows == original


def test_empty_results_and_empty_string_targets():
    from droidasc_mcp.reference_groups import group_reference_rows

    assert group_reference_rows([]) == []
    groups = group_reference_rows(
        [{"dex_entry": "classes.dex", "caller": "La;->m()V", "value": ""}]
    )
    assert groups[0]["matches"] == [""]


def test_group_headers_preserve_mixed_units_and_target_kinds():
    from droidasc_mcp.reference_groups import ReferenceGroups

    base = {"dex_entry": "classes.dex", "caller": "La;->m()V", "value": "x"}
    rows = [
        base,
        {**base, "offset_unit": None},
        {**base, "offset_unit": "bytes"},
        {**base, "offset_unit": "code_units"},
        {"dex_entry": "classes.dex", "caller": "La;->m()V", "callee": "x"},
    ]
    page = ReferenceGroups()
    for row in rows:
        assert page.offer(row)
        assert page.size == len(json.dumps(page.finish()).encode())
    assert len(page.finish()) == 5
    assert flatten(page.finish()) == rows


def test_target_table_byte_budget_is_exact_and_rejections_leave_page_unchanged():
    from droidasc_mcp.reference_groups import ReferenceGroups

    page = ReferenceGroups()
    base = {"dex_entry": "classes.dex", "caller": "La;->m()V", "offset_unit": "bytes"}
    for index in range(14):
        row = {**base, "value": str(index), "offset": index}
        assert page.offer(row)
        assert page.size == len(json.dumps(page.finish()).encode())
    prior = copy.deepcopy(page.finish())
    assert not page.offer({**base, "value": "extra"}, maximum=page.size)
    assert page.finish() == prior
    assert page.offer({**base, "value": "0", "offset": 15})
    assert page.finish()[0]["evidence"][-1]["target_index"] == 0
    assert page.size == len(json.dumps(page.finish()).encode())


def test_continuation_chunks_do_not_require_whole_caller_materialization():
    from droidasc_mcp.reference_groups import group_reference_rows

    rows = [
        {"dex_entry": "classes.dex", "caller": "La;->m()V", "value": "v", "offset": i}
        for i in range(20)
    ]
    first, second = group_reference_rows(rows[:7]), group_reference_rows(rows[7:])
    assert len(first) == len(second) == 1
    assert [row["offset"] for page in (first, second) for row in page[0]["evidence"]] == list(
        range(20)
    )


def test_session_grouped_pages_collect_multiple_flat_pages_and_resume(string_reference_dex_files):
    settings = replace(
        Settings.from_env(), allowed_roots=(string_reference_dex_files[0].parent,), max_page_size=1
    )
    service = DroidAscService(settings)
    try:
        opened = service.open_dex_session([str(path) for path in string_reference_dex_files])
        assert opened["status"] == "ok", opened
        key = opened["session_id"]
        query = {"operation": "find_string_refs", "value": "https://", "limit": 1, "offset": 0}
        cursor, rows, pages = None, [], []
        while True:
            result = service.query_dex_session(
                key, **query, reference_format="grouped", cursor=cursor
            )
            assert result["status"] == "ok", result
            assert result["reference_format"] == "grouped"
            assert result["limit_unit"] == "caller_groups"
            assert len(result["groups"]) <= 1
            assert result["offset"] == len(rows)
            rows.extend(flatten(result["groups"]))
            pages.append(result)
            if not result["has_more"]:
                assert result["next_cursor"] is None and result["next_offset"] is None
                break
            assert result["next_offset"] == len(rows) and len(rows) < result["total"]
            assert result["next_cursor"] and result["next_cursor"] != cursor
            cursor = result["next_cursor"]
        assert len(pages) == 2 and len(rows) == pages[0]["total"] == 4
        assert pages[0]["returned_sites"] == 3
        flat = [
            service.query_dex_session(key, **{**query, "offset": i})["items"][0] for i in range(4)
        ]
        assert rows == flat
    finally:
        service.close()


@pytest.mark.parametrize(
    "query",
    [
        {"operation": "find_method_refs", "method_descriptor": "Lfixture/Target;->pick(I)V"},
        {"operation": "find_field_refs", "field_descriptor": "Lfixture/Target;->value:I"},
        {"operation": "get_method_calls", "method_descriptor": "Lfixture/Caller;->run()V"},
        {"operation": "search_refs", "kind": "method", "value": "pick", "member_match": "name"},
        {"operation": "search_refs", "kind": "field", "value": "value", "member_match": "name"},
    ],
)
def test_member_grouped_service_preserves_all_flat_rows_and_diagnostics(smali_dex_files, query):
    settings = replace(Settings.from_env(), allowed_roots=(smali_dex_files[0].parent,))
    service = DroidAscService(settings)
    try:
        opened = service.open_dex_session([str(path) for path in smali_dex_files])
        assert opened["status"] == "ok", opened
        key = opened["session_id"]
        flat = service.query_dex_session(key, **query, limit=1000, offset=0)
        assert flat["status"] == "ok" and flat["total"] > 0 and not flat["has_more"], flat
        cursor, rows = None, []
        while True:
            page = service.query_dex_session(
                key, **query, reference_format="grouped", limit=1, cursor=cursor
            )
            assert page["status"] == "ok", page
            assert page["offset"] == len(rows)
            rows.extend(flatten(page["groups"]))
            for name in (
                "total",
                "scanned_methods",
                "scanned_instructions",
                "methods_without_code",
                "instruction_scan_complete",
                "scan_errors",
                "input_id",
                "sources",
                "unresolved_matches",
                "dynamic_sites",
                "dynamic_sites_truncated",
            ):
                assert (name in page) == (name in flat)
                if name in flat:
                    assert page[name] == flat[name]
            if not page["has_more"]:
                assert page["next_cursor"] is None and page["next_offset"] is None
                break
            assert page["next_offset"] == len(rows) < flat["total"]
            cursor = page["next_cursor"]
        assert rows == flat["items"]
    finally:
        service.close()


def test_empty_grouped_service_result_has_terminal_cursor(string_reference_dex_files):
    settings = replace(Settings.from_env(), allowed_roots=(string_reference_dex_files[0].parent,))
    service = DroidAscService(settings)
    try:
        opened = service.open_dex_session([str(path) for path in string_reference_dex_files])
        result = service.query_dex_session(
            opened["session_id"],
            operation="find_string_refs",
            value="no-such-fixture-value",
            reference_format="grouped",
            limit=1,
        )
        assert result["status"] == "ok"
        assert result["total"] == result["returned_sites"] == 0 and result["groups"] == []
        assert not result["has_more"] and not result["truncated"]
        assert result["next_cursor"] is None and result["next_offset"] is None
    finally:
        service.close()


def test_warm_grouped_collection_skips_flat_formatting_and_page_cache(
    string_reference_dex_files, monkeypatch
):
    from droidasc_mcp import reference_cache

    service = DroidAscService(
        replace(Settings.from_env(), allowed_roots=(string_reference_dex_files[0].parent,))
    )
    try:
        key = service.open_dex_session([str(p) for p in string_reference_dex_files])["session_id"]
        query = {"operation": "find_string_refs", "value": "https://"}
        flat = service.query_dex_session(key, **query, limit=100, offset=0)
        assert flat["status"] == "ok" and flat["total"] == 4

        def unexpected(*args, **kwargs):
            raise AssertionError("Grouped cache hits must not format or cache flat pages")

        entry = service.sessions.entries[key]
        monkeypatch.setattr(reference_cache, "reference_page", unexpected)
        monkeypatch.setattr(entry.pages, "execute", unexpected)
        monkeypatch.setattr(service.runner, "query_dex_session", unexpected)
        grouped = service.query_dex_session(key, **query, reference_format="grouped", limit=100)
        assert grouped["status"] == "ok" and not grouped["has_more"]
        assert flatten(grouped["groups"]) == flat["items"]
    finally:
        service.close()


@pytest.mark.parametrize("kind", ["string", "type"])
@pytest.mark.parametrize("fits", [False, True])
def test_wide_caller_splits_at_byte_cap_without_losing_sites(
    wide_operand_dex_file, kind, fits, monkeypatch
):
    from droidasc_mcp import reference_cache

    monkeypatch.setattr(reference_cache, "MAX_ENTRY_BYTES", (1024 if fits else 64) * 1024)
    path, values, targets = wide_operand_dex_file
    service = DroidAscService(replace(Settings.from_env(), allowed_roots=(path.parent,)))
    try:
        key = service.open_dex_session([str(path)])["session_id"]
        query = (
            {"operation": "find_string_refs", "value": "literal[a.*]"}
            if kind == "string"
            else {
                "operation": "find_type_refs",
                "type_relation": "operand",
                "type_match": "substring",
                "type_descriptor": "Lwide/",
            }
        )
        cursor, rows, pages = None, [], 0
        while True:
            result = service.query_dex_session(
                key, **query, reference_format="grouped", cursor=cursor, limit=1
            )
            assert result["status"] == "ok", result
            assert len(json.dumps(result).encode()) + 1 <= 256 * 1024
            assert len(result["groups"]) == 1 and result["offset"] == len(rows)
            rows.extend(flatten(result["groups"]))
            pages += 1
            if not result["has_more"]:
                break
            assert result["next_offset"] == len(rows) > result["offset"]
            assert result["page_limited_by"] == "response_bytes"
            cursor = result["next_cursor"]
        assert pages > 1 and len(rows) == result["total"] == 100
        assert [row["instruction_offset"] for row in rows] == list(range(0, 200, 2))
        assert [row["value" if kind == "string" else "type_descriptor"] for row in rows] == (
            values if kind == "string" else targets
        )
        assert bool(service.sessions.entries[key].references.entries) == fits
    finally:
        service.close()


def test_cursor_bound_to_query_and_session_but_not_page_size(string_reference_dex_files):
    service = DroidAscService(
        replace(
            Settings.from_env(),
            allowed_roots=(string_reference_dex_files[0].parent,),
        )
    )
    try:
        paths = [str(path) for path in string_reference_dex_files]
        first, other = [service.open_dex_session(paths)["session_id"] for _ in range(2)]
        query = {
            "operation": "find_string_refs",
            "value": "https://",
            "reference_format": "grouped",
        }
        page = service.query_dex_session(first, **query, limit=1)
        cursor = page["next_cursor"]
        for key, params, value in (
            (other, query, cursor),
            (first, {**query, "value": "different"}, cursor),
            (first, query, cursor[:-3] + "AAA"),
            (first, query, "invalid"),
        ):
            assert (
                service.query_dex_session(key, **params, cursor=value)["code"] == "invalid_cursor"
            )
        resumed = service.query_dex_session(first, **query, cursor=cursor, limit=2)
        assert resumed["status"] == "ok" and resumed["offset"] == page["next_offset"]
        assert not resumed["has_more"]
        service.sessions.close(first)
        assert (
            service.query_dex_session(first, **query, cursor=cursor)["code"] == "session_not_found"
        )
    finally:
        service.close()


@pytest.mark.parametrize(
    "query",
    [
        {"operation": "info", "reference_format": "grouped"},
        {"operation": "info", "reference_format": "other"},
        {"operation": "info", "cursor": "token"},
        {"operation": "find_string_refs", "value": "x", "reference_format": "grouped", "offset": 1},
        {
            "operation": "find_string_refs",
            "value": "x",
            "reference_format": "grouped",
            "limit": True,
        },
        {
            "operation": "find_string_refs",
            "value": "x",
            "reference_format": "grouped",
            "cursor": "",
        },
    ],
)
def test_invalid_grouped_parameters_rejected_before_session_lookup(settings, query):
    service = DroidAscService(settings)
    try:
        with pytest.raises(ValueError):
            service.query_dex_session("missing", **query)
    finally:
        service.close()


def test_grouped_query_keeps_session_pinned_through_all_internal_pages(
    string_reference_dex_files, monkeypatch
):
    service = DroidAscService(
        replace(
            Settings.from_env(),
            allowed_roots=(string_reference_dex_files[0].parent,),
            max_page_size=1,
        )
    )
    try:
        key = service.open_dex_session([str(p) for p in string_reference_dex_files])["session_id"]
        root = Path(service.sessions.entries[key].storage.name)
        execute = service.runner.query_dex_session
        calls = []

        def close_during_first_page(*args, **kwargs):
            result = execute(*args, **kwargs)
            calls.append(result)
            assert service.sessions.close(key)["cleanup_pending"]
            assert root.exists()
            return result

        monkeypatch.setattr(service.runner, "query_dex_session", close_during_first_page)
        result = service.query_dex_session(
            key, operation="find_string_refs", value="https://", reference_format="grouped", limit=1
        )
        assert result["status"] == "ok" and result["returned_sites"] == 3
        assert len(calls) == 1, "Unseen internal pages must reuse the complete selected set"
        assert not root.exists() and key not in service.sessions.entries
    finally:
        service.close()


def test_cancelled_grouped_collection_releases_pin_and_retains_complete_cache(
    string_reference_dex_files, monkeypatch
):
    from droidasc_mcp import grouped_references

    class Cancelled(BaseException):
        pass

    service = DroidAscService(
        replace(
            Settings.from_env(),
            allowed_roots=(string_reference_dex_files[0].parent,),
        )
    )
    try:
        key = service.open_dex_session([str(p) for p in string_reference_dex_files])["session_id"]
        calls = 0
        check = grouped_references._check_cancelled

        def cancel():
            nonlocal calls
            calls += 1
            if calls == 3:
                raise Cancelled()

        monkeypatch.setattr(grouped_references, "_check_cancelled", cancel)
        query = {
            "operation": "find_string_refs",
            "value": "https://",
            "reference_format": "grouped",
        }
        with pytest.raises(Cancelled):
            service.query_dex_session(key, **query)
        entry = service.sessions.entries[key]
        assert entry.users == 0 and entry.references.entries and not entry.references.pending
        monkeypatch.setattr(grouped_references, "_check_cancelled", check)
        assert service.query_dex_session(key, **query)["returned_sites"] == 4
    finally:
        service.close()


def test_grouped_collection_checks_total_elapsed_time(string_reference_dex_files, monkeypatch):
    from droidasc_mcp import grouped_references
    from droidasc_mcp.runner import DroidAscError

    service = DroidAscService(
        replace(
            Settings.from_env(),
            allowed_roots=(string_reference_dex_files[0].parent,),
        )
    )
    try:
        key = service.open_dex_session([str(p) for p in string_reference_dex_files])["session_id"]
        ticks = iter([0, 0, service.settings.timeout_seconds + 1])
        monkeypatch.setattr(grouped_references, "monotonic", lambda: next(ticks), raising=False)
        with pytest.raises(DroidAscError, match="Grouped reference collection timed out"):
            service.query_dex_session(
                key, operation="find_string_refs", value="https://", reference_format="grouped"
            )
        assert service.sessions.entries[key].users == 0
    finally:
        service.close()


def test_cursor_tracks_preparation_changes_but_not_optional_index_creation(
    string_reference_dex_files,
):
    service = DroidAscService(
        replace(
            Settings.from_env(),
            allowed_roots=(string_reference_dex_files[0].parent,),
        )
    )
    try:
        key = service.open_dex_session([str(p) for p in string_reference_dex_files])["session_id"]
        query = {
            "operation": "find_string_refs",
            "value": "https://",
            "reference_format": "grouped",
        }
        page = service.query_dex_session(key, **query, limit=1)
        root = Path(service.sessions.entries[key].storage.name)
        (root / "calls.sqlite").touch()
        assert service.query_dex_session(key, **query, cursor=page["next_cursor"])["status"] == "ok"
        prepared = root / "prepared.json"
        prepared.write_text(prepared.read_text() + "\n")
        result = service.query_dex_session(key, **query, cursor=page["next_cursor"])
        assert result.get("code") == "invalid_cursor", result
    finally:
        service.close()
