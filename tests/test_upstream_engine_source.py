"""Exercise installed ASC source fixes through the public service and real workers."""

import hashlib
import re
from dataclasses import replace

import pytest
from conftest import assemble_smali

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService

OWNER = "Lsourcefixes/Subject;"


def complete_pages(service, key, operation):
    pages, offset = [], 0
    while True:
        page = service.query_dex_session(
            key,
            operation=operation,
            class_name=OWNER,
            threads=1,
            offset=offset,
            limit=3,
        )
        assert page["status"] == "ok", page
        assert page["offset"] == offset
        pages.append(page)
        if not page["has_more"]:
            assert page["next_offset"] is None
            return pages
        assert offset < page["next_offset"] <= page["total"]
        offset = page["next_offset"]


@pytest.fixture(scope="module")
def installed_source(tmp_path_factory):
    dex = assemble_smali(tmp_path_factory, ("upstream_sourcefixes",))[0]
    settings = replace(
        Settings.from_env(),
        allowed_roots=(dex.parent,),
        timeout_seconds=90,
        max_parallel=1,
        jadx_home=None,
        dexlib_home=None,
    )
    service = DroidAscService(settings)
    try:
        opened = service.open_dex_session([str(dex)])
        assert opened["status"] == "ok", opened
        key = opened["session_id"]
        plain = complete_pages(service, key, "get_class_source")
        metadata = complete_pages(service, key, "get_class_source_metadata")
        yield {
            "plain_pages": plain,
            "metadata_pages": metadata,
            "plain": "\n".join(page["source"] for page in plain),
            "source": "".join(page["source"] for page in metadata),
            "references": [row for page in metadata for row in page["member_references"]],
            "dex_sha256": hashlib.sha256(dex.read_bytes()).hexdigest(),
        }
    finally:
        service.close()


def test_lazy_method_throws_annotation_survives_both_source_paths(installed_source):
    declaration = r"@Throws\(value=\{Exception\.class\}\)\s+public static void mayThrow\(\)"
    for source in (installed_source["plain"], installed_source["source"]):
        assert re.search(declaration, source), source


def test_original_field_return_and_parameter_type_links(installed_source):
    source, references = installed_source["source"], installed_source["references"]
    field = next(
        row
        for row in references
        if row["kind"] == "field" and row["declaration"] and row["name"] == "label"
    )
    assert (field["declaring_class"], field["descriptor"]) == (OWNER, "Ljava/lang/String;")
    field_types = [
        row
        for row in references
        if row["kind"] == "class"
        and row["end"] < field["start"]
        and source[row["end"] : field["start"]].isspace()
    ]
    assert len(field_types) == 1
    assert field_types[0]["declaring_class"] == "Ljava/lang/String;"
    assert source[field_types[0]["start"] : field_types[0]["end"]] == "String"
    method = next(
        row
        for row in references
        if row["kind"] == "method" and row["declaration"] and row["name"] == "echo"
    )
    assert (method["declaring_class"], method["descriptor"]) == (
        OWNER,
        "(Ljava/lang/Boolean;)Ljava/lang/Boolean;",
    )
    start = source.rfind("\n", 0, method["start"]) + 1
    end = source.index("\n", method["end"])
    signature_types = [
        row for row in references if row["kind"] == "class" and start <= row["start"] < end
    ]
    assert len(signature_types) == 2
    assert {row["declaring_class"] for row in signature_types} == {"Ljava/lang/Boolean;"}
    assert all(source[row["start"] : row["end"]] == "Boolean" for row in signature_types)
    assert signature_types[0]["end"] < method["start"] < signature_types[1]["start"]


def test_array_and_super_tokens_keep_original_type_and_member_links(installed_source):
    source, references = installed_source["source"], installed_source["references"]
    array = re.search(r"new (Object)\[", source)
    assert array is not None, source
    array_links = [row for row in references if (row["start"], row["end"]) == array.span(1)]
    assert len(array_links) == 1
    assert (array_links[0]["kind"], array_links[0]["declaring_class"]) == (
        "class",
        "Ljava/lang/Object;",
    )
    assert "super.toString(" in source and "super.toString(" in installed_source["plain"]
    calls = [
        row
        for row in references
        if row["kind"] == "method" and not row["declaration"] and row["name"] == "toString"
    ]
    assert len(calls) == 1
    assert (calls[0]["declaring_class"], calls[0]["descriptor"]) == (
        "Ljava/lang/Object;",
        "()Ljava/lang/String;",
    )
    assert source[calls[0]["start"] - len("super.") : calls[0]["start"]] == "super."
    assert not {row["declaring_class"] for row in references if row["kind"] == "class"} & {
        "LString;",
        "LBoolean;",
        "LObject;",
        "Lsuper;",
        "Lthis;",
    }


def test_complete_pages_preserve_source_identity_and_global_token_spans(installed_source):
    source, references = installed_source["source"], installed_source["references"]
    assert installed_source["plain"].splitlines() == source.splitlines()
    assert len(installed_source["plain_pages"]) > 1
    assert len(installed_source["metadata_pages"]) > 1
    assert references
    assert len({(row["start"], row["end"]) for row in references}) == len(references)
    for row in references:
        assert 0 <= row["start"] < row["end"] <= len(source)
        text = source[row["start"] : row["end"]]
        assert text
        if row["kind"] in {"field", "method"} and row["name"] != "<init>":
            assert text == row["name"]
    expected_sha = hashlib.sha256(source.encode()).hexdigest()
    cursor = 0
    for page in installed_source["metadata_pages"]:
        assert page["class_name"] == OWNER and page["dex_entry"] == "classes.dex"
        assert page["span_unit"] == "unicode_code_points"
        assert page["source_sha256"] == expected_sha
        assert page["source_start"] == cursor
        cursor += len(page["source"])
        assert page["source_end"] == cursor
        assert page["total"] == len(source.splitlines())
        assert all(
            page["source_start"] <= row["start"] < page["source_end"]
            for row in page["member_references"]
        )
    assert cursor == len(source)
    for page in installed_source["plain_pages"] + installed_source["metadata_pages"]:
        assert len(page["sources"]) == 1
        assert page["sources"][0]["dex_entry"] == "classes.dex"
        assert page["sources"][0]["sha256"] == installed_source["dex_sha256"]
