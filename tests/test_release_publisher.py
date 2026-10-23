"""Release safety tests; all GitHub operations are mocked."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_accepted_release.py"
SPEC = importlib.util.spec_from_file_location("release_publisher", SCRIPT)
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


def approval():
    return {
        "schema": 1,
        "repository": publisher.REPOSITORY,
        "version": "0.2.4",
        "accepted_sha": "a" * 40,
        "ci_run_id": 123,
        "ci_run_attempt": 1,
        "packages": {name: "b" * 64 for name in publisher.expected_packages()},
        "sha256sums_sha256": "c" * 64,
        "title": "v0.2.4 - Accepted increment",
        "body": "## Highlights\n\n## Acceptance\n"
        + "a" * 40
        + "\nhttps://github.com/cnlnn/droidasc-mcp/actions/runs/123\n"
        + "## Install\n\n## Limits\n",
    }


def jobs():
    return [
        {
            "name": name,
            "run_id": 123,
            "run_attempt": 1,
            "status": "completed",
            "conclusion": "success",
        }
        for name in publisher.expected_jobs()
    ]


def test_exact_ci_matrix():
    assert len(publisher.expected_jobs()) == 25
    publisher.validate_jobs(jobs(), 123, 1)


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "unrelated"),
        ("run_id", 124),
        ("run_attempt", 2),
        ("status", "in_progress"),
        ("conclusion", "failure"),
        ("conclusion", "skipped"),
    ],
)
def test_rejects_wrong_ci_job(field, value):
    rows = jobs()
    rows[0][field] = value
    with pytest.raises(ValueError):
        publisher.validate_jobs(rows, 123, 1)


def test_rejects_missing_or_duplicate_ci_jobs():
    rows = jobs()
    with pytest.raises(ValueError):
        publisher.validate_jobs(rows[:-1], 123, 1)
    rows[-1] = rows[0].copy()
    with pytest.raises(ValueError):
        publisher.validate_jobs(rows, 123, 1)


def test_accepts_complete_approval():
    publisher.validate_approval(approval())


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", "0.3.0"),
        ("repository", "someone/else"),
        ("accepted_sha", "main"),
        ("ci_run_id", True),
        ("ci_run_attempt", 0),
        ("packages", {}),
        ("title", "Wrong title"),
        ("body", "No evidence"),
    ],
)
def test_rejects_incomplete_approval(field, value):
    item = approval()
    item[field] = value
    with pytest.raises(ValueError):
        publisher.validate_approval(item)


def test_exact_packages_and_manifest_are_staged_without_rebuilding(tmp_path):
    packages = {name: name.encode() for name in publisher.expected_packages()}
    sums = "".join(
        f"{publisher.sha256(raw)}  {name}\n" for name, raw in sorted(packages.items())
    ).encode()
    item = approval()
    item["sha256sums_sha256"] = publisher.sha256(sums)
    target = tmp_path / "stage"
    result = publisher.stage_assets(item, packages, target)
    assert result == {**packages, "SHA256SUMS": sums}
    assert {p.name: p.read_bytes() for p in target.iterdir()} == result
    with pytest.raises(ValueError, match="must be new"):
        publisher.stage_assets(item, packages, target)


def test_rejects_changed_checksum_manifest(tmp_path):
    packages = {name: name.encode() for name in publisher.expected_packages()}
    with pytest.raises(ValueError, match="manifest differs"):
        publisher.stage_assets(approval(), packages, tmp_path / "stage")


def test_refuses_conflicting_tag_before_any_release_write(monkeypatch, tmp_path):
    calls = []

    def api(path, method="GET", payload=None):
        calls.append((path, method))
        assert "matching-refs/tags/v0.2.4" in path
        return [{"ref": "refs/tags/v0.2.4", "object": {"type": "commit", "sha": "d" * 40}}]

    monkeypatch.setattr(publisher, "api", api)
    with pytest.raises(ValueError, match="Existing tag differs"):
        publisher.publish(approval(), {}, tmp_path)
    assert len(calls) == 1 and calls[0][1] == "GET"


@pytest.mark.parametrize("tag_type,tag_sha", [("tag", "a" * 40), ("commit", "b" * 40)])
def test_refuses_ambiguous_or_nonmatching_tag(monkeypatch, tag_type, tag_sha):
    monkeypatch.setattr(
        publisher,
        "api",
        lambda path: [{"ref": "refs/tags/v0.2.4", "object": {"type": tag_type, "sha": tag_sha}}],
    )
    with pytest.raises(ValueError):
        publisher.verify_existing_tag("a" * 40)


def test_accepts_existing_exact_tag(monkeypatch):
    monkeypatch.setattr(
        publisher,
        "api",
        lambda path: [{"ref": "refs/tags/v0.2.4", "object": {"type": "commit", "sha": "a" * 40}}],
    )
    publisher.verify_existing_tag("a" * 40)


def test_rejects_altered_evidence_bytes():
    raw = b'{"status":"passed"}'
    assert publisher.checked_json_bytes(raw, publisher.sha256(raw))["status"] == "passed"
    with pytest.raises(ValueError, match="hash mismatch"):
        publisher.checked_json_bytes(b'{"status":"failed"}', publisher.sha256(raw))


def test_wrong_readback_bytes_prevent_success(monkeypatch):
    assets = {str(i): bytes([i]) for i in range(6)}
    monkeypatch.setattr(
        publisher,
        "collection",
        lambda path: [{"id": i, "name": str(i), "size": 1, "state": "uploaded"} for i in range(6)],
    )
    monkeypatch.setattr(publisher, "command", lambda *args: b"wrong bytes")
    with pytest.raises(ValueError, match="readback differs"):
        publisher.verify_asset_readback({"id": 1}, assets)


def test_rejects_api_targets_outside_repository():
    with pytest.raises(ValueError, match="outside release repository"):
        publisher.api("repos/someone/else/releases", "POST", {})


def test_control_moving_during_upload_prevents_publish(monkeypatch, tmp_path):
    item = approval()
    release = {
        "id": 10,
        "name": item["title"],
        "body": item["body"],
        "target_commitish": item["accepted_sha"],
        "draft": True,
        "prerelease": False,
    }
    calls = []
    monkeypatch.setenv("RELEASE_CONTROL_SHA", "b" * 40)
    monkeypatch.setattr(publisher, "releases_for_tag", lambda: [release])
    monkeypatch.setattr(publisher, "collection", lambda path: [])
    monkeypatch.setattr(publisher, "verify_asset_readback", lambda *args: None)
    monkeypatch.setattr(publisher, "validate_ci", lambda *args: None)
    monkeypatch.setattr(publisher, "command", lambda *args: b"")

    def api(path, method="GET", payload=None):
        calls.append((path, method))
        assert method == "GET", "A superseded release must not be published"
        if "matching-refs" in path:
            return []
        if path.endswith("heads/main"):
            return {"object": {"sha": item["accepted_sha"]}}
        if path.endswith("heads/publish/v0.2.4"):
            return {"object": {"sha": "c" * 40}}
        raise AssertionError(path)

    monkeypatch.setattr(publisher, "api", api)
    with pytest.raises(ValueError, match="superseded"):
        publisher.publish(item, {"asset": b"data"}, tmp_path)
    assert not any(method == "PATCH" for _, method in calls)


def test_untrusted_request_actor_stops_before_control_is_read(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setattr(publisher, "command", lambda *args: ("a" * 40).encode())
    calls = []

    def api(path):
        calls.append(path)
        if path.endswith("heads/main"):
            return {"object": {"sha": "a" * 40}}
        if path.endswith("actions/runs/1"):
            return {"actor": {"id": 999}}
        raise AssertionError(path)

    monkeypatch.setattr(publisher, "api", api)
    with pytest.raises(ValueError, match="authorized account"):
        publisher.fetch_approval(tmp_path, "b" * 40, 1)
    assert len(calls) == 2
