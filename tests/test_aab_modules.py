"""Explicit module unions retain exact DEX evidence and module-addressed metadata."""

import hashlib
import json
import os
import sys
import zipfile
from contextlib import closing, nullcontext
from dataclasses import replace

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from test_integration import running_http_endpoint

from droidasc_mcp.service import DroidAscService


def bundle(tmp_path, entries):
    path = tmp_path / "modules.aab"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return path


@pytest.fixture
def module_bundle(tmp_path, graph_dex_files, smali_dex_files):
    sources = {
        "base/dex/classes.dex": graph_dex_files[0].read_bytes(),
        "feature-a/dex/classes.dex": graph_dex_files[1].read_bytes(),
        "feature-a/dex/classes2.dex": smali_dex_files[0].read_bytes(),
        "feature-b/dex/classes.dex": smali_dex_files[1].read_bytes(),
    }
    entries = {
        **sources,
        **{
            f"{name}/manifest/AndroidManifest.xml": f'<manifest package="{name}"/>'.encode()
            for name in ("base", "feature-a", "feature-b", "metadata-only")
        },
        "base/lib/arm64-v8a/libbase.so": b"base",
        "feature-b/lib/x86/libfeature.so": b"feature",
        "feature-b/res/raw/config.txt": b"feature resource",
    }
    return bundle(tmp_path, entries), sources


