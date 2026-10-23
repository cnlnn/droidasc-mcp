"""Fail-closed, GitHub-only publisher of an explicitly accepted 0.2.4 candidate.

The script runs from the accepted default-branch commit, never the request branch.
Without --publish it performs only reads and writes to the supplied local staging directory.
"""

import argparse
import base64
import hashlib
import io
import json
import os
import re
import subprocess
import zipfile
from pathlib import Path

REPOSITORY = "cnlnn/droidasc-mcp"
AUTHORIZED_ACTOR_ID = 24188176
VERSION = "0.2.4"
TAG = f"v{VERSION}"
CONTROL_BRANCH = f"publish/{TAG}"
APPROVAL_PATH = f".release/approval-{TAG}.json"
HEX40 = re.compile(r"[0-9a-f]{40}")
HEX64 = re.compile(r"[0-9a-f]{64}")
OS_NAMES = ("ubuntu-latest", "windows-latest")
PYTHONS = ("3.10", "3.11", "3.12", "3.13")
# Frozen release acceptance contract. Changes require a new candidate and complete CI.
CORPUS_CHECKS = frozenset(
    {
        "verify_preparation_directory",
        "verify_mcp_reference_pages",
        "verify_frontier_graph",
        "verify_graph_benchmark",
        "verify_reference_page_benchmark",
    }
)
CORPUS_NAMES = frozenset({"taobao", "wechat", "douyin"})


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(content):
    return hashlib.sha256(content).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def checked_sha(value, pattern=HEX64):
    require(isinstance(value, str) and pattern.fullmatch(value), "Malformed SHA")
    return value


def command(*args, data=None):
    return subprocess.run(args, input=data, stdout=subprocess.PIPE, check=True).stdout


def api(path, method="GET", payload=None):
    require(path.startswith(f"repos/{REPOSITORY}/"), "API outside release repository")
    args = ["gh", "api", "--method", method, path]
    data = None
    if payload is not None:
        args += ["--input", "-"]
        data = canonical(payload)
    return json.loads(command(*args, data=data))


def collection(path, key=None):
    items = []
    for page in range(1, 101):
        separator = "&" if "?" in path else "?"
        result = api(f"{path}{separator}per_page=100&page={page}")
        batch = result[key] if key else result
        require(isinstance(batch, list), "Invalid paginated API response")
        items.extend(batch)
        if len(batch) < 100:
            return items
    raise ValueError("Unexpectedly large API collection")


def expected_packages():
    prefix = f"droidasc_mcp-{VERSION}"
    result = {}
    for os_name, platform in (
        ("ubuntu-latest", "manylinux_2_34_x86_64"),
        ("windows-latest", "win_amd64"),
    ):
        for python, abi in (("3.10", "cp310-cp310"), ("3.11", "cp311-abi3")):
            result[f"{prefix}-{abi}-{platform}.whl"] = f"python-distributions-{os_name}-py{python}"
    result[f"{prefix}.tar.gz"] = "python-distributions-ubuntu-latest-py3.11"
    return result


def expected_jobs():
    return (
        {"fixture"}
        | {f"{job} ({os_name})" for job in ("rust", "stability") for os_name in OS_NAMES}
        | {
            f"{job} ({os_name}, {python})"
            for job in ("test", "distribution")
            for os_name in OS_NAMES
            for python in PYTHONS
        }
        | {f"package ({os_name}, {python})" for os_name in OS_NAMES for python in ("3.10", "3.11")}
    )


def validate_jobs(jobs, run_id, attempt):
    require(len(jobs) == 25, "CI must contain exactly 25 required jobs")
    require({j["name"] for j in jobs} == expected_jobs(), "Required CI matrix differs")
    for job in jobs:
        require(job["run_id"] == run_id, "Job belongs to a different run")
        require(job["run_attempt"] == attempt, "Job belongs to a different run attempt")
        require(job["status"] == "completed", "CI job is not complete")
        require(job["conclusion"] == "success", "CI job did not pass")


