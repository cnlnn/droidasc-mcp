"""Uncached/cached equivalence covers more than a matching count or sorted set."""

import copy
import importlib.util
from dataclasses import replace
from pathlib import Path

import pytest


@pytest.fixture
def parity(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "selected_set_parity", scripts / "verify_selected_set_parity.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "damage", [None, "order", "duplicate", "diagnostic", "missing", "unknown", "context"]
)
def test_semantics_check_order_duplicates_fields_and_context(parity, damage):
    expected = {
        "status": "ok",
        "items": [{"offset": 3}, {"offset": 7}, {"offset": 7}],
        "total": 3,
        "scan_errors": 0,
        "reference_semantics": "explicit_type_operand",
    }
    opened = {"session_id": "session", "input_id": "original", "sources": [{"sha256": "hash"}]}
    actual = copy.deepcopy({**expected, **opened})
    if damage == "order":
        actual["items"].reverse()
    elif damage == "duplicate":
        actual["items"] = [{"offset": 3}, {"offset": 3}, {"offset": 7}]
    elif damage == "diagnostic":
        actual["scan_errors"] = 1
    elif damage == "missing":
        actual.pop("reference_semantics")
    elif damage == "unknown":
        actual["new_field"] = "unverified"
    elif damage == "context":
        actual["sources"][0]["sha256"] = "different"
    if damage:
        with pytest.raises(AssertionError):
            parity.compare_semantics(expected, actual, opened)
    else:
        assert parity.compare_semantics(expected, actual, opened) == parity.fingerprint(expected)


@pytest.mark.parametrize("damage", [None, "partial", "offset", "error", "count", "continuation"])
def test_uncached_oracle_requires_complete_success(parity, damage):
    result = {
        "status": "ok",
        "items": [{"value": "x"}],
        "total": 1,
        "instruction_scan_complete": True,
        "scan_errors": 0,
        "offset": 0,
        "limit": 1000,
        "has_more": False,
        "truncated": False,
        "next_offset": None,
    }
    if damage:
        key, value = {
            "partial": ("instruction_scan_complete", False),
            "offset": ("offset", 1),
            "error": ("scan_errors", 1),
            "count": ("total", 2),
            "continuation": ("next_offset", 1),
        }[damage]
        result[key] = value
        with pytest.raises(AssertionError):
            parity.semantic_result(result)
    else:
        assert parity.semantic_result(result) == {
            k: v
            for k, v in result.items()
            if k in {"status", "items", "total", "instruction_scan_complete", "scan_errors"}
        }


@pytest.mark.parametrize(
    "damage", [None, "runtime", "apk", "helper", "duplicate", "missing", "collection", "repeat"]
)
def test_receipt_identity_and_inventory_are_mandatory(parity, damage):
    helpers = {name: name for name in parity.HELPERS}
    receipt = {
        "status": "passed",
        "input_unchanged": True,
        "runtime_unchanged": True,
        "apk_sha256": "apk",
        "ours_runtime_sha256": {"native_types.py": "current"},
        "harness_sha256": helpers["benchmark_competitor_runtime.py"],
        "cpu_wrapper_sha256": helpers["benchmark_cpu_wrapper.py"],
        "repeats": 2,
        "full_collection_page_size": 1000,
        "trials": [
            {
                "round": 0,
                "scenario": "full_operands",
                "implementation": impl,
                "status": "passed",
                "reference_collections": [
                    {"label": f"query:{r}:{i}"} for r in range(2) for i in range(2)
                ],
            }
            for impl in ("ours", "competitor")
        ],
    }
    if damage == "runtime":
        receipt["ours_runtime_sha256"] = {}
    elif damage == "apk":
        receipt["apk_sha256"] = "different"
    elif damage == "helper":
        receipt["harness_sha256"] = "different"
    elif damage == "duplicate":
        receipt["trials"].append(copy.deepcopy(receipt["trials"][0]))
    elif damage == "missing":
        receipt["trials"].pop()
    elif damage == "collection":
        receipt["trials"][0]["reference_collections"].pop()
    elif damage == "repeat":
        receipt["repeats"] = 1
    if damage:
        with pytest.raises(AssertionError):
            parity.validate_receipt(receipt, "apk", {"native_types.py": "current"}, helpers)
    else:
        parity.validate_receipt(receipt, "apk", {"native_types.py": "current"}, helpers)


@pytest.mark.parametrize("scope", [None, "unknown", "exact_query_page", "selected_reference_set"])
def test_repeated_collection_requires_actual_cache_evidence(parity, scope):
    result = {"query_cache": {"scope": scope, "hit": True}} if scope else {}
    operations = [{"label": "page", "result": result}]
    collection = {"label": "query:1:0", "page_labels": ["page"]}
    if scope in {None, "unknown"}:
        with pytest.raises(AssertionError):
            parity.cache_evidence(operations, collection)
    else:
        assert parity.cache_evidence(operations, collection)[scope] == 1


@pytest.mark.anyio
@pytest.mark.parametrize("kind", ["string", "type"])
async def test_real_fixture_uncached_scan_matches_complete_cached_service(
    parity, kind, smali_dex_files, string_reference_dex_files, settings, tmp_path
):
    import zipfile

    from droidasc_mcp.service import DroidAscService

    bundle = tmp_path / "original.apk"
    with zipfile.ZipFile(bundle, "w") as output:
        for i, path in enumerate([*smali_dex_files, *string_reference_dex_files]):
            output.write(path, "classes.dex" if i == 0 else f"classes{i + 1}.dex")
    tool, params = parity.benchmark.queries("ours", "offline", kind, "unused", 3)[0]
    params["value" if kind == "string" else "type_descriptor"] = (
        "https://" if kind == "string" else "Lfixture/Target;"
    )
    query = {k: v for k, v in params.items() if k != "session_id"}
    query.update(offset=0, limit=2**31 - 1)
    scan = parity.query_strings if kind == "string" else parity.query_types
    expected = parity.semantic_result(
        scan(replace(settings, max_page_size=2**31 - 1), bundle, query)
    )
    assert expected["total"] > 1
    service = DroidAscService(replace(settings, allowed_roots=(tmp_path,)))
    try:
        opened = service.open_artifact_session(
            str(bundle), max_uncompressed_bytes=settings.max_apk_bytes
        )
        assert opened["status"] == "ok", opened
        params["session_id"] = opened["session_id"]
        operations = []

        async def call(label, tool, arguments, **kwargs):
            result = service.query_dex_session(**arguments)
            operations.append({"label": label, "result": result})
            return result

        for repeat in range(2):
            result, labels, _ = await parity.benchmark.collect_reference_pages(
                call, "ours", tool, params, f"query:{repeat}:0", 1
            )
            parity.compare_semantics(expected, result, opened)
            counts = parity.cache_evidence(
                operations, {"label": f"query:{repeat}:0", "page_labels": labels}
            )
            assert counts["selected_reference_set"] > 0 if repeat == 0 else sum(counts.values()) > 0
    finally:
        service.close()
