"""Explicit DEX type operands are distinct from broader static type relations."""

import struct
from dataclasses import replace
from pathlib import Path

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService


def test_operand_scope_and_complete_result_reuse(smali_dex_files, monkeypatch):
    service = DroidAscService(
        replace(
            Settings.from_env(),
            allowed_roots=(smali_dex_files[0].parent,),
            java_executable="must-not-run",
            jadx_home=None,
        )
    )
    try:
        opened = service.open_dex_session([str(p) for p in smali_dex_files])
        assert opened["status"] == "ok", opened
        key = opened["session_id"]
        query = {
            "operation": "find_type_refs",
            "type_descriptor": "Lfixture/Target;",
            "type_relation": "operand",
            "offset": 0,
            "limit": 1,
        }
        first = service.query_dex_session(key, **query)
        assert first["status"] == "ok" and first["total"] == 2, first
        assert first["reference_semantics"] == "explicit_type_operand"
        assert "index" not in first
        root = service.sessions.entries[key].storage.name
        assert not (Path(root) / "xrefs.sqlite").exists()
        assert not (Path(root) / "calls.sqlite").exists()

        def rescan(*args, **kwargs):
            pytest.fail("Operand pages must reuse the complete selected set")

        monkeypatch.setattr(service.runner, "query_dex_session", rescan)
        second = service.query_dex_session(key, **{**query, "offset": 1, "limit": 2})
        assert second["query_cache"]["scope"] == "selected_reference_set"
        assert not second["has_more"]
        rows = first["items"] + second["items"]
        assert [(r["type_descriptor"], r["opcode"], r["instruction_offset"]) for r in rows] == [
            ("Lfixture/Target;", "const-class", 0),
            ("Lfixture/Target;", "check-cast", 2),
        ]
        assert all(r["dex_entry"] == "classes.dex" for r in rows)
        assert all(r["caller"].startswith("Lfixture/Types;->typed(") for r in rows)
    finally:
        service.close()


@pytest.mark.parametrize("target", ["Lfixture/Target;", "Lmissing/Nothing;"])
@pytest.mark.parametrize("indexed", [False, True])
def test_operand_routing_never_builds_or_restores_index(
    smali_dex_files, tmp_path, monkeypatch, target, indexed
):
    from types import SimpleNamespace

    from droidasc_mcp import native_index, xref_index
    from droidasc_mcp.dex_worker import query_prepared
    from droidasc_mcp.durable_index import DurableIndexes

    settings = replace(Settings.from_env(), allowed_roots=(smali_dex_files[0].parent,))
    service = DroidAscService(settings)
    try:
        key = service.open_dex_session([str(p) for p in smali_dex_files])["session_id"]
        root = Path(service.sessions.entries[key].storage.name)
        if indexed:
            broad = service.query_dex_session(
                key,
                operation="find_type_refs",
                type_descriptor="Lfixture/Target;",
                type_relation="instruction",
                offset=0,
                limit=100,
            )
            assert broad["status"] == "ok" and broad["total"] == 10
            assert (root / "xrefs.sqlite").exists()

        def unexpected(*args, **kwargs):
            pytest.fail("Operand queries must not enter index lookup, build or restore")

        monkeypatch.setattr(xref_index, "query_index", unexpected)
        monkeypatch.setattr(native_index, "build", unexpected)
        monkeypatch.setattr(DurableIndexes, "restore", unexpected)
        runner = SimpleNamespace(
            settings=replace(settings, xref_cache_dir=tmp_path),
            reference_spool=None,
        )
        result = query_prepared(
            runner,
            root / "analysis.apk",
            {},
            {
                "operation": "find_type_refs",
                "type_descriptor": target,
                "type_relation": "operand",
                "offset": 0,
                "limit": 100,
            },
            root,
        )
        assert result["status"] == "ok" and "index" not in result
        assert result["total"] == (2 if target == "Lfixture/Target;" else 0)
        assert (root / "xrefs.sqlite").exists() == indexed
        assert not (root / "calls.sqlite").exists()
    finally:
        service.close()


