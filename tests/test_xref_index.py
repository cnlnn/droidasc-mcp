"""Persistent index parity and transactional failure checks with independent Smali inputs."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService, _normalize_dex_query


def session_query(service, key, **args):
    return service.query_dex_session(key, **{"offset": 0, "limit": 1000, **args})


def test_field_opcode_bytes_in_payload_and_adjacent_header_are_not_references(boundary_dex_file):
    settings = replace(Settings.from_env(), allowed_roots=(boundary_dex_file.parent,))
    service = DroidAscService(settings)
    try:
        key = service.open_dex_session([str(boundary_dex_file)])["session_id"]

        def check():
            result = session_query(
                service,
                key,
                operation="find_field_refs",
                field_descriptor="Lfixture/Boundary;->value:I",
            )
            assert result["status"] == "ok", result
            assert result["instruction_scan_complete"]
            assert result["total"] == 1
            assert [
                (r["caller"], r["instruction_offset"], r["opcode"]) for r in result["items"]
            ] == [("Lfixture/Boundary;->dReal()I", 0, "sget")]

        check()
        built = session_query(service, key, operation="build_xref_index")
        assert built["status"] == "ok", built
        check()
    finally:
        service.close()


@pytest.fixture
def indexed_service(smali_dex_files):
    settings = replace(
        Settings.from_env(), allowed_roots=(smali_dex_files[0].parent,), timeout_seconds=120
    )
    service = DroidAscService(settings)
    yield service
    service.close()


def test_index_parity_and_type_oracle(indexed_service, smali_dex_files):
    service = indexed_service
    opened = service.open_dex_session(list(map(str, smali_dex_files)))
    key = opened["session_id"]
    root = Path(service.sessions.entries[key].storage.name)

    def query(operation, **args):
        result = session_query(service, key, operation=operation, **args)
        assert result["status"] == "ok", result
        return result

    requests = [
        ("find_method_refs", {"method_descriptor": "Lfixture/Target;->pick(I)V"}),
        ("get_method_calls", {"method_descriptor": "Lfixture/Caller;->run()V"}),
        (
            "get_method_calls",
            {"method_descriptor": "Lfixture/Caller;->dynamic(Ljava/lang/invoke/MethodHandle;)V"},
        ),
        ("find_field_refs", {"field_descriptor": "Lfixture/Target;->value:I"}),
        (
            "find_field_refs",
            {"field_descriptor": "Lexternal/Missing;->value:I", "field_access": "write"},
        ),
    ]
    baselines = [query(op, **args) for op, args in requests]
    built = query("build_xref_index")
    assert built["index"]["reused"] is False
    assert built["edge_counts"]["type"] > 0
    assert built["index"]["persistence"] == "session_lifetime"
    index = root / "xrefs.sqlite"
    digest = hashlib.sha256(index.read_bytes()).hexdigest()
    for (op, args), expected in zip(requests, baselines, strict=True):
        actual = query(op, **args)
        assert actual["index"]["reused"] is True
        ignored = {"backend", "index", "query_cache"}
        assert {k: v for k, v in actual.items() if k not in ignored} == {
            k: v for k, v in expected.items() if k not in ignored
        }
    target = "Lfixture/Target;"
    declarations = query("find_type_refs", type_descriptor=target, type_relation="declaration")
    assert {(r["source"], r["detail"]) for r in declarations["items"]} == {
        ("Lfixture/Types;->member:Lfixture/Target;", "field_type"),
        ("Lfixture/Types;->typed(Lfixture/Target;[Lfixture/Target;)Lfixture/Target;", "return"),
        (
            "Lfixture/Types;->typed(Lfixture/Target;[Lfixture/Target;)Lfixture/Target;",
            "parameter:0",
        ),
        ("Lfixture/Caller;->fields(Lfixture/Target;)V", "parameter:0"),
    }
    annotations = query("find_type_refs", type_descriptor=target, type_relation="annotation")
    assert annotations["total"] == 5
    assert {r["detail"] for r in annotations["items"]} == {
        "class:Lexternal/Mark;.value",
        "class:Lexternal/Mark;.nested.types[0]",
        "field:Lexternal/Mark;.value",
        "method:Lexternal/Mark;.value",
        "parameter:0:Lexternal/Mark;.value",
    }
    instructions = query("find_type_refs", type_descriptor=target, type_relation="instruction")
    typed = [r for r in instructions["items"] if r["source"].startswith("Lfixture/Types;")]
    assert [(r["detail"], r["instruction_offset"]) for r in typed] == [
        ("const-class", 0),
        ("check-cast", 2),
    ]
    arrays = query("find_type_refs", type_descriptor="[Lfixture/Target;")
    assert arrays["total"] == 3
    assert all(r["target_resolution"] == "not_defined_in_input" for r in arrays["items"])
    assert all(r["target_dex_entry"] == "classes2.dex" for r in annotations["items"])
    for name, detail in [("Base", "superclass"), ("Contract", "interface")]:
        rows = query("find_type_refs", type_descriptor=f"Lexternal/{name};")["items"]
        assert len(rows) == 1 and rows[0]["detail"] == detail
    page = query(
        "find_type_refs", type_descriptor=target, type_relation="annotation", limit=2, offset=1
    )
    assert page["items"] == annotations["items"][1:3] and page["next_offset"] == 3
    assert query("find_type_refs", type_descriptor="Lmissing/Unknown;")["total"] == 0
    found = query("search_members", kind="method", value="->pick(")
    assert found["items"] == [
        {"kind": "method", "descriptor": descriptor, "dex_entry": "classes2.dex"}
        for descriptor in (
            "Lfixture/Target;->pick(I)V",
            "Lfixture/Target;->pick(Ljava/lang/String;)V",
        )
    ]
    assert query("search_members", kind="method", value="->PICK(")["total"] == 0
    assert query("search_members", kind="method", value="%_")["total"] == 0
    page = query("search_members", kind="method", value="->pick(", limit=1)
    assert page["has_more"] and page["next_offset"] == 1
    assert (
        query("search_members", kind="method", value="->pick(", offset=1)["items"]
        == found["items"][1:]
    )
    for member in found["items"]:
        assert query("find_method_refs", method_descriptor=member["descriptor"])["total"] > 0
    fields = query("search_members", kind="field", value="value:", class_name="fixture.Target")
    assert {r["descriptor"] for r in fields["items"]} == {
        "Lfixture/Target;->value:I",
        "Lfixture/Target;->value:J",
    }
    assert (
        query("search_members", kind="field", value="[Ljava/lang/String;")["items"][0]["descriptor"]
        == "Lfixture/Target;->names:[Ljava/lang/String;"
    )
    assert hashlib.sha256(index.read_bytes()).hexdigest() == digest
    service.sessions.close(key)
    assert not root.exists()


def test_concurrent_index_build_and_identity(indexed_service, smali_dex_files):
    service = indexed_service
    key = service.open_dex_session(list(map(str, smali_dex_files)))["session_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(session_query, service, key, operation="build_xref_index") for _ in range(2)
        ]
        results = [f.result() for f in futures]
    assert all(r["status"] == "ok" for r in results), results
    assert sorted(r["index"]["reused"] for r in results) == [False, True]
    import sqlite3

    index = Path(service.sessions.entries[key].storage.name) / "xrefs.sqlite"
    with closing(sqlite3.connect(index)) as db, db:
        db.execute("UPDATE metadata SET value='stale' WHERE key='backend_id'")
    result = session_query(service, key, operation="build_xref_index")
    assert result["code"] == "index_identity_changed"


def test_index_disk_quota_does_not_publish(indexed_service, smali_dex_files):
    service = indexed_service
    service.runner.settings = replace(service.runner.settings, max_xref_index_bytes=4096)
    key = service.open_dex_session(list(map(str, smali_dex_files)))["session_id"]
    result = session_query(service, key, operation="build_xref_index")
    assert result["status"] == "error", result
    assert not (Path(service.sessions.entries[key].storage.name) / "xrefs.sqlite").exists()
    assert session_query(service, key, operation="info")["status"] == "ok"


def test_discovery_without_index_and_cached_references(indexed_service, smali_dex_files):
    service = indexed_service
    key = service.open_dex_session(list(map(str, smali_dex_files)))["session_id"]
    root = Path(service.sessions.entries[key].storage.name)

    def query(**args):
        result = session_query(service, key, **args)
        assert result["status"] == "ok", result
        return result

    requests = [
        {"operation": "search_members", "kind": "method", "value": "->pick("},
        {"operation": "search_members", "kind": "field", "value": "", "limit": 2, "offset": 1},
        {
            "operation": "search_members",
            "kind": "field",
            "value": "value:",
            "class_name": "fixture.Target",
        },
        {"operation": "search_members", "kind": "method", "value": "->PICK("},
        {"operation": "search_members", "kind": "method", "value": "%_"},
        {"operation": "search_members", "kind": "method", "value": "", "offset": 2**64},
    ]
    baselines = [query(**request) for request in requests]
    assert baselines[0]["items"] == [
        {"kind": "method", "descriptor": descriptor, "dex_entry": "classes2.dex"}
        for descriptor in (
            "Lfixture/Target;->pick(I)V",
            "Lfixture/Target;->pick(Ljava/lang/String;)V",
        )
    ]
    assert baselines[1]["has_more"]
    assert baselines[2]["total"] == 2
    assert baselines[3]["total"] == baselines[4]["total"] == 0
    assert baselines[5]["items"] == [] and not baselines[5]["has_more"]
    assert not (root / "xrefs.sqlite").exists()
    for request in [
        requests[0],
        {"operation": "find_method_refs", "method_descriptor": "Lfixture/Target;->pick(I)V"},
    ]:
        original = query(**request)
        repeat = query(**request)
        assert repeat["query_cache"]["hit"]
        assert {k: v for k, v in original.items() if k != "query_cache"} == {
            k: v for k, v in repeat.items() if k != "query_cache"
        }
    string = query(operation="search_strings", value="STRING_ARGUMENT")
    assert string["total"] == 1 and not string["instruction_scan_complete"]
    assert string["scope"] == "string_pool_in_supplied_files"
    assert string["items"][0]["value"] == "STRING_ARGUMENT"
    assert string["items"][0]["dex_entry"] == "classes.dex"
    assert isinstance(string["items"][0]["string_index"], int)
    # A source-file name lives in the pool without a const-string use site.
    assert query(operation="search_strings", value="Caller.java")["total"] == 1
    assert query(operation="search_strings", value="string_argument")["total"] == 0
    assert query(operation="search_strings", value="%_")["total"] == 0
    assert not (root / "xrefs.sqlite").exists()
    assert service.sessions.entries[key].pages.used > 0
    # Native read-only queries use bounded resident pages, not shared disk-page writes.
    assert not list((root / "query-cache").glob("*.json"))
    query(operation="build_xref_index")
    assert not list((root / "query-cache").glob("*.json"))
    for request, baseline in zip(requests, baselines, strict=True):
        actual = query(**request)
        ignored = {"backend", "index", "query_cache"}
        assert {k: v for k, v in actual.items() if k not in ignored} == {
            k: v for k, v in baseline.items() if k not in ignored
        }


@pytest.mark.parametrize(
    "args", [{}, {"value": ""}, {"value": "x", "class_name": "fixture.Caller"}]
)
def test_string_pool_query_validation(args):
    with pytest.raises(ValueError, match="search_strings"):
        _normalize_dex_query({"operation": "search_strings", **args})


@pytest.mark.parametrize(
    "descriptor", [None, "Target", "V", "[V", "LTarget", "Lfoo.Bar;", "LTarget;->f:I"]
)
def test_type_query_requires_exact_identity(descriptor):
    with pytest.raises(ValueError, match="type_descriptor"):
        _normalize_dex_query({"operation": "find_type_refs", "type_descriptor": descriptor})