def checked_json_bytes(raw, digest):
    checked_sha(digest)
    require(sha256(raw) == digest, "Evidence content hash mismatch")
    value = json.loads(raw)
    require(isinstance(value, dict), "Expected a JSON object")
    return value


def package_runtime(wheel_bytes):
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), "Duplicate wheel members")
        return {
            name.removeprefix("droidasc_mcp/"): sha256(archive.read(name))
            for name in names
            if name.startswith("droidasc_mcp/") and not name.endswith("/")
        }


def validate_corpus(approval, packages, root):
    # The capsule contains deterministic privacy-safe projections of real raw reports.
    # Their SHA256s retain the link to the full local reports; no APK/code rows are public.
    raw = base64.b64decode(approval["corpus_capsule_base64"], validate=True)
    capsule = checked_json_bytes(raw, approval["corpus_capsule_sha256"])
    require(capsule["schema"] == 1, "Unsupported corpus capsule schema")
    require(capsule["execution_environment"] == "dot-cloud", "Corpus must run in dot cloud")
    require(capsule["status"] == "passed", "Corpus product gates did not pass")
    require(
        capsule["capsule_builder_sha256"]
        == sha256((root / "scripts/build_release_capsule.py").read_bytes()),
        "Corpus capsule builder differs from accepted candidate",
    )
    for name in ("accepted_sha", "ci_run_id", "ci_run_attempt"):
        require(capsule[name] == approval[name], f"Corpus {name} does not match approval")
    source_files = {
        p.relative_to(root / "src/droidasc_mcp").as_posix(): sha256(p.read_bytes())
        for p in (root / "src/droidasc_mcp").rglob("*")
        if p.is_file() and p.suffix in {".py", ".java", ".c", ".json"}
    }
    require(source_files, "Accepted source files are missing")
    require(
        capsule["source_manifest_sha256"] == sha256(canonical(source_files)),
        "Corpus source manifest differs from accepted candidate",
    )
    wheel_name = f"droidasc_mcp-{VERSION}-cp311-abi3-manylinux_2_34_x86_64.whl"
    wheel_identity = {
        "asset_name": wheel_name,
        "sha256": sha256(packages[wheel_name]),
        "installed_byte_identity_passed": True,
    }
    require(capsule["ci_wheel"] == wheel_identity, "Corpus did not test this exact CI wheel")
    wheel_runtime = package_runtime(packages[wheel_name])
    inputs = capsule["inputs"]
    require(len(inputs) == 3, "All three original corpus inputs are required")
    require({row["name"] for row in inputs} == CORPUS_NAMES, "Incorrect corpus inputs")
    input_hashes = {checked_sha(row["sha256"]) for row in inputs}
    require(len(input_hashes) == 3, "Corpus inputs must be distinct")
    for row in inputs:
        require(
            type(row["size_bytes"]) is int and row["size_bytes"] > 0,
            "Invalid input size",
        )
        require(isinstance(row["version"], str) and row["version"], "Missing corpus version")
    checks = capsule["checks"]
    expected = {
        (stage, name, digest)
        for stage in ("source", "ci_wheel")
        for name in CORPUS_CHECKS
        for digest in input_hashes
    }
    require(len(checks) == len(expected), "Missing or duplicate corpus checks")
    seen = set()
    for item in checks:
        evidence_raw = base64.b64decode(item["evidence_base64"], validate=True)
        evidence = checked_json_bytes(evidence_raw, item["evidence_sha256"])
        key = (evidence["stage"], evidence["check"], evidence["input_sha256"])
        require(
            key in expected and key not in seen,
            "Unexpected or duplicate corpus evidence",
        )
        seen.add(key)
        checked_sha(evidence["raw_receipt_sha256"])
        require(evidence["raw_status"] in {"passed", "failed"}, "Missing original report status")
        require(evidence["status"] == "passed", "A required corpus check failed")
        require(evidence["input_unchanged"] is True, "Corpus input was not stable")
        require(evidence["runtime_unchanged"] is True, "Corpus runtime was not stable")
        require(evidence["product_results_complete"] is True, "Partial corpus evidence")
        require(evidence["oracle_match"] is True, "Corpus oracle mismatch")
        require(
            type(evidence["product_cases"]) is int and evidence["product_cases"] > 0,
            "Empty product acceptance evidence",
        )
        require(evidence["product_failures"] == 0, "Product failures cannot be waived")
        require(evidence["product_missing_sites"] == 0, "Missing product result sites")
        require(evidence["product_extra_sites"] == 0, "Extra product result sites")
        competitor = evidence["competitor"]
        require(
            type(competitor["failed_cases"]) is int and competitor["failed_cases"] >= 0,
            "Invalid comparator failure count",
        )
        checked_sha(competitor["failures_sha256"])
        require(
            competitor["failed_cases_excluded_from_ratios"] is True,
            "Failed comparator cases must not produce speed ratios",
        )
        if evidence["raw_status"] == "failed":
            require(
                evidence["check"] == "verify_reference_page_benchmark"
                and competitor["failed_cases"] > 0,
                "Failed raw evidence is not a known comparator-only result",
            )
        if evidence["check"] in {"verify_frontier_graph", "verify_graph_benchmark"}:
            checked_sha(evidence["independent_call_index_sha256"])
        verifier = root / "scripts" / f"{evidence['check']}.py"
        require(
            evidence["verifier_sha256"] == sha256(verifier.read_bytes()),
            "Verifier drift",
        )
        runtime = evidence["runtime_sha256"]
        if evidence["stage"] == "ci_wheel":
            require(runtime == wheel_runtime, "Corpus installed bytes differ from CI wheel")
        else:
            require(
                {name: runtime.get(name) for name in source_files} == source_files,
                "Corpus source runtime differs from accepted source",
            )
    require(seen == expected, "Corpus matrix is incomplete")
    supplements = capsule["supplemental_checks"]
    expected_supplements = {
        (stage, "verify_method_selection", (digest,))
        for stage in ("source", "ci_wheel")
        for digest in input_hashes
    } | {
        (stage, "verify_artifact_summary", tuple(sorted(input_hashes)))
        for stage in ("source", "ci_wheel")
    }
    require(len(supplements) == 8, "All eight supplementary corpus checks are required")
    seen_supplements = set()
    for item in supplements:
        raw = base64.b64decode(item["evidence_base64"], validate=True)
        evidence = checked_json_bytes(raw, item["evidence_sha256"])
        key = (evidence["stage"], evidence["check"], tuple(evidence["input_sha256s"]))
        require(
            key in expected_supplements and key not in seen_supplements,
            "Unexpected or duplicate supplementary corpus evidence",
        )
        seen_supplements.add(key)
        checked_sha(evidence["raw_receipt_sha256"])
        require(evidence["status"] == "passed", "Supplementary corpus gate failed")
        require(
            evidence["input_unchanged"] is True and evidence["runtime_unchanged"] is True,
            "Supplementary corpus input/runtime was unstable",
        )
        require(
            evidence["oracle_match"] is True and evidence["product_failures"] == 0,
            "Supplementary product evidence differs from oracle",
        )
        require(
            type(evidence["product_cases"]) is int and evidence["product_cases"] > 0,
            "Empty supplementary product evidence",
        )
        verifier = root / "scripts" / f"{evidence['check']}.py"
        require(
            evidence["verifier_sha256"] == sha256(verifier.read_bytes()),
            "Supplementary verifier drift",
        )
        runtime = evidence["runtime_sha256"]
        if evidence["stage"] == "ci_wheel":
            require(runtime == wheel_runtime, "Supplementary wheel runtime differs")
        else:
            require(
                {name: runtime.get(name) for name in source_files} == source_files,
                "Supplementary source runtime differs",
            )
    require(seen_supplements == expected_supplements, "Supplementary corpus matrix incomplete")
    return capsule


