"""Independent structural, operand-text and source-link acceptance oracles."""

import hashlib
from dataclasses import replace

import pytest
from conftest import assemble_smali

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService


@pytest.fixture(scope="module")
def structure_files(tmp_path_factory):
    return assemble_smali(tmp_path_factory, ("structure",))


@pytest.fixture(scope="module")
def structure_service(structure_files):
    service = DroidAscService(
        replace(Settings.from_env(), allowed_roots=(structure_files[0].parent,), timeout_seconds=90)
    )
    opened = service.open_dex_session([str(p) for p in structure_files])
    assert opened["status"] == "ok", opened
    try:
        yield service, opened["session_id"]
    finally:
        service.close()


def query(pair, operation, **kwargs):
    service, key = pair
    result = service.query_dex_session(
        key, operation=operation, threads=1, offset=0, limit=100, **kwargs
    )
    assert result["status"] == "ok", result
    return result


def test_outline_and_hierarchy(structure_service):
    result = query(structure_service, "get_class_outline", class_name="structure.Base")
    assert result["superclass"] == "Lexternal/Root;"
    assert (result["field_count"], result["method_count"], result["total"]) == (2, 4, 7)
    methods = [row for row in result["items"] if row["kind"] == "method"]
    assert len({row["descriptor"] for row in methods}) == 4
    assert next(row for row in methods if row["name"] == "empty")["has_code"] is False
    assert next(row for row in methods if row["name"] == "numeric")["dispatch_kind"] == "direct"
    hierarchy = query(structure_service, "get_class_hierarchy", class_name="structure.Base")
    assert {(row["relation"], row["type_descriptor"]) for row in hierarchy["items"]} == {
        ("superclass", "Lexternal/Root;"),
        ("interface", "Lstructure/Contract;"),
        ("direct_subclass", "Lstructure/Child;"),
    }
    assert not hierarchy["hierarchy_cycle_detected"]
    contract = query(structure_service, "get_class_hierarchy", class_name="structure.Contract")
    assert any(row.get("relation") == "direct_implementor" for row in contract["items"])
    cycle = query(structure_service, "get_class_hierarchy", class_name="structure.CycleA")
    assert cycle["hierarchy_cycle_detected"]
    assert [
        row["type_descriptor"] for row in cycle["items"] if row["relation"] == "superclass"
    ] == ["Lstructure/CycleB;"]


def test_switch_and_array_payload_rendering(structure_service):
    switch = query(
        structure_service,
        "disassemble_method",
        method_descriptor="Lstructure/Payload;->select(I)I",
    )
    assert any(row["opcode"] == "packed-switch-payload" for row in switch["items"])
    array = query(structure_service, "search_method_bodies", value="0x12345678")
    assert array["total"] == 1
    assert array["items"][0]["opcode"] == "array-payload"


def test_all_competitor_secret_families_and_extra_github_pattern(structure_service):
    service, key = structure_service
    hidden = service.secret_candidates(key)
    assert hidden["status"] == "ok", hidden
    assert {row["pattern"] for row in hidden["items"]} == {
        "aws_access_key_id",
        "google_api_key",
        "private_key_marker",
        "credential_assignment",
        "jwt_like",
        "github_classic_token",
    }
    assert not any("value" in row for row in hidden["items"])
    visible = service.secret_candidates(key, include_values=True)
    assert visible["status"] == "ok", visible
    assert all(
        hashlib.sha256(row["value"].encode()).hexdigest() == row["candidate_sha256"]
        for row in visible["items"]
    )
    assert (
        next(row["value"] for row in visible["items"] if row["pattern"] == "credential_assignment")
        == "synthetic-value-only"
    )


def test_constants_jumbo_unicode_and_instruction_offsets(structure_service):
    result = query(structure_service, "get_string_constants", class_name="structure.Base")
    assert {row["value"] for row in result["items"]} == {"", "MixedCase 中文"}
    assert {row["opcode"] for row in result["items"]} == {"const-string", "const-string/jumbo"}
    assert all(
        row["instruction_offset"] == 0 and row["offset_unit"] == "16_bit_code_units"
        for row in result["items"]
    )
    numeric = query(structure_service, "search_method_bodies", value="v0, 0x1234")
    assert numeric["total"] == 1 and numeric["items"][0]["opcode"] == "const/16"
    assert (
        query(structure_service, "search_method_bodies", value="mixedcase", case_sensitive=False)[
            "total"
        ]
        == 1
    )
    assert (
        query(structure_service, "search_method_bodies", value="mixedcase", case_sensitive=True)[
            "total"
        ]
        == 0
    )


