"""Before/after acceptance must compare complete collections, not page layouts."""

import copy
import importlib.util
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def revisions(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("revisions", scripts / "benchmark_revisions.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def receipt(revisions, sizes, session="session"):
    opened = {"session_id": session, "input_id": "input", "artifact_sha256": "apk", "sources": []}
    tool, params = revisions.benchmark.queries("ours", session, "full_string", "", 1)[0]
    params.pop("limit")
    operations = [{"label": "open", "status": "ok", "result": opened}]
    offset = 0
    labels = []
    for index, size in enumerate(sizes):
        label = f"query:0:0:page:{index}:attempt:0"
        rows = [{"value": "a", "instruction_offset": i} for i in range(offset, offset + size)]
        more = offset + size < 3
        operations.append(
            {
                "label": label,
                "tool": tool,
                "status": "ok",
                "arguments": {**params, "offset": offset, "limit": 3},
                "result": {
                    **opened,
                    "status": "ok",
                    "items": rows,
                    "total": 3,
                    "offset": offset,
                    "limit": 3,
                    "next_offset": offset + size if more else None,
                    "has_more": more,
                    "truncated": more,
                    "scan_errors": 0,
                    "query_cache": {"hit": True, "scope": "selected_reference_set"},
                },
            }
        )
        labels.append(label)
        offset += size
    operations.append({"label": "close", "status": "ok"})
    trial = {
        "scenario": "full_string",
        "status": "passed",
        "reference_collections": [
            {"label": "query:0:0", "page_labels": labels, "response_limit_recoveries": []}
        ],
    }
    return operations, trial


@pytest.mark.anyio
async def test_full_replay_ignores_only_session_and_page_execution_metadata(revisions):
    first, first_trial = receipt(revisions, [3])
    second, second_trial = receipt(revisions, [1, 2], "other-session")
    expected = await revisions.collection_digests(first, first_trial, 1, 3)
    assert expected == await revisions.collection_digests(second, second_trial, 1, 3)
    changed = copy.deepcopy(second)
    changed[1]["result"]["items"][0]["value"] = "different"
    assert expected != await revisions.collection_digests(changed, second_trial, 1, 3)


@pytest.mark.anyio
@pytest.mark.parametrize("damage", [None, "artifact", "prepared_identity", "source"])
async def test_lazy_handle_replay_binds_snapshot_and_all_prepared_pages(revisions, damage):
    operations, trial = receipt(revisions, [1, 2])
    expected = await revisions.collection_digests(operations, trial, 1, 3)
    trial["artifact_handle"] = True
    operations[0]["result"] = {"analysis_id": "session", "sha256": "apk"}
    if damage == "artifact":
        operations[1]["result"]["artifact_sha256"] = "other"
    elif damage == "prepared_identity":
        operations[2]["result"]["input_id"] = "other"
    elif damage == "source":
        operations[2]["result"]["sources"] = [{"dex_entry": "other.dex"}]
    if damage is None:
        assert expected == await revisions.collection_digests(operations, trial, 1, 3)
    else:
        with pytest.raises(AssertionError):
            await revisions.collection_digests(operations, trial, 1, 3)


@pytest.mark.anyio
async def test_full_replay_preserves_byte_limit_retry_and_changed_page_size(revisions):
    operations, trial = receipt(revisions, [1, 1, 1])
    failed = copy.deepcopy(operations[1])
    failed.update(
        status="response_limit",
        result={"status": "error", "code": "response_limit", "session_id": "session"},
    )
    for operation in operations[1:-1]:
        operation["label"] = operation["label"].replace("attempt:0", "attempt:1")
        operation["arguments"]["limit"] = operation["result"]["limit"] = 1
    trial["reference_collections"][0].update(
        page_labels=[op["label"] for op in operations[1:-1]],
        response_limit_recoveries=[{"offset": 0, "limit": 3}],
    )
    operations.insert(1, failed)
    expected_ops, expected_trial = receipt(revisions, [3])
    assert await revisions.collection_digests(operations, trial, 1, 3) == (
        await revisions.collection_digests(expected_ops, expected_trial, 1, 3)
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "damage", ["source", "selector", "continuation", "missing", "extra", "diagnostic"]
)
async def test_full_replay_rejects_incomplete_or_tampered_pages(revisions, damage):
    operations, trial = receipt(revisions, [1, 2])
    if damage == "source":
        operations[1]["result"]["input_id"] = "other"
    elif damage == "selector":
        operations[1]["arguments"]["value"] = "other"
    elif damage == "continuation":
        operations[1]["result"]["next_offset"] = 2
    elif damage == "missing":
        operations.pop(2)
    elif damage == "extra":
        operations.insert(1, {"label": "unaccounted", "status": "ok"})
    else:
        operations[2]["result"]["scan_errors"] = 1
    with pytest.raises(AssertionError):
        await revisions.collection_digests(operations, trial, 1, 3)


@pytest.mark.parametrize("scenario", ["full_type", "full_operands", "type", "graph"])
def test_revision_scenarios_exclude_semantically_incompatible_baseline_queries(revisions, scenario):
    assert scenario not in revisions.SCENARIOS


def test_runtime_identity_reads_back_requested_package_and_native_extension(revisions, tmp_path):
    import droidasc_mcp

    root = Path(droidasc_mcp.__file__).resolve().parent
    result = revisions.runtime_at(root.parent)
    assert result["root"] == str(root)
    assert Path(result["native"]).parent == root
    assert result["files"]["__init__.py"] == revisions.benchmark.digest(root / "__init__.py")
    with pytest.raises(subprocess.CalledProcessError):
        revisions.runtime_at(tmp_path)


@pytest.mark.anyio
@pytest.mark.parametrize("different", [False, True])
async def test_revision_run_alternates_spills_and_restores_environment(
    revisions, tmp_path, monkeypatch, different
):
    roots = {name: tmp_path / name for name in ("baseline", "candidate")}
    for root in roots.values():
        root.mkdir()
    apk = tmp_path / "fixture.apk"
    apk.write_bytes(b"original input")
    monkeypatch.setenv("PYTHONPATH", "original path")
    monkeypatch.setattr(revisions, "runtime_at", lambda root: {"root": str(root), "files": {}})
    monkeypatch.setattr(revisions, "select_cpus", lambda count: [0, 1])
    calls = []

    async def trial(args, implementation, scenario, number, report, save):
        revision = Path(os.environ["PYTHONPATH"]).name
        calls.append((number, revision))
        operations, metric = receipt(revisions, [3] if revision == "baseline" else [1, 2])
        if different and revision == "candidate":
            operations[1]["result"]["items"][0]["value"] = "different"
        metric.update(round=number, implementation=implementation, cpu_affinity_samples=1)
        metric["operations"] = operations
        report["trials"].append(metric)
        save()

    monkeypatch.setattr(revisions.benchmark, "trial", trial)
    args = SimpleNamespace(
        apk=apk,
        baseline_runtime=roots["baseline"],
        candidate_runtime=roots["candidate"],
        workers=2,
        memory_mib=4096,
        client_memory_mib=1024,
        timeout=180,
        trial_timeout=600,
        expanded_mib=128,
        session_disk_mib=8192,
        page_size=3,
        repeats=1,
        rounds=2,
        scenarios=["full_string"],
        output=tmp_path / "result.json",
    )
    if different:
        with pytest.raises(AssertionError, match="Complete rows or diagnostics"):
            await revisions.main(args)
    else:
        await revisions.main(args)
        assert calls == [(0, "baseline"), (0, "candidate"), (1, "candidate"), (1, "baseline")]
    report = json.loads(args.output.read_text())
    assert report["status"] == ("failed" if different else "passed")
    assert os.environ["PYTHONPATH"] == "original path"
    assert all("operations" not in row for row in report["trials"])
    assert len(list(args.output.with_suffix(".trials").iterdir())) == len(calls)
