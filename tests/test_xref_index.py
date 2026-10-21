"""Persistent index parity and transactional failure checks with independent Smali inputs."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService, _normalize_dex_query


def session_query(service, key, **args):
    return service.query_dex_session(key, **{"offset": 0, "limit": 1000, **args})


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
        ignored = {"backend", "index"}
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
    with sqlite3.connect(index) as db:
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


@pytest.mark.parametrize(
    "descriptor", [None, "Target", "V", "[V", "LTarget", "Lfoo.Bar;", "LTarget;->f:I"]
)
def test_type_query_requires_exact_identity(descriptor):
    with pytest.raises(ValueError, match="type_descriptor"):
        _normalize_dex_query({"operation": "find_type_refs", "type_descriptor": descriptor})