@pytest.mark.parametrize("selection", ["*", ["feature-b", "base", "feature-a"]])
@pytest.mark.parametrize("handle", [False, True])
def test_union_keeps_classes_cross_module_edges_and_original_sources(
    settings, module_bundle, selection, handle
):
    path, sources = module_bundle
    with closing(DroidAscService(replace(settings, java_executable="java-must-not-run"))) as svc:
        inventory = svc.inspect_artifact(
            str(path), module=selection, include_summary=True, max_uncompressed_bytes=1024**2
        )
        assert inventory["status"] == "ok", inventory
        chosen = ["base", "feature-a", "feature-b"] + (
            ["metadata-only"] if selection == "*" else []
        )
        assert inventory["selected_modules"] == chosen and inventory["selected_module"] is None
        assert inventory["modules"] == ["base", "feature-a", "feature-b", "metadata-only"]
        assert inventory["dex_entries"] == sorted(sources)
        assert {row["module"] for row in inventory["items"]} == {"base", "feature-a", "feature-b"}
        summary = inventory["summary"]
        assert summary["native_scope"] == "selected_modules"
        assert summary["native_library_count"] == 2 and summary["native_abis"] == [
            "arm64-v8a",
            "x86",
        ]
        assert "manifest" not in summary
        assert [(row["module"], row["package_name"]) for row in summary["manifests"]] == [
            (name, name) for name in chosen
        ]
        opened = (
            svc.load_artifact(str(path), module=selection, max_uncompressed_bytes=1024**2)
            if handle
            else svc.open_artifact_session(
                str(path), module=selection, max_uncompressed_bytes=1024**2
            )
        )
        key = opened["analysis_id" if handle else "session_id"]
        info = svc.query_dex_session(key, operation="info", offset=0, limit=1)
        assert info["status"] == "ok" and info["selected_modules"] == chosen
        assert info["artifact_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        by_entry = {row["dex_entry"]: row for row in info["sources"]}
        assert [row["container_entry"] for row in info["sources"]] == sorted(sources)
        for row in info["sources"]:
            assert row["module"] == row["container_entry"].split("/")[0]
            assert row["sha256"] == hashlib.sha256(sources[row["container_entry"]]).hexdigest()
        classes, offset = [], 0
        while True:
            page = svc.query_dex_session(key, operation="list_classes", offset=offset, limit=2)
            assert page["status"] == "ok", page
            classes.extend(row["class_name"] for row in page["items"])
            if not page["has_more"]:
                break
            offset = page["next_offset"]
        assert sorted(classes) == [
            "Lfixture/Caller;",
            "Lfixture/Target;",
            "Lfixture/Types;",
            "Lgraph/A;",
            "Lgraph/B;",
        ]
        for caller, target, source_module, target_module in (
            ("Lgraph/A;->root()V", "Lgraph/B;->step(I)V", "base", "feature-a"),
            ("Lfixture/Caller;->run()V", "Lfixture/Target;->pick(I)V", "feature-a", "feature-b"),
        ):
            graph = svc.query_dex_session(
                key,
                operation="get_call_graph",
                method_descriptor=caller,
                direction="outgoing",
                depth=1,
                offset=0,
                limit=100,
            )
            assert graph["status"] == "ok", graph
            matches = [row for row in graph["edges"] if row["callee"] == target]
            assert [row["instruction_offset"] for row in matches] == (
                [1, 4] if source_module == "base" else [1]
            )
            for row in matches:
                assert by_entry[row["dex_entry"]]["module"] == source_module
                assert by_entry[row["target_dex_entry"]]["module"] == target_module
        root = svc.sessions.entries[key].storage.name
        svc.close_artifact(key) if handle else svc.sessions.close(key)
        assert not svc.sessions.entries and svc.sessions.reserved == 0
        from pathlib import Path

        assert not Path(root).exists()


@pytest.mark.parametrize(
    "selection",
    [[], ["base", "base"], [""], ["../base"], [None], [1], True, 1, {}, ["*"], [".."], ["."]],
)
def test_invalid_module_selections_fail_before_loading(settings, tmp_path, selection):
    path = bundle(tmp_path, {"base/manifest/AndroidManifest.xml": b"<manifest/>"})
    with closing(DroidAscService(settings)) as svc:
        assert (
            svc.inspect_artifact(str(path), module=selection, max_uncompressed_bytes=1024**2)[
                "code"
            ]
            == "invalid_query"
        )
        with pytest.raises(ValueError):
            svc.load_artifact(str(path), module=selection, max_uncompressed_bytes=1024**2)
        assert not svc.sessions.entries and svc.sessions.reserved == 0


def test_exact_base_defaults_missing_lists_and_manifest_only_module(settings, tmp_path):
    path = bundle(
        tmp_path,
        {
            "base/manifest/AndroidManifest.xml": b'<manifest package="base"/>',
            "all/manifest/AndroidManifest.xml": b'<manifest package="literal.all"/>',
        },
    )
    with closing(DroidAscService(settings)) as svc:
        assert (
            svc.inspect_artifact(str(path), max_uncompressed_bytes=1024**2)["selected_module"]
            == "base"
        )
        assert svc.inspect_artifact(str(path), module="all", max_uncompressed_bytes=1024**2)[
            "selected_modules"
        ] == ["all"]
        assert (
            svc.inspect_artifact(str(path), module=["absent"], max_uncompressed_bytes=1024**2)[
                "code"
            ]
            == "module_not_found"
        )
        key = svc.load_artifact(str(path), module=["all"], max_uncompressed_bytes=1024**2)[
            "analysis_id"
        ]
        result = svc.query_artifact(key, operation="manifest_summary", offset=0, limit=1)
        assert result["package_name"] == "literal.all" and result["module"] == "all"
        assert svc.query_dex_session(key, operation="info")["code"] == "no_analyzable_dex"
        assert svc.query_artifact(key, operation="list_entries", kind="manifest")["total"] == 2


def test_handle_freezes_selection_and_manifest_routing(settings, module_bundle):
    path, _ = module_bundle
    selection = ["feature-b", "base"]
    with closing(DroidAscService(settings)) as svc:
        key = svc.load_artifact(str(path), module=selection, max_uncompressed_bytes=1024**2)[
            "analysis_id"
        ]
        selection[:] = ["feature-a"]
        summary = svc.query_artifact(key, operation="artifact_inventory", include_summary=True)
        assert summary["selected_modules"] == ["base", "feature-b"]
        assert svc.query_artifact(key, operation="manifest_summary")["code"] == "ambiguous_module"
        assert (
            svc.query_artifact(key, operation="manifest_summary", module="feature-a")["code"]
            == "module_not_selected"
        )
        manifest = svc.query_artifact(key, operation="manifest_summary", module="feature-b")
        assert manifest["status"] == "ok" and manifest["package_name"] == "feature-b"
        assert manifest["entry"]["path"] == "feature-b/manifest/AndroidManifest.xml"
        content = svc.query_artifact(
            key, operation="read_entry", entry_path="feature-b/res/raw/config.txt"
        )
        assert content["content"] == "feature resource" and content["module"] == "feature-b"
        assert svc.query_artifact(key, operation="list_entries", kind="dex")["total"] == 4


def test_union_duplicate_classes_and_combined_expansion_budget(settings, tmp_path, graph_dex_files):
    first, second = [path.read_bytes() for path in graph_dex_files]
    path = bundle(tmp_path, {"base/dex/classes.dex": first, "feature/dex/classes.dex": first})
    with closing(DroidAscService(settings)) as svc:
        assert (
            svc.open_artifact_session(str(path), module="*", max_uncompressed_bytes=1024**2)["code"]
            == "duplicate_class"
        )
        assert not svc.sessions.entries and svc.sessions.reserved == 0
        path = bundle(tmp_path, {"base/dex/classes.dex": first, "feature/dex/classes.dex": second})
        assert (
            svc.open_artifact_session(
                str(path), module="*", max_uncompressed_bytes=max(len(first), len(second))
            )["code"]
            == "container_limit"
        )
        assert not svc.sessions.entries and svc.sessions.reserved == 0


def test_union_summary_manifests_share_budget_and_keep_protobuf_limit(settings, tmp_path):
    base = b'<manifest package="base"/>'
    feature = b'<manifest package="feature"/>'
    path = bundle(
        tmp_path,
        {
            "base/manifest/AndroidManifest.xml": base,
            "a/manifest/AndroidManifest.xml": b"\x0a\x00",
            "feature/manifest/AndroidManifest.xml": feature,
        },
    )
    with closing(DroidAscService(settings)) as svc:
        summary = svc.inspect_artifact(
            str(path), module="*", include_summary=True, max_uncompressed_bytes=len(base) + 2
        )["summary"]
        a, base_header, feature_header = summary["manifests"]
        assert a["code"] == "invalid_xml" and "protobuf XML is not decoded" in a["message"]
        assert base_header["package_name"] == "base"
        assert feature_header["code"] == "container_limit"
        key = svc.load_artifact(str(path), module="*", max_uncompressed_bytes=1024**2)[
            "analysis_id"
        ]
        assert (
            "protobuf XML is not decoded"
            in svc.query_artifact(key, operation="manifest_xml", module="a")["message"]
        )


@pytest.mark.parametrize("selection", ["*", [f"m{i}" for i in range(101)]])
def test_module_union_count_is_bounded(settings, tmp_path, selection):
    path = bundle(
        tmp_path, {f"m{i}/manifest/AndroidManifest.xml": b"<manifest/>" for i in range(101)}
    )
    with closing(DroidAscService(settings)) as svc:
        result = svc.inspect_artifact(str(path), module=selection, max_uncompressed_bytes=1024**2)
        assert result["code"] == ("module_limit" if selection == "*" else "invalid_query")


def test_module_selectors_do_not_apply_to_apk_inputs(settings, tmp_path):
    path = bundle(tmp_path, {"AndroidManifest.xml": b"<manifest/>"}).rename(tmp_path / "input.apk")
    with closing(DroidAscService(settings)) as svc:
        assert (
            svc.inspect_artifact(str(path), module="*", max_uncompressed_bytes=1024**2)["code"]
            == "invalid_query"
        )
        key = svc.load_artifact(str(path), max_uncompressed_bytes=1024**2)["analysis_id"]
        assert (
            svc.query_artifact(key, operation="manifest_summary", module="base")["code"]
            == "invalid_query"
        )


@pytest.mark.anyio
@pytest.mark.parametrize("transport", ["stdio", "http"])
async def test_all_modules_metadata_and_code_over_real_transports(
    module_bundle, tmp_path, monkeypatch, transport
):
    path, _ = module_bundle
    owned = tmp_path / "owned-temporary"
    owned.mkdir()
    for name in ("TMPDIR", "TMP", "TEMP"):
        monkeypatch.setenv(name, str(owned))
    monkeypatch.setenv("DROIDASC_MCP_ALLOWED_ROOTS", str(tmp_path))
    monkeypatch.setenv("DROIDASC_MCP_TOOL_PROFILE", "artifact")
    monkeypatch.setenv("DROIDASC_MCP_JAVA", "java-must-not-run")
    monkeypatch.delenv("DROIDASC_MCP_JADX_HOME", raising=False)
    monkeypatch.delenv("DROIDASC_MCP_DEXLIB_HOME", raising=False)
    with running_http_endpoint(tmp_path) if transport == "http" else nullcontext(None) as http:
        endpoint = http or StdioServerParameters(
            command=sys.executable, args=["-m", "droidasc_mcp"], env=dict(os.environ)
        )
        async with Client(endpoint) as client:

            async def call(name, **arguments):
                reply = await client.call_tool(name, arguments)
                assert not reply.is_error, reply
                return reply.structured_content

            loaded = await call(
                "load_artifact", path=str(path), module="*", max_uncompressed_bytes=1024**2
            )
            key = loaded["analysis_id"]
            summary = await call("apk_get_summary", analysis_id=key)
            assert len(summary["selected_modules"]) == 4
            manifest = await call("apk_get_manifest", analysis_id=key, module="feature-b")
            assert manifest["package_name"] == "feature-b"
            resource = await client.read_resource(
                f"droidasc://analysis/{key}/manifest?module=feature-a&limit=1"
            )
            assert json.loads(resource.contents[0].text)["module"] == "feature-a"
            classes = await call("apk_list_classes", analysis_id=key, limit=100)
            assert classes["total"] == 5
            graph = await call(
                "apk_get_call_graph",
                analysis_id=key,
                method_descriptor="Lfixture/Caller;->run()V",
                direction="outgoing",
                depth=1,
            )
            assert any(
                row["callee"] == "Lfixture/Target;->pick(I)V"
                and row["target_resolution"] == "defined_in_input"
                for row in graph["edges"]
            )
            content = await call(
                "apk_get_resource_content", analysis_id=key, path="feature-b/res/raw/config.txt"
            )
            assert content["module"] == "feature-b" and content["content"] == "feature resource"
            assert (await call("close_artifact", analysis_id=key))["closed"]
            assert (await call("asc_ping"))["dex_sessions"]["open_count"] == 0
    assert not list(owned.iterdir())