def validate_approval(approval):
    require(approval["schema"] == 1, "Unsupported approval schema")
    require(approval["repository"] == REPOSITORY, "Wrong release repository")
    require(approval["version"] == VERSION, "Wrong release version")
    checked_sha(approval["accepted_sha"], HEX40)
    for name in ("ci_run_id", "ci_run_attempt"):
        require(type(approval[name]) is int and approval[name] > 0, "Invalid CI identity")
    require(
        set(approval["packages"]) == set(expected_packages()),
        "Exactly five packages required",
    )
    for digest in approval["packages"].values():
        checked_sha(digest)
    checked_sha(approval["sha256sums_sha256"])
    require(approval["title"].startswith(f"{TAG} - "), "Release title format differs")
    body = approval["body"]
    require(isinstance(body, str), "Release body must be text")
    for heading in ("Highlights", "Acceptance", "Install", "Limits"):
        require(f"## {heading}\n" in body, f"Missing release section: {heading}")
    require(approval["accepted_sha"] in body, "Release notes omit accepted SHA")
    require(
        f"/actions/runs/{approval['ci_run_id']}" in body,
        "Release notes omit accepted CI",
    )


def fetch_approval(root, control_sha, request_run_id):
    candidate = command("git", "-C", str(root), "rev-parse", "HEAD").decode().strip()
    checked_sha(candidate, HEX40)
    main = api(f"repos/{REPOSITORY}/git/ref/heads/main")["object"]["sha"]
    require(candidate == main == os.environ["GITHUB_SHA"], "Publisher is not accepted main")
    request = api(f"repos/{REPOSITORY}/actions/runs/{request_run_id}")
    require(
        request["actor"]["id"] == AUTHORIZED_ACTOR_ID,
        "Release request was not authored by the authorized account",
    )
    require(
        request["triggering_actor"]["id"] == AUTHORIZED_ACTOR_ID,
        "Release request was retriggered by an unauthorized account",
    )
    require(request["head_sha"] == control_sha, "Release request SHA mismatch")
    require(request["head_branch"] == CONTROL_BRANCH, "Wrong release request branch")
    require(
        request["path"] == ".github/workflows/release-request.yml",
        "Wrong request workflow",
    )
    require(request["event"] == "push", "Only an explicit control-branch push may publish")
    require(request["conclusion"] == "success", "Release request workflow did not pass")
    require(request["head_repository"]["full_name"] == REPOSITORY, "Foreign release request")
    current_control = api(f"repos/{REPOSITORY}/git/ref/heads/{CONTROL_BRANCH}")["object"]["sha"]
    require(current_control == control_sha, "Release request is superseded")
    commit = api(f"repos/{REPOSITORY}/commits/{control_sha}")
    require([p["sha"] for p in commit["parents"]] == [candidate], "Control parent differs")
    require(
        [(f["filename"], f["status"]) for f in commit["files"]] == [(APPROVAL_PATH, "added")],
        "Control commit may only add the release approval JSON",
    )
    content = api(f"repos/{REPOSITORY}/contents/{APPROVAL_PATH}?ref={control_sha}")
    require(content["encoding"] == "base64", "Approval must be an ordinary UTF-8 JSON file")
    approval = json.loads(base64.b64decode(content["content"]))
    validate_approval(approval)
    require(
        approval["accepted_sha"] == candidate,
        "Approval candidate differs from accepted main",
    )
    return approval