def test_disassembly_exact_overloads_no_code_and_pagination(structure_service):
    method = "Lstructure/Base;->text(I)Ljava/lang/String;"
    result = query(structure_service, "disassemble_method", method_descriptor=method)
    assert [row["opcode"] for row in result["items"]] == ["const-string/jumbo", "return-object"]
    assert [row["instruction_offset"] for row in result["items"]] == [0, 3]
    assert all(row["method_descriptor"] == method for row in result["items"])
    assert (
        query(
            structure_service, "disassemble_method", method_descriptor="Lstructure/Base;->empty()V"
        )["total"]
        == 0
    )
    service, key = structure_service
    for op, kwargs in (
        ("get_class_outline", {"class_name": "structure.Base"}),
        ("disassemble_method", {"method_descriptor": method}),
        ("get_class_hierarchy", {"class_name": "structure.Base"}),
    ):
        rows, offset = [], 0
        while True:
            page = service.query_dex_session(
                key, operation=op, threads=1, offset=offset, limit=1, **kwargs
            )
            assert page["status"] == "ok", page
            rows += page["items"]
            if not page["has_more"]:
                break
            offset = page["next_offset"]
        assert rows == query(structure_service, op, **kwargs)["items"]
    missing = service.query_dex_session(
        key,
        operation="disassemble_method",
        method_descriptor="Lstructure/Base;->missing()V",
        offset=0,
        limit=1,
    )
    assert missing["code"] == "method_not_found"


def test_case_and_member_name_scope_before_and_after_index(structure_service):
    result = query(
        structure_service, "search_classes", value="base", prefix="structure.", case_sensitive=False
    )
    assert [row["class_name"] for row in result["items"]] == ["Lstructure/Base;"]
    for value in ("structure.Base", "Lstructure/Base;", "structure.Ba", "STRUCTURE.BASE"):
        found = query(structure_service, "search_classes", value=value, case_sensitive=False)
        assert found["items"] == result["items"]
        assert found["match_semantics"].endswith("class_descriptor_or_dotted_name")
    assert query(structure_service, "search_classes", value="STRUCTURE.BASE")["total"] == 0
    for indexed in (False, True):
        if indexed:
            query(structure_service, "build_xref_index")
        assert (
            query(
                structure_service,
                "search_members",
                kind="method",
                value="TEXT",
                member_match="name",
                case_sensitive=False,
            )["total"]
            == 2
        )
        assert (
            query(
                structure_service,
                "search_members",
                kind="method",
                value="Base",
                member_match="name",
            )["total"]
            == 0
        )
        assert (
            query(structure_service, "search_strings", value="mixedcase", case_sensitive=False)[
                "total"
            ]
            == 1
        )


def test_source_metadata_tokens_and_line_pages(structure_service):
    result = query(structure_service, "get_class_source_metadata", class_name="structure.Child")
    assert result["member_references"]
    assert result["span_unit"] == "unicode_code_points"
    source = result["source"]
    assert result["source_sha256"] == hashlib.sha256(source.encode()).hexdigest()
    for row in result["member_references"]:
        assert 0 <= row["start"] < row["end"] <= len(source)
        assert source[row["start"] : row["end"]]
    service, key = structure_service
    refs, chunks, offset = [], [], 0
    while True:
        page = service.query_dex_session(
            key,
            operation="get_class_source_metadata",
            class_name="structure.Child",
            offset=offset,
            limit=1,
        )
        assert page["status"] == "ok", page
        chunks.append(page["source"])
        refs += page["member_references"]
        if not page["has_more"]:
            break
        offset = page["next_offset"]
    assert "".join(chunks) == source
    assert refs == result["member_references"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"operation": "get_class_outline"},
        {"operation": "get_string_constants", "class_name": "structure.Base", "fuzzy_class": True},
        {"operation": "search_method_bodies", "value": ""},
        {
            "operation": "get_class_hierarchy",
            "class_name": "structure.Base",
            "case_sensitive": False,
        },
        {"operation": "get_class_source_metadata"},
        {"operation": "disassemble_method", "method_descriptor": "text"},
        {"operation": "search_strings", "value": "x", "case_sensitive": "false"},
    ],
)
def test_structure_rejects_ambiguous_queries(structure_service, kwargs):
    service, key = structure_service
    with pytest.raises(ValueError):
        service.query_dex_session(key, offset=0, limit=10, **kwargs)
