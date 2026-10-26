"""Byte-limited pages retain complete rows and gap-free, advancing continuations."""

import json
from copy import deepcopy

import pytest

from droidasc_mcp.reference_page import reference_page


def page(rows, offset=0, remaining=100):
    return {
        "status": "ok",
        "items": rows,
        "offset": offset,
        "limit": len(rows),
        "total": offset + len(rows) + remaining,
        "has_more": bool(remaining),
        "truncated": bool(remaining),
        "next_offset": offset + len(rows) if remaining else None,
    }


def size(value):
    return len(json.dumps(value).encode())


def test_small_and_nonpage_results_are_unchanged():
    for result in (page([{"callee": "Lx;->m()V"}]), {"status": "error"}, {"status": "ok"}):
        assert reference_page(result, 4096) is result


@pytest.mark.parametrize("offset", [0, 8, 98, 998, 2**80])
@pytest.mark.parametrize("value", ["x" * 37, '"\\\n', "\u00e9\U0001f680\ud800"])
def test_largest_prefix_fits_exact_json_bytes_without_mutation(offset, value):
    rows = [{"value": value, "ordinal": i} for i in range(60)]
    original = page(rows, offset)
    untouched = deepcopy(original)
    bounded = reference_page(original, 750)
    count = len(bounded["items"])
    assert 0 < count < len(rows)
    assert bounded["items"] == rows[:count] and original == untouched
    assert bounded["limit"] == 60 and bounded["total"] == original["total"]
    assert bounded["next_offset"] == offset + count
    assert bounded["page_limited_by"] == "response_bytes"
    assert bounded["response_byte_limit"] == 749
    assert bounded["has_more"] and bounded["truncated"]
    assert size(bounded) + 1 <= 750
    extra = {**bounded, "items": rows[: count + 1], "next_offset": offset + count + 1}
    assert size(extra) + 1 > 750


def test_last_page_can_split_and_continue_to_the_exact_end():
    original = page([{"value": "x" * 100} for _ in range(10)], offset=20, remaining=0)
    result = reference_page(original, 500)
    assert result["total"] == 30 and result["has_more"] and result["truncated"]
    assert result["next_offset"] == 20 + len(result["items"]) < 30


def test_optional_diagnostics_are_dropped_before_splitting_a_valid_page():
    original = page([{"value": "proof"}])
    result = {**original, "query_cache": {"hit": True, "scope": "exact_query_page"}}
    assert reference_page(result, size(original) + 1) == original
    assert "query_cache" in result


@pytest.mark.parametrize("offset,total", [(0, 0), (3, 1)])
def test_empty_or_beyond_end_pages_do_not_invent_more_results(offset, total):
    original = {**page([], offset, 0), "total": total}
    assert reference_page(original, 512) == original


@pytest.mark.parametrize("fault", ["row", "metadata", "nonterminal_empty"])
def test_unpageable_result_returns_bounded_error_instead_of_nonadvancing_page(fault):
    result = page([{"value": "x" * (1000 if fault == "row" else 1)}])
    if fault == "metadata":
        result["metadata"] = "x" * 1000
    if fault == "nonterminal_empty":
        result.update(items=[], limit=5)
    assert reference_page(result, 512)["code"] == "response_limit"


def test_already_short_byte_bounded_prefix_has_explicit_reason():
    result = {**page([{"value": "proof"}]), "limit": 10}
    bounded = reference_page(result, 512)
    assert bounded["page_limited_by"] == "response_bytes"
    assert bounded["next_offset"] == 1


def test_cancellation_during_prefix_selection_is_propagated():
    class Cancelled(BaseException):
        pass

    calls = 0

    def check():
        nonlocal calls
        calls += 1
        if calls == 3:
            raise Cancelled

    with pytest.raises(Cancelled):
        reference_page(page([{"value": "proof"} for _ in range(100)]), 512, check=check)


def test_fixed_response_ceiling_and_worker_newline_are_reserved():
    result = reference_page(page([{"value": "x" * 900} for _ in range(1000)]), 1024**2)
    assert result["response_byte_limit"] == 256 * 1024 - 1
    assert size(result) + 1 <= 256 * 1024


@pytest.mark.parametrize(
    "cache",
    [
        {},
        {"hit": True, "scope": "selected_reference_set", "stored_bytes": 14388577},
        {"nested": [None, False, -12, {"escaped": '"\\\\\n\u00e9\U0001f680\ud800'}]},
    ],
)
@pytest.mark.parametrize("position", ["first", "middle", "last"])
def test_cache_fragment_subtraction_matches_complete_serialization(cache, position):
    result = page([{"value": "proof"}])
    if position == "first":
        original = {"query_cache": cache, **result}
    elif position == "middle":
        original = {"status": result["status"], "query_cache": cache, **result}
    else:
        original = {**result, "query_cache": cache}
    assert size(original) - size({"query_cache": cache}) == size(result)
    untouched = deepcopy(original)
    assert reference_page(original, size(result) + 1) == result
    assert original == untouched


@pytest.mark.parametrize("offset", [0, 98, 998, 2**80])
@pytest.mark.parametrize("remaining", [0, 100])
@pytest.mark.parametrize("maximum", [700, 1200, 2100])
def test_cached_prefix_equals_brute_force_serialized_oracle(offset, remaining, maximum):
    original = {
        **page(
            [
                {"ordinal": i, "value": '"\\\\\n\u00e9\U0001f680\ud800' * (1 + i % 4)}
                for i in range(25)
            ],
            offset,
            remaining,
        ),
        "query_cache": {"hit": True, "nested": [None, {"value": "\u00e9"}]},
    }
    untouched = deepcopy(original)
    ceiling = maximum - 1
    without_cache = {k: v for k, v in original.items() if k != "query_cache"}
    if size(original) <= ceiling:
        expected = original
    elif size(without_cache) <= ceiling:
        expected = without_cache
    else:
        expected = None
        for count in range(1, len(original["items"]) + 1):
            candidate = {
                **original,
                "items": original["items"][:count],
                "has_more": True,
                "truncated": True,
                "next_offset": offset + count,
                "page_limited_by": "response_bytes",
                "response_byte_limit": ceiling,
            }
            if size(candidate) > ceiling:
                break
            expected = candidate
        assert expected is not None
    assert reference_page(original, maximum) == expected
    assert original == untouched


def test_oversized_cached_page_serializes_complete_items_only_once(monkeypatch):
    import droidasc_mcp.reference_page as module

    sized = []
    original_size = module._size

    def measured(value):
        sized.append(value)
        return original_size(value)

    monkeypatch.setattr(module, "_size", measured)
    original = {
        **page([{"value": "x" * 100} for _ in range(100)]),
        "query_cache": {"hit": True, "scope": "selected_reference_set"},
    }
    bounded = reference_page(original, 1000)
    assert bounded["status"] == "ok" and 0 < len(bounded["items"]) < 100
    assert sum(isinstance(value, dict) and bool(value.get("items")) for value in sized) == 1