def validate_ci(approval):
    run_id, attempt = approval["ci_run_id"], approval["ci_run_attempt"]
    run = api(f"repos/{REPOSITORY}/actions/runs/{run_id}")
    require(run["head_sha"] == approval["accepted_sha"], "CI SHA differs from release SHA")
    require(
        run["head_repository"]["full_name"] == REPOSITORY,
        "CI is from another repository",
    )
    require(run["path"] == ".github/workflows/ci.yml", "Not the accepted CI workflow")
    require(run["event"] == "push", "CI must run the candidate itself, not a PR merge ref")
    require(run["run_attempt"] == attempt, "Accepted CI attempt has changed")
    require(run["status"] == "completed" and run["conclusion"] == "success", "CI not green")
    jobs = collection(f"repos/{REPOSITORY}/actions/runs/{run_id}/attempts/{attempt}/jobs", "jobs")
    validate_jobs(jobs, run_id, attempt)
    return collection(f"repos/{REPOSITORY}/actions/runs/{run_id}/artifacts", "artifacts")


def download_packages(approval, artifacts):
    packages = {}
    by_name = {}
    for artifact in artifacts:
        by_name.setdefault(artifact["name"], []).append(artifact)
    for artifact_name in set(expected_packages().values()):
        matches = by_name.get(artifact_name, [])
        require(len(matches) == 1, f"Missing or ambiguous artifact: {artifact_name}")
        artifact = matches[0]
        require(not artifact["expired"], "CI artifact has expired")
        require(
            artifact["workflow_run"]["id"] == approval["ci_run_id"],
            "Artifact run mismatch",
        )
        require(
            artifact["workflow_run"]["head_sha"] == approval["accepted_sha"],
            "Artifact SHA mismatch",
        )
        raw = command("gh", "api", f"repos/{REPOSITORY}/actions/artifacts/{artifact['id']}/zip")
        if artifact.get("digest"):
            require(
                artifact["digest"] == f"sha256:{sha256(raw)}",
                "Artifact ZIP digest differs",
            )
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            require(
                len(archive.namelist()) == len(set(archive.namelist())),
                "Duplicate ZIP members",
            )
            for name, origin in expected_packages().items():
                if origin == artifact_name:
                    packages[name] = archive.read(name)
    require(
        {name: sha256(raw) for name, raw in packages.items()} == approval["packages"],
        "CI package bytes differ from cloud-accepted bytes",
    )
    return packages


