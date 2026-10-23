"""Name-based method selection must resolve definitions, never guess an overload."""

from dataclasses import replace
from pathlib import Path

import pytest
from conftest import assemble_smali

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService, _normalize_dex_query


@pytest.fixture(scope="module")
def named_methods(tmp_path_factory):
    paths = assemble_smali(tmp_path_factory, ("structure", "selection"))
    service = DroidAscService(
        replace(
            Settings.from_env(),
            allowed_roots=(paths[0].parent,),
            java_executable="java-must-not-run",
            jadx_home=None,
            dexlib_home=None,
        )
    )
    opened = service.open_dex_session([str(p) for p in paths])
    assert opened["status"] == "ok", opened
    try:
        yield service, paths, opened
    finally:
        service.close()


@pytest.mark.parametrize(
    "operation",
    [
        "disassemble_method",
        "get_method_source",
        "get_method_calls",
        "find_method_refs",
        "get_call_graph",
    ],
)
@pytest.mark.parametrize("one_shot", [False, True])
def test_unique_name_matches_exact_method(named_methods, operation, one_shot):
    service, paths, opened = named_methods

    def run(**selection):
        args = dict(operation=operation, threads=1, offset=0, limit=1, **selection)
        if one_shot:
            return service.analyze_dex([str(p) for p in paths], **args)
        return service.query_dex_session(opened["session_id"], **args)

    named = run(class_name="structure.Base", method_name="numeric")
    exact = run(method_descriptor="Lstructure/Base;->numeric()I")
    assert named["status"] == exact["status"] == "ok", (named, exact)
    assert named["method_descriptor"] == "Lstructure/Base;->numeric()I"
    assert named["candidate_count"] == 1
    assert named["input_id"] == exact["input_id"] == opened["input_id"]
    assert named["sources"] == exact["sources"] == opened["sources"]
    for key in ("items", "total", "source", "nodes", "edges", "next_offset", "has_more"):
        assert named.get(key) == exact.get(key), key


def test_overloads_prototype_and_recovery(named_methods):
    service, _, opened = named_methods

    def run(**selection):
        return service.query_dex_session(
            opened["session_id"], operation="disassemble_method", offset=0, limit=1, **selection
        )

    ambiguous = run(class_name="structure.Base", method_name="text")
    assert ambiguous["status"] == "error", ambiguous
    assert ambiguous["code"] == "ambiguous_method"
    assert ambiguous["candidate_count"] == 2
    assert "list_methods" in ambiguous["message"]
    assert "items" not in ambiguous and "method_descriptor" not in ambiguous
    selected = run(
        class_name="Lstructure/Base;", method_name="text", target_descriptor="(I)Ljava/lang/String;"
    )
    assert selected["status"] == "ok", selected
    assert selected["method_descriptor"] == "Lstructure/Base;->text(I)Ljava/lang/String;"
    assert selected["items"][0]["opcode"] == "const-string/jumbo"
    assert selected["has_more"] and selected["next_offset"] == 1
    rest = service.query_dex_session(
        opened["session_id"],
        operation="disassemble_method",
        method_descriptor=selected["method_descriptor"],
        offset=1,
        limit=1,
    )
    assert rest["status"] == "ok" and rest["items"][0]["opcode"] == "return-object"
    for name, prototype in (("missing", None), ("text", "()V"), ("Text", None)):
        missing = run(class_name="structure.Base", method_name=name, target_descriptor=prototype)
        assert missing["code"] == "method_not_found", missing
        assert missing["candidate_count"] == 0
    assert run(class_name="missing.Owner", method_name="text")["code"] == "class_not_found"
    no_code = run(class_name="structure.Base", method_name="empty")
    assert no_code["status"] == "ok" and no_code["total"] == 0


