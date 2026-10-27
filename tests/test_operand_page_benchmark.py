"""Operand receipt acceptance must reject incomplete or altered transport evidence."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def verifier(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "operand_page_verifier", scripts / "verify_operand_page_benchmark.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("kind", ["string", "type"])
@pytest.mark.parametrize("damage", [None, "offset", "entry", "unit", "duplicate"])
def test_native_sites_retain_identity_and_duplicates(verifier, kind, damage):
    sources = [{"dex_entry": "classes.dex", "container_entry": "classes10.dex"}]
    row = {
        "dex_entry": "classes.dex",
        "caller": "LA;->m()V",
        "value": "https://x",
        "type_descriptor": "Ljava/lang/String;",
        "offset_unit": "code_units_from_method_start",
        "instruction_offset": 3,
        "opcode": "const-string" if kind == "string" else "const-class",
    }
    expected = [
        (
            "classes10.dex",
            "LA;->m()V",
            row["value" if kind == "string" else "type_descriptor"],
            6,
            row["opcode"],
        )
    ]
    if damage == "offset":
        row["instruction_offset"] = -1
    elif damage == "entry":
        row["dex_entry"] = "missing.dex"
    elif damage == "unit":
        row["offset_unit"] = "bytes"
    if damage in {"offset", "entry", "unit"}:
        with pytest.raises((AssertionError, KeyError)):
            verifier.native_sites([row], sources, kind)
    else:
        actual = verifier.native_sites([row] * (2 if damage else 1), sources, kind)
        comparison = verifier.compare_sites(expected, actual)
        assert comparison["status"] == ("failed" if damage else "passed")
        assert comparison["extra_sites"] == int(damage == "duplicate")


@pytest.mark.anyio
@pytest.mark.parametrize(
    "damage", [None, "provenance", "diagnostic", "arguments", "missing", "extra", "label"]
)
async def test_receipt_replay_checks_each_attempt(verifier, damage):
    opened = {"session_id": "s", "input_id": "i", "artifact_sha256": "a", "sources": []}
    tool, params = verifier.queries("ours", "s", "string", verifier.GRAPH_ROOT, 3)[0]
    label = "query:0:0:page:0:attempt:0"
    response = {
        **opened,
        "status": "ok",
        "items": [],
        "total": 0,
        "offset": 0,
        "limit": 1,
        "has_more": False,
        "truncated": False,
        "next_offset": None,
        "scanned_methods": 1,
        "scanned_instructions": 2,
        "methods_without_code": 0,
        "scan_errors": 0,
        "instruction_scan_complete": True,
    }
    operation = {
        "label": label,
        "tool": tool,
        "arguments": {**params, "limit": 1, "offset": 0},
        "status": "ok",
        "result": response,
    }
    operations = [operation]
    collection = {"label": "query:0:0", "page_labels": [label], "response_limit_recoveries": []}
    diagnostics = {
        "scanned_methods": 1,
        "scanned_instructions": 2,
        "methods_without_code": 0,
        "scan_errors": 0,
        "instruction_scan_complete": True,
    }
    if damage == "provenance":
        response["input_id"] = "different"
    elif damage == "diagnostic":
        response["scanned_instructions"] = 3
    elif damage == "arguments":
        operation["arguments"]["value"] = "different"
    elif damage == "missing":
        operations = []
    elif damage == "extra":
        operations.append(dict(operation))
    elif damage == "label":
        collection["page_labels"] = ["fabricated"]
    if damage:
        with pytest.raises((AssertionError, RuntimeError)):
            await verifier.replay(operations, collection, "ours", opened, "string", 1, diagnostics)
    else:
        result = await verifier.replay(
            operations, collection, "ours", opened, "string", 1, diagnostics
        )
        assert result["items"] == []


@pytest.mark.parametrize("damage", [None, "missing", "duplicate", "unexpected"])
def test_collection_inventory_covers_every_repeat(verifier, damage):
    collections = [{"label": f"query:{repeat}:{i}"} for repeat in range(2) for i in range(2)]
    if damage == "missing":
        collections.pop()
    elif damage == "duplicate":
        collections[-1] = collections[0]
    elif damage == "unexpected":
        collections[-1] = {"label": "query:2:0"}
    trial = {"scenario": "full_operands", "reference_collections": collections}
    if damage:
        with pytest.raises(AssertionError):
            verifier.collection_kinds(trial, 2)
    else:
        assert [kind for _, kind in verifier.collection_kinds(trial, 2)] == ["string", "type"] * 2


@pytest.mark.parametrize("kind", ["string", "type"])
@pytest.mark.parametrize(
    "damage", [None, "offset", "entry", "access", "target", "empty", "duplicate"]
)
def test_competitor_sites_verify_evidence_not_group_counts(verifier, kind, damage):
    target = "https://x" if kind == "string" else "Ljava/lang/String;"
    evidence = {
        "offset": 6,
        "opcode": "const-string" if kind == "string" else "const-class",
        "access": "load" if kind == "string" else "type-use",
        "target_value": target if kind == "string" else None,
        "target_descriptor": target if kind == "type" else None,
    }
    row = {
        "dex_name": "classes10.dex",
        "match_type": kind,
        "method_class": "LA;",
        "method_name": "m",
        "method_descriptor": "()V",
        "evidence": [evidence],
    }
    sources = [{"container_entry": "classes10.dex"}]
    expected = [("classes10.dex", "LA;->m()V", target, 6, evidence["opcode"])]
    if damage == "offset":
        evidence["offset"] = 3
    elif damage == "entry":
        row["dex_name"] = "missing.dex"
    elif damage == "access":
        evidence["access"] = "read"
    elif damage == "target":
        evidence["target_value" if kind == "string" else "target_descriptor"] = None
    elif damage == "empty":
        row["evidence"] = []
    elif damage == "duplicate":
        row["evidence"].append(dict(evidence))
    if damage not in {None, "duplicate"}:
        with pytest.raises(AssertionError):
            verifier.competitor_sites([row], sources, kind)
    else:
        actual = verifier.competitor_sites([row], sources, kind)
        comparison = verifier.compare_sites(expected, actual)
        assert comparison["status"] == ("failed" if damage else "passed")
        assert comparison["extra_sites"] == int(damage == "duplicate")