def stage_assets(approval, packages, directory):
    checksum_bytes = "".join(
        f"{sha256(raw)}  {name}\n" for name, raw in sorted(packages.items())
    ).encode("ascii")
    require(
        sha256(checksum_bytes) == approval["sha256sums_sha256"],
        "Checksum manifest differs",
    )
    require(not directory.exists(), "Staging directory must be new")
    directory.mkdir(parents=True)
    assets = {**packages, "SHA256SUMS": checksum_bytes}
    for name, raw in assets.items():
        (directory / name).write_bytes(raw)
    return assets


def releases_for_tag():
    # Listing includes drafts visible to this token and avoids treating an arbitrary
    # API error as evidence that no release exists.
    return [r for r in collection(f"repos/{REPOSITORY}/releases") if r["tag_name"] == TAG]


def verify_asset_readback(release, assets):
    remote = collection(f"repos/{REPOSITORY}/releases/{release['id']}/assets")
    require(len(remote) == 6, "Release must contain exactly six assets")
    require({a["name"] for a in remote} == set(assets), "Release asset inventory differs")
    for asset in remote:
        require(asset["state"] == "uploaded", "Asset upload did not complete")
        require(asset["size"] == len(assets[asset["name"]]), "Release asset size differs")
        raw = command(
            "gh",
            "api",
            "-H",
            "Accept: application/octet-stream",
            f"repos/{REPOSITORY}/releases/assets/{asset['id']}",
        )
        require(raw == assets[asset["name"]], "Release asset byte readback differs")


def verify_existing_tag(candidate):
    refs = api(f"repos/{REPOSITORY}/git/matching-refs/tags/{TAG}")
    tags = [ref for ref in refs if ref["ref"] == f"refs/tags/{TAG}"]
    require(len(tags) <= 1, "Ambiguous release tag")
    if tags:
        obj = tags[0]["object"]
        require(
            obj["type"] == "commit" and obj["sha"] == candidate,
            "Existing tag differs from accepted candidate",
        )


def verify_control_still_current():
    current = api(f"repos/{REPOSITORY}/git/ref/heads/{CONTROL_BRANCH}")["object"]["sha"]
    require(current == os.environ["RELEASE_CONTROL_SHA"], "Release request was superseded")


