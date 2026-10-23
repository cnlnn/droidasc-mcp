"""Full-page evidence rejects equal-count corruptions and continuation failures."""

import asyncio
import hashlib
import importlib
import json
import subprocess
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def verifier(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("verify_mcp_reference_pages")


@pytest.mark.parametrize("count", [0, 1, 2, 5])
def test_all_reference_pages_and_scan_diagnostics(verifier, count):
    expected = {
        "status": "ok",
        "items": [{"site": i} for i in range(count)],
        "total": count,
        "scanned_instructions": 42,
        "scan_errors": 0,
        "instruction_scan_complete": True,
    }
    offsets = []

    async def call(**query):
        offset = query["offset"]
        offsets.append(offset)
        rows = expected["items"][offset : offset + 2]
        more = offset + len(rows) < count
        return {
            **expected,
            "items": rows,
            "offset": offset,
            "limit": 2,
            "has_more": more,
            "truncated": more,
            "next_offset": offset + 2 if more else None,
        }

    result = asyncio.run(
        verifier.verify_pages(call, {"operation": "find_method_refs"}, expected, 2)
    )
    assert result["status"] == "passed" and result["total"] == count
    assert offsets == list(range(0, max(1, count), 2))
    assert result["full_result_sha256"] == verifier.fingerprint(expected)


@pytest.mark.parametrize(
    "failure",
    [
        "rows",
        "order",
        "diagnostics",
        "total",
        "offset",
        "limit",
        "empty",
        "continuation",
        "more",
        "truncated",
    ],
)
def test_equal_counts_do_not_approve_wrong_reference_content(verifier, failure):
    expected = {
        "status": "ok",
        "items": [{"site": i} for i in range(3)],
        "total": 3,
        "scanned_instructions": 42,
        "scan_errors": 0,
        "instruction_scan_complete": True,
    }

    async def call(**query):
        result = {
            **expected,
            "items": expected["items"][:2],
            "offset": 0,
            "limit": 2,
            "has_more": True,
            "truncated": True,
            "next_offset": 2,
        }
        if failure == "rows":
            result["items"] = [{"site": 0}, {"site": 99}]
        elif failure == "order":
            result["items"] = list(reversed(result["items"]))
        elif failure == "diagnostics":
            result["scanned_instructions"] += 1
        elif failure in {"total", "offset", "limit"}:
            result[failure] += 1
        elif failure == "empty":
            result["items"] = []
            result["next_offset"] = 0
        elif failure == "continuation":
            result["next_offset"] = 3
        else:
            result["has_more" if failure == "more" else "truncated"] = False
        return result

    with pytest.raises(AssertionError):
        asyncio.run(verifier.verify_pages(call, {}, expected, 2))


def test_response_limit_recovery_keeps_every_row_and_the_current_offset(verifier):
    expected = {
        "status": "ok",
        "items": [{"site": i} for i in range(7)],
        "total": 7,
        "scanned_instructions": 42,
    }
    attempts = []

    async def call(**query):
        offset, limit = query["offset"], query["limit"]
        attempts.append((offset, limit))
        if limit > (2 if offset == 0 else 1):
            return {"status": "error", "code": "response_limit"}
        rows = expected["items"][offset : offset + limit]
        more = offset + len(rows) < expected["total"]
        return {
            **expected,
            "items": rows,
            "offset": offset,
            "limit": limit,
            "has_more": more,
            "truncated": more,
            "next_offset": offset + limit if more else None,
        }

    result = asyncio.run(verifier.verify_pages(call, {}, expected, 8))
    assert attempts[:5] == [(0, 8), (0, 4), (0, 2), (2, 2), (2, 1)]
    assert [page["offset"] for page in result["pages"]] == [0, 2, 3, 4, 5, 6]
    assert result["total"] == 7 and len(result["response_limit_recoveries"]) == 3


@pytest.mark.parametrize("failure", ["response_limit", "invalid_dex"])
def test_unrecoverable_errors_are_not_accepted_as_empty_results(verifier, failure):
    async def call(**query):
        return {"status": "error", "code": failure}

    with pytest.raises(AssertionError):
        asyncio.run(verifier.verify_pages(call, {}, {"items": [], "total": 0}, 1))


@pytest.mark.parametrize("failed", [False, True])
def test_oracle_command_and_implementation_metadata(verifier, monkeypatch, tmp_path, failed):
    home = tmp_path / "oracle"
    (home / "lib").mkdir(parents=True)
    jar = home / "lib" / "scanner.jar"
    jar.write_bytes(b"acceptance jar")
    args = SimpleNamespace(
        oracle_home=home,
        java=tmp_path / "java",
        baseline_source=tmp_path / "Frozen.java",
        oracle_heap_mib=1024,
    )
    expected = {
        "status": "ok",
        "instruction_scan_complete": True,
        "total": 0,
        "items": [],
        "scanned_instructions": 42,
        "scan_errors": 0,
    }

    def run(command, **kwargs):
        assert command[0:2] == [str(args.java), "-Xmx1024m"]
        assert command[command.index("-cp") + 1] == str(jar)
        assert command[-10:] == [
            str(args.baseline_source),
            str(tmp_path / "bundle.apk"),
            "",
            "",
            "find_field_refs",
            "Lx/C;->f:I",
            "auto",
            "0",
            str(2**31 - 1),
            "all",
        ]
        assert kwargs == {"capture_output": True, "check": False, "timeout": 180}
        payload = {**expected, "backend": "independent scanner", "backend_version": "different"}
        return subprocess.CompletedProcess(
            command,
            int(failed),
            stdout=json.dumps(payload).encode(),
            stderr=b"scanner heap diagnostic",
        )

    monkeypatch.setattr(verifier.subprocess, "run", run)
    if failed:
        with pytest.raises(AssertionError, match="scanner heap diagnostic"):
            verifier.oracle(args, tmp_path / "bundle.apk", "find_field_refs", "Lx/C;->f:I")
    else:
        assert (
            verifier.oracle(args, tmp_path / "bundle.apk", "find_field_refs", "Lx/C;->f:I")
            == expected
        )


@pytest.mark.parametrize("failure", [None, "hash", "size", "duplicate", "unsafe", "budget"])
def test_oracle_bundle_uses_exact_original_bytes(verifier, tmp_path, failure):
    apk, bundle = tmp_path / "input.apk", tmp_path / "oracle.apk"
    data = b"original instruction bytes" * 30000
    first = b"first DEX"
    with zipfile.ZipFile(apk, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("classes.dex", first)
        archive.writestr("classes10.dex", data)
    original = apk.read_bytes()
    row = {
        "dex_entry": "classes2.dex",
        "container_entry": "classes10.dex",
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    if failure == "hash":
        row["sha256"] = "0" * 64
    elif failure == "size":
        row["size_bytes"] -= 1
    elif failure == "unsafe":
        row["container_entry"] = "../classes10.dex"
    rows = [
        {
            "dex_entry": "classes.dex",
            "container_entry": "classes.dex",
            "size_bytes": len(first),
            "sha256": hashlib.sha256(first).hexdigest(),
        },
        *([row] * (2 if failure == "duplicate" else 1)),
    ]
    limit = len(data) + len(first) - (1 if failure == "budget" else 0)
    if failure:
        with pytest.raises(AssertionError):
            verifier.original_bundle(apk, bundle, rows, limit)
    else:
        verifier.original_bundle(apk, bundle, rows, limit)
        with zipfile.ZipFile(bundle) as archive:
            assert archive.namelist() == ["classes.dex", "classes2.dex"]
            assert archive.read("classes.dex") == first
            assert archive.read("classes2.dex") == data
    assert apk.read_bytes() == original


@pytest.mark.parametrize("failure", ["missing_dex", "swapped_canonical_entries"])
def test_oracle_inventory_is_independent_of_the_session_selection(verifier, tmp_path, failure):
    apk, bundle = tmp_path / "input.apk", tmp_path / "oracle.apk"
    originals = {"classes.dex": b"first bytes", "classes2.dex": b"second bytes"}
    with zipfile.ZipFile(apk, "w") as archive:
        for name, data in originals.items():
            archive.writestr(name, data)
    sources = [
        {
            "dex_entry": name,
            "container_entry": name,
            "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        for name, data in originals.items()
    ]
    if failure == "missing_dex":
        sources.pop()
    else:
        sources[0]["dex_entry"], sources[1]["dex_entry"] = (
            sources[1]["dex_entry"],
            sources[0]["dex_entry"],
        )
    with pytest.raises(AssertionError):
        verifier.original_bundle(apk, bundle, sources, 1024)