@pytest.mark.parametrize("accelerator", [False, True])
@pytest.mark.parametrize("mutation", ["index", "unknown", "truncated", "payload"])
def test_type_cursor_validates_even_when_no_type_matches(accelerator, mutation):
    from droidasc_mcp.native_dex import Dex, InvalidDex
    from droidasc_mcp.native_scan import scanner

    code = bytearray(16) + b"\x1c\x00\x00\x00\x0e\x00"
    struct.pack_into("<I", code, 12, 3)
    if mutation == "index":
        struct.pack_into("<H", code, 18, 2)
    elif mutation == "unknown":
        code[16] = 0xE3
    elif mutation == "truncated":
        code[20] = 0x1C
    else:
        code[16:18] = b"\x00\x03"
    dex = Dex.__new__(Dex)
    dex.data, dex.version, dex.tables = bytes(code), 39, [(2, 0)] * 5
    with pytest.raises(InvalidDex):
        list(scanner(dex, set(), 3, True, accelerator=accelerator)(0))


def test_old_accelerator_uses_checked_type_fallback(monkeypatch):
    from droidasc_mcp import _dexscan

    monkeypatch.delattr(_dexscan, "type_operands")
    test_checked_cursor_covers_every_type_operand(True)


@pytest.mark.parametrize(
    "extra",
    [
        {"type_match": "regex"},
        {"type_match": "substring", "type_relation": "instruction"},
        {"type_descriptor": ""},
        {"type_descriptor": " "},
        {"type_descriptor": 1},
        {"class_name": "fixture.Target"},
        {"value": "Target"},
        {"prefix": "fixture"},
        {"type_descriptor": "Target.*", "type_match": "exact"},
    ],
)
def test_type_operand_invalid_selectors(extra):
    from droidasc_mcp.service import _normalize_dex_query

    with pytest.raises(ValueError):
        _normalize_dex_query(
            {
                "operation": "find_type_refs",
                "type_descriptor": "Lfixture/Target;",
                "type_relation": "operand",
                **extra,
            }
        )


@pytest.mark.parametrize(
    "value,expected",
    [
        ("Lpkg.Type", "LLpkg/Type;"),
        ("Lpkg.Type;", "Lpkg/Type;"),
        ("[Lpkg.Type;", "[Lpkg/Type;"),
        ("pkg.Type", "Lpkg/Type;"),
    ],
)
def test_dotted_type_names_starting_with_l_are_not_truncated(value, expected):
    from droidasc_mcp.service import _normalize_dex_query

    result = _normalize_dex_query(
        {
            "operation": "find_type_refs",
            "type_descriptor": value,
            "type_relation": "operand",
        }
    )
    assert result["type_descriptor"] == expected


@pytest.mark.parametrize("accelerator", [False, True])
def test_checked_cursor_covers_every_type_operand(accelerator):
    from droidasc_mcp.native_dex import WIDTHS, Dex
    from droidasc_mcp.native_scan import scanner

    code = bytearray(16)
    expected = []
    for op in (0x1C, 0x1F, 0x20, 0x22, 0x23, 0x24, 0x25):
        position = len(code)
        expected.append((position, (position - 16) // 2, op))
        code.extend(bytes([op, 0, 1, 0]) + bytes(WIDTHS[op] * 2 - 4))
    code.extend(b"\x0e\x00")
    struct.pack_into("<I", code, 12, (len(code) - 16) // 2)
    dex = Dex.__new__(Dex)
    dex.data, dex.version, dex.tables = bytes(code), 39, [(2, 0)] * 5
    rows = list(scanner(dex, {1}, 3, True, accelerator=accelerator)(0))
    assert [r[:3] for r in rows if r[2] >= 0] == expected
    assert sum(r[3] for r in rows) == 8


@pytest.mark.parametrize(
    "selector,mode,opcodes",
    [
        ("Lfixture/Target;", "exact", ["const-class", "check-cast"]),
        ("fixture.Target", "exact", ["const-class", "check-cast"]),
        ("[Lfixture/Target;", "exact", ["const-class"]),
        ("Lfixture/Target;", "substring", ["const-class", "check-cast", "const-class"]),
        ("fixture.Target", "substring", ["const-class", "check-cast", "const-class"]),
        ("Ljava/lang/Exception;", "exact", []),
        ("Lmissing/Nothing;", "exact", []),
        ("fixture/target", "substring", []),
        ("Target.*", "substring", []),
    ],
)
def test_type_scope_matching(smali_dex_files, selector, mode, opcodes):
    service = DroidAscService(
        replace(Settings.from_env(), allowed_roots=(smali_dex_files[0].parent,))
    )
    try:
        result = service.analyze_dex(
            [str(p) for p in smali_dex_files],
            operation="find_type_refs",
            type_descriptor=selector,
            type_relation="operand",
            type_match=mode,
            offset=0,
            limit=100,
        )
        assert result["status"] == "ok", result
        assert [r["opcode"] for r in result["items"]] == opcodes
    finally:
        service.close()
