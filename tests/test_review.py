"""Public declaration and synthetic secret oracles, independent of instruction indexes."""

import hashlib
import json
from dataclasses import replace

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService

ORACLE = {
    ("class", "Lreview/Added;", "added"),
    ("field", "Lreview/C;->added:[I", "added"),
    ("field", "Lreview/C;->removed:Ljava/lang/String;", "removed"),
    ("method", "Lreview/C;->added(I)I", "added"),
    ("method", "Lreview/C;->removed()V", "removed"),
}


@pytest.fixture
def review_service(review_dex_files):
    service = DroidAscService(
        replace(
            Settings.from_env(), allowed_roots=(review_dex_files[0].parent,), timeout_seconds=90
        )
    )
    try:
        keys = [service.open_dex_session([str(path)])["session_id"] for path in review_dex_files]
        yield service, keys
    finally:
        service.close()


def test_revision_hashes_inventory_filters_and_pages(review_service):
    service, (old, new) = review_service
    result = service.diff_dex_sessions(old, new, limit=2)
    assert result["status"] == "ok", result
    assert result["counts"] == {"added": 3, "removed": 2, "unchanged": 4}
    assert result["old_input_id"] != result["new_input_id"]
    assert result["old_sources"][0]["sha256"] != result["new_sources"][0]["sha256"]
    rows = result["items"]
    while result["has_more"]:
        result = service.diff_dex_sessions(old, new, offset=result["next_offset"], limit=2)
        rows += result["items"]
    assert {(r["kind"], r["descriptor"], r["change"]) for r in rows} == ORACLE
    assert [r["descriptor"] for r in rows] == sorted(r["descriptor"] for r in rows)
    assert all(r["old_dex_entry"] == "classes.dex" for r in rows if r["change"] == "removed")
    assert result["behavior_comparison"] == "not_performed"
    assert not any("keep()I" in row["descriptor"] for row in rows)
    fields = service.diff_dex_sessions(old, new, kind="field", change="removed")
    assert fields["total"] == 1 and fields["items"][0]["descriptor"].endswith(
        "removed:Ljava/lang/String;"
    )
    same = service.diff_dex_sessions(old, old)
    assert same["total"] == 0 and same["counts"]["unchanged"] == 6
    assert same["old_input_id"] == same["new_input_id"]


def test_candidates_redaction_locations_fingerprints_and_budget(review_service):
    service, (old, new) = review_service
    result = service.secret_candidates(old, limit=1)
    assert result["status"] == "ok", result
    rows = result["items"]
    while result["has_more"]:
        result = service.secret_candidates(old, offset=result["next_offset"], limit=1)
        rows += result["items"]
    expected = {
        "aws_access_key_id": "AKIA0000000000000000",
        "credential_assignment": "synthetic_example_value_12345",
        "private_key_marker": "-----BEGIN PRIVATE KEY-----",
    }
    assert {row["pattern"] for row in rows} == set(expected)
    for row in rows:
        assert (
            row["candidate_sha256"] == hashlib.sha256(expected[row["pattern"]].encode()).hexdigest()
        )
        assert row["dex_entry"] == "classes.dex" and row["string_index"] >= 0
        assert row["redacted"] == "[REDACTED]" and row["confidence"] == "candidate"
    assert all(value not in json.dumps(rows) for value in expected.values())
    assert result["coverage_complete"] and result["credential_validity"] == "not_checked"
    only = service.secret_candidates(old, pattern="aws_access_key_id")
    assert only["total"] == 1 and only["items"][0]["utf16_offset"] == 0
    assert service.secret_candidates(new)["total"] == 0
    budget = service.secret_candidates(old, max_scan_bytes=1)
    assert budget["status"] == "error" and budget["diagnostic"] == "secret_scan_limit"


@pytest.mark.parametrize(
    "kwargs", [{"kind": "body"}, {"change": "modified"}, {"offset": -1}, {"limit": 0}]
)
def test_diff_validates_query(review_service, kwargs):
    service, (old, new) = review_service
    with pytest.raises(ValueError):
        service.diff_dex_sessions(old, new, **kwargs)


@pytest.mark.parametrize(
    "kwargs", [{"pattern": "regex"}, {"max_scan_bytes": True}, {"max_scan_bytes": 0}]
)
def test_candidates_validate_query(review_service, kwargs):
    service, (old, _) = review_service
    with pytest.raises(ValueError):
        service.secret_candidates(old, **kwargs)


def test_diff_close_and_missing_session(review_service):
    service, (old, new) = review_service
    service.sessions.close(new)
    assert service.diff_dex_sessions(old, new)["code"] == "session_not_found"


def test_secret_values_require_explicit_opt_in(review_service):
    service, (old, _) = review_service
    shown = service.secret_candidates(old, include_values=True)
    assert shown["status"] == "ok" and shown["values_included"]
    assert all(
        hashlib.sha256(row["value"].encode()).hexdigest() == row["candidate_sha256"]
        for row in shown["items"]
    )
    hidden = service.secret_candidates(old)
    assert not hidden["values_included"]
    assert all("value" not in row for row in hidden["items"])
    with pytest.raises(ValueError):
        service.secret_candidates(old, include_values="true")
