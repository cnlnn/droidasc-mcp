"""Source-backed competitor workflow gaps across the actual public MCP transports."""

import base64
import hashlib
import os
import sys
import zipfile
from contextlib import nullcontext

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from test_integration import running_http_endpoint

from droidasc_mcp.archive_worker import entry_kind
from droidasc_mcp.service import _normalize_class_prefix, _normalize_dex_query


@pytest.mark.parametrize("operation", ["list_classes", "search_classes"])
@pytest.mark.parametrize(
    "prefix, expected",
    [
        (None, None),
        ("", ""),
        ("fixture.", "Lfixture/"),
        ("fixture.Ca", "Lfixture/Ca"),
        ("Local.Package.", "LLocal/Package/"),
        ("Lfixture/", "Lfixture/"),
        ("Lfixture/Caller;", "Lfixture/Caller;"),
        ("L", "L"),
        ("包.类", "L包/类"),
    ],
)
def test_class_prefix_normalization_is_shared(operation, prefix, expected):
    assert _normalize_class_prefix(prefix) == expected
    query = {"operation": operation, "prefix": prefix, "value": "Caller"}
    assert _normalize_dex_query(query)["prefix"] == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("fixture.Target", "Lfixture/Target;"),
        ("android.app.Activity", "Landroid/app/Activity;"),
        ("Local.Target", "LLocal/Target;"),
        ("Target", "LTarget;"),
        ("LTarget", "LLTarget;"),
        ("fixture.Target$Inner", "Lfixture/Target$Inner;"),
        ("包.类型", "L包/类型;"),
        ("Lfixture/Target;", "Lfixture/Target;"),
        ("[Lfixture/Target;", "[Lfixture/Target;"),
        ("[[I", "[[I"),
        *[(value, value) for value in "ZBCSIJFD"],
    ],
)
def test_exact_type_name_handoff_preserves_dex_identities(value, expected):
    query = _normalize_dex_query({"operation": "find_type_refs", "type_descriptor": value})
    assert query["type_descriptor"] == expected


@pytest.mark.parametrize(
    "value", [None, "", "V", "[V", "[LTarget", "Lfoo.Bar;", "foo.*", "foo..Bar", "foo Bar", 1]
)
def test_type_handoff_still_rejects_void_patterns_and_malformed_names(value):
    with pytest.raises(ValueError, match="type_descriptor"):
        _normalize_dex_query({"operation": "find_type_refs", "type_descriptor": value})


@pytest.mark.parametrize(
    "path, kind",
    [
        ("classes.dex", "dex"),
        ("classes12.dex", "dex"),
        ("payload.dex", "dex"),
        ("PAYLOAD.DEX", "dex"),
        ("assets/payload.dex", "asset"),
        ("res/raw/payload.dex", "resource"),
        ("META-INF/payload.dex", "metadata"),
        ("nested/payload.dex", "other"),
        ("payload.dex/", "other"),
        ("payload.dex.txt", "other"),
    ],
)
def test_dex_inventory_category_matches_root_input_capabilities(path, kind):
    assert entry_kind(path) == kind


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_discovered_dex_and_dotted_identifiers_roundtrip(
    transport, tmp_path, smali_dex_files, monkeypatch
):
    artifact = tmp_path / "named payloads.jar"
    originals = {
        "payload.dex": smali_dex_files[0].read_bytes(),
        "SECOND.DEX": smali_dex_files[1].read_bytes(),
    }
    with zipfile.ZipFile(artifact, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in originals.items():
            archive.writestr(name, data)
        archive.writestr("assets/not-code.dex", b"asset, not selected by the dex category")
    # The legacy APK route uses standard entry names; both class-list routes must agree.
    apk = tmp_path / "legacy.apk"
    with zipfile.ZipFile(apk, "w") as archive:
        for index, data in enumerate(originals.values(), 1):
            archive.writestr("classes.dex" if index == 1 else f"classes{index}.dex", data)
    monkeypatch.setenv("ASC_TEST_ROOT", str(tmp_path))
    monkeypatch.setenv("DROIDASC_MCP_JAVA", "java-must-not-run")
    monkeypatch.delenv("DROIDASC_MCP_JADX_HOME", raising=False)
    monkeypatch.delenv("DROIDASC_MCP_DEXLIB_HOME", raising=False)
    endpoint = (
        running_http_endpoint(tmp_path)
        if transport == "http"
        else nullcontext(
            StdioServerParameters(
                command=sys.executable,
                args=["-m", "droidasc_mcp"],
                env={**os.environ, "DROIDASC_MCP_ALLOWED_ROOTS": str(tmp_path)},
            )
        )
    )
    with endpoint as address:
        async with Client(address) as client:

            async def call(name, **args):
                reply = await client.call_tool(name, args)
                assert not reply.is_error, reply
                result = reply.structured_content
                assert result.get("status", "ok") == "ok", result
                return result

            offset, entries = 0, []
            while True:
                page = await call(
                    "asc_list_apk_entries",
                    apk_path=str(artifact),
                    kind="dex",
                    offset=offset,
                    limit=1,
                )
                assert page["artifact_sha256"] == hashlib.sha256(artifact.read_bytes()).hexdigest()
                entries.extend(row["path"] for row in page["items"])
                if page["next_offset"] is None:
                    break
                offset = page["next_offset"]
            assert entries == sorted(originals)
            paths = []
            for name in entries:
                read = await call("asc_read_apk_entry", apk_path=str(artifact), entry_path=name)
                assert read["content_complete"] and read["crc_verified"]
                assert base64.b64decode(read["content"]) == originals[name]
                path = tmp_path / name
                path.write_bytes(originals[name])
                paths.append(str(path))
            opened = await call("asc_open_dex_session", dex_paths=paths)
            key = opened["session_id"]
            try:
                common = {"operation": "list_classes", "prefix": "fixture.", "limit": 1}
                offset, classes = 0, []
                while True:
                    page = await call(
                        "asc_query_dex_session", session_id=key, offset=offset, **common
                    )
                    assert page["total"] == 3
                    classes.extend(row["class_name"] for row in page["items"])
                    if page["next_offset"] is None:
                        break
                    offset = page["next_offset"]
                assert classes == ["Lfixture/Caller;", "Lfixture/Target;", "Lfixture/Types;"]
                once = await call("asc_analyze_dex", dex_paths=paths, **{**common, "limit": 100})
                assert [row["class_name"] for row in once["items"]] == classes
                legacy = await call("asc_list_classes", apk_path=str(apk), prefix="fixture.")
                literal = await call("asc_list_classes", apk_path=str(apk), prefix="Lfixture/")
                assert legacy["total"] == literal["total"] == 3
                assert legacy["items"] == literal["items"]
                for relation, name, descriptor in (
                    ("instruction", "fixture.Target", "Lfixture/Target;"),
                    ("declaration", "external.Base", "Lexternal/Base;"),
                ):
                    query = {"operation": "find_type_refs", "type_relation": relation, "limit": 1}
                    offset, actual = 0, []
                    while True:
                        page = await call(
                            "asc_query_dex_session",
                            session_id=key,
                            type_descriptor=name,
                            offset=offset,
                            **query,
                        )
                        assert page["total"] > 0
                        actual.extend(page["items"])
                        if page["next_offset"] is None:
                            break
                        offset = page["next_offset"]
                    exact = await call(
                        "asc_query_dex_session",
                        session_id=key,
                        type_descriptor=descriptor,
                        **{**query, "limit": 100},
                    )
                    assert actual == exact["items"]
            finally:
                await call("asc_close_dex_session", session_id=key)