@pytest.mark.parametrize(
    "selection",
    [
        {"method_name": "numeric"},
        {"class_name": "structure.Base", "method_name": ""},
        {"class_name": "structure.Base", "method_name": "num.*"},
        {"class_name": "structure.Base", "method_name": "numeric()I"},
        {"class_name": "structure.Base", "method_name": "numeric", "fuzzy_class": True},
        {"class_name": "structure.Base", "method_name": "numeric", "target_descriptor": "(V)I"},
        {
            "class_name": "structure.Base",
            "method_name": "numeric",
            "method_descriptor": "Lstructure/Base;->numeric()I",
        },
    ],
)
def test_invalid_name_selection_rejected(selection):
    with pytest.raises(ValueError):
        _normalize_dex_query({"operation": "disassemble_method", **selection})


@pytest.mark.parametrize("operation", ["info", "list_methods", "search_refs", "search_members"])
def test_name_not_silently_ignored_by_unrelated_operations(operation):
    with pytest.raises(ValueError, match="method_name"):
        _normalize_dex_query(
            {
                "operation": operation,
                "method_name": "numeric",
                "class_name": "structure.Base",
                "kind": "method",
            }
        )


def test_exact_external_references_remain_supported(named_methods):
    service, _, opened = named_methods
    external = service.query_dex_session(
        opened["session_id"],
        operation="find_method_refs",
        method_descriptor="Lexternal/Root;->external()V",
        offset=0,
        limit=1,
    )
    assert external["status"] == "ok", external


def test_ambiguous_graph_does_not_build_index(named_methods):
    original, paths, _ = named_methods
    service = DroidAscService(original.settings)
    try:
        opened = service.open_dex_session([str(p) for p in paths])
        key = opened["session_id"]
        result = service.query_dex_session(
            key,
            operation="get_call_graph",
            class_name="structure.Base",
            method_name="text",
            offset=0,
            limit=1,
        )
        assert result["code"] == "ambiguous_method", result
        root = Path(service.sessions.entries[key].storage.name)
        assert not (root / "calls.sqlite").exists()
        assert not (root / "xrefs.sqlite").exists()
        assert not service.sessions.entries[key].pages.pages
    finally:
        service.close()


@pytest.mark.parametrize("name", ["<init>", "<clinit>", "\u5904\u7406", "choose"])
def test_special_names_and_array_prototype(named_methods, name):
    service, _, opened = named_methods
    prototype = "([I[[Ljava/lang/String;)Ljava/lang/Object;" if name == "choose" else "()V"
    result = service.query_dex_session(
        opened["session_id"],
        operation="disassemble_method",
        class_name="selection.Methods",
        method_name=name,
        target_descriptor=prototype,
        offset=0,
        limit=100,
    )
    assert result["status"] == "ok", result
    assert result["method_descriptor"] == f"Lselection/Methods;->{name}{prototype}"
    assert result["dex_entry"] == "classes2.dex"


def test_resolution_checks_only_owning_snapshot_and_rejects_directory_disagreement(
    named_methods,
    monkeypatch,
):
    from contextlib import contextmanager

    from droidasc_mcp import native_snapshot
    from droidasc_mcp.native_structure import resolve_method
    from droidasc_mcp.worker_errors import DroidAscError

    service, _, opened = named_methods
    bundle = Path(service.sessions.entries[opened["session_id"]].storage.name) / "analysis.apk"
    original = native_snapshot.query_dex
    calls = []

    @contextmanager
    def checked(bundle, archive, info):
        calls.append(info.filename)
        with original(bundle, archive, info) as dex:
            yield dex

    monkeypatch.setattr(native_snapshot, "query_dex", checked)
    result = resolve_method(bundle, "classes2.dex", "Lselection/Methods;", "<init>")
    assert result["status"] == "ok" and calls == ["classes2.dex"]
    with pytest.raises(DroidAscError, match="directory disagrees"):
        resolve_method(bundle, "classes.dex", "Lselection/Methods;", "<init>")
    missing = service.query_dex_session(
        opened["session_id"],
        operation="get_method_calls",
        class_name="structure.Child",
        method_name="text",
        offset=0,
        limit=100,
    )
    assert missing["code"] == "method_not_found", missing