def publish(approval, assets, directory):
    verify_existing_tag(approval["accepted_sha"])
    existing = releases_for_tag()
    require(len(existing) <= 1, "Ambiguous existing release")
    if existing:
        release = existing[0]
        require(
            release["name"] == approval["title"] and release["body"] == approval["body"],
            "Existing release metadata differs; stop for inspection",
        )
        require(
            release["target_commitish"] == approval["accepted_sha"],
            "Existing target differs",
        )
        require(not release["prerelease"], "Existing release is a prerelease")
    else:
        # Create as draft so failed/missing uploads are not presented as a finished release.
        release = api(
            f"repos/{REPOSITORY}/releases",
            "POST",
            {
                "tag_name": TAG,
                "target_commitish": approval["accepted_sha"],
                "name": approval["title"],
                "body": approval["body"],
                "draft": True,
                "prerelease": False,
            },
        )
    remote = collection(f"repos/{REPOSITORY}/releases/{release['id']}/assets")
    require(
        len(remote) == len({a["name"] for a in remote}),
        "Duplicate existing release assets",
    )
    require({a["name"] for a in remote} <= set(assets), "Unexpected existing release asset")
    for asset in remote:
        raw = command(
            "gh",
            "api",
            "-H",
            "Accept: application/octet-stream",
            f"repos/{REPOSITORY}/releases/assets/{asset['id']}",
        )
        require(raw == assets[asset["name"]], "Existing asset differs; do not overwrite")
    missing = set(assets) - {a["name"] for a in remote}
    require(
        release["draft"] or not missing,
        "Published release is incomplete; stop for inspection",
    )
    for name in sorted(missing):
        command("gh", "release", "upload", TAG, str(directory / name), "--repo", REPOSITORY)
    verify_asset_readback(release, assets)
    # Re-check the source and acceptance immediately before the final mutation.
    require(
        api(f"repos/{REPOSITORY}/git/ref/heads/main")["object"]["sha"] == approval["accepted_sha"],
        "Main moved during release preparation",
    )
    validate_ci(approval)
    verify_existing_tag(approval["accepted_sha"])
    verify_control_still_current()
    if release["draft"]:
        release = api(
            f"repos/{REPOSITORY}/releases/{release['id']}",
            "PATCH",
            {
                "draft": False,
                "make_latest": "true",
            },
        )
    tag = api(f"repos/{REPOSITORY}/git/ref/tags/{TAG}")["object"]
    require(
        tag["type"] == "commit" and tag["sha"] == approval["accepted_sha"],
        "Release tag differs",
    )
    release = api(f"repos/{REPOSITORY}/releases/{release['id']}")
    require(not release["draft"] and not release["prerelease"], "Release not published")
    require(
        release["tag_name"] == TAG
        and release["name"] == approval["title"]
        and release["body"] == approval["body"]
        and release["target_commitish"] == approval["accepted_sha"],
        "Published release metadata differs",
    )
    require(
        api(f"repos/{REPOSITORY}/releases/latest")["id"] == release["id"],
        "Published release is not the latest release",
    )
    require(
        api(f"repos/{REPOSITORY}/git/ref/heads/main")["object"]["sha"] == approval["accepted_sha"],
        "Main moved during publication",
    )
    verify_asset_readback(release, assets)
    print(
        json.dumps(
            {
                "status": "published",
                "url": release["html_url"],
                "sha": approval["accepted_sha"],
                "assets_verified": 6,
            }
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--publish", action="store_true")
    args = parser.parse_args()
    require(os.environ.get("GITHUB_REPOSITORY") == REPOSITORY, "Wrong workflow repository")
    require(os.environ.get("GITHUB_EVENT_NAME") == "workflow_run", "Unapproved trigger")
    control_sha = checked_sha(os.environ["RELEASE_CONTROL_SHA"], HEX40)
    request_run_id = int(os.environ["RELEASE_REQUEST_RUN_ID"])
    require(request_run_id > 0, "Invalid release request run")
    root = Path(__file__).resolve().parents[1]
    approval = fetch_approval(root, control_sha, request_run_id)
    artifacts = validate_ci(approval)
    packages = download_packages(approval, artifacts)
    validate_corpus(approval, packages, root)
    assets = stage_assets(approval, packages, args.stage)
    if args.publish:
        publish(approval, assets, args.stage)
    else:
        print(
            json.dumps(
                {
                    "status": "validated",
                    "sha": approval["accepted_sha"],
                    "ci_run_id": approval["ci_run_id"],
                    "assets": sorted(assets),
                }
            )
        )


if __name__ == "__main__":
    main()
