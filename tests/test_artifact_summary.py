"""Opt-in summaries retain checked archive identity and bounded manifest evidence."""

import hashlib
import zipfile
from dataclasses import replace

import pytest
from pydantic import TypeAdapter, ValidationError

from droidasc_mcp import archive_worker as worker
from droidasc_mcp.config import Settings
from droidasc_mcp.contracts import ArtifactResult
from droidasc_mcp.service import DroidAscService

MANIFEST = (
    b'<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
    b'package="example.summary" android:versionName="@string/version" android:versionCode="42">'
    b'<uses-sdk android:minSdkVersion="23" android:targetSdkVersion="35"/>'
    b'<application android:name=".App"><activity android:name=".Main"/></application></manifest>'
)


def artifact(tmp_path, entries, suffix="apk"):
    path = tmp_path / f"summary.{suffix}"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return path


def inspect(path, **query):
    return worker.analyze(
        {
            "apk_path": str(path),
            "allowed_roots": [str(path.parent)],
            "max_input_bytes": 16 * 1024**2,
            "max_page_size": 100,
            "query": {"operation": "artifact_inventory", **query},
        }
    )


def test_opt_in_summary_reuses_inventory_and_preserves_raw_declarations(tmp_path, monkeypatch):
    path = artifact(
        tmp_path,
        {
            "AndroidManifest.xml": MANIFEST,
            "classes.dex": b"invalid DEX is inventory only",
            "lib/arm64-v8a/liba.so": b"library inventory only",
            "lib/x86/liba.so": b"library inventory only",
            "lib/x86/deeper/not-a-library.so": b"ignored",
            "lib/x86/directory.so/": b"",
        },
    )
    opened = []
    original = zipfile.ZipFile.open

    def track(self, member, *args, **kwargs):
        opened.append(member.filename if isinstance(member, zipfile.ZipInfo) else member)
        return original(self, member, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "open", track)
    plain = inspect(path)
    assert "summary" not in plain and opened == []
    result = inspect(path, include_summary=True, limit=1)
    assert opened == ["AndroidManifest.xml"]
    assert result["status"] == "ok" and result["items"] == plain["items"][:1]
    assert result["artifact_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["artifact_size_bytes"] == path.stat().st_size
    summary = result["summary"]
    assert summary == {
        "entry_count": 6,
        "native_scope": "archive",
        "native_library_count": 2,
        "native_abis": ["arm64-v8a", "x86"],
        "native_abi_count": 2,
        "native_abis_truncated": False,
        "manifest": {
            "entry": "AndroidManifest.xml",
            "status": "ok",
            "xml_format": "text_xml",
            "decoding_warnings": [],
            "package_name": "example.summary",
            "version_name": "@string/version",
            "version_code": "42",
            "min_sdk": "23",
            "target_sdk": "35",
            "application_name": ".App",
            "resource_values_resolved": False,
        },
    }
    assert TypeAdapter(ArtifactResult).validate_python(result) == result
    with pytest.raises(ValidationError):
        TypeAdapter(ArtifactResult).validate_python(
            {**result, "summary": {**summary, "entry_count": "6"}}
        )


@pytest.mark.parametrize("suffix", ["jar", "aar", "apks", "xapk", "zip"])
def test_non_apk_missing_manifest_has_explicit_coverage(tmp_path, suffix):
    path = artifact(tmp_path, {"nested.apk": b"inventory only"}, suffix)
    result = inspect(path, include_summary=True)
    assert result["status"] == "ok" and result["nested_apk_count"] == 1
    assert result["summary"]["native_abis"] == []
    assert result["summary"]["manifest"] == {
        "entry": "AndroidManifest.xml",
        "status": "not_applicable",
        "code": "manifest_not_found",
    }


@pytest.mark.parametrize("module", [None, "feature"])
def test_aab_summary_matches_selected_module_only(tmp_path, module):
    path = artifact(
        tmp_path,
        {
            "base/manifest/AndroidManifest.xml": MANIFEST,
            "base/lib/arm64-v8a/libbase.so": b"base",
            "base/dex/classes.dex": b"base DEX",
            "feature/manifest/AndroidManifest.xml": b'<manifest package="feature"/>',
            "feature/lib/x86/libfeature.so": b"feature",
            "feature/dex/classes.dex": b"feature DEX",
            "lib/irrelevant/lib.so": b"outside modules",
        },
        "aab",
    )
    result = inspect(path, module=module, include_summary=True)
    chosen = module or "base"
    assert result["selected_module"] == chosen
    summary = result["summary"]
    assert summary["native_scope"] == "selected_module" and summary["entry_count"] == 7
    assert summary["native_abis"] == (["x86"] if module else ["arm64-v8a"])
    assert summary["native_library_count"] == 1
    assert summary["manifest"]["entry"] == f"{chosen}/manifest/AndroidManifest.xml"
    assert summary["manifest"]["package_name"] == ("feature" if module else "example.summary")


@pytest.mark.parametrize(
    "manifest,code",
    [
        (b"<manifest>", "invalid_xml"),
        (b"<other/>", "invalid_manifest"),
        (b"<manifest><application/><application/></manifest>", "invalid_manifest"),
        (b"<manifest><uses-sdk/><uses-sdk/></manifest>", "invalid_manifest"),
        (b'<!DOCTYPE manifest [<!ENTITY x "secret">]><manifest package="&x;"/>', "invalid_xml"),
        (b"<manifest>" + b"<a/>" * 20_001 + b"</manifest>", "xml_limit"),
        (b"x" * (worker.MAX_XML_BYTES + 1), "xml_limit"),
    ],
)
def test_manifest_diagnostics_do_not_hide_available_inventory(tmp_path, manifest, code):
    path = artifact(tmp_path, {"AndroidManifest.xml": manifest, "classes.dex": b"inventory"})
    result = inspect(path, include_summary=True)
    assert result["status"] == "ok" and result["dex_entries"] == ["classes.dex"]
    header = result["summary"]["manifest"]
    assert header["status"] == "error" and header["code"] == code
    assert "package_name" not in header


def test_aab_protobuf_manifest_decode_limitation_is_explicit(tmp_path):
    path = artifact(tmp_path, {"base/manifest/AndroidManifest.xml": b"\x0a\x00"}, "aab")
    header = inspect(path, include_summary=True)["summary"]["manifest"]
    assert header["status"] == "error" and header["code"] == "invalid_xml"
    assert "protobuf XML is not decoded" in header["message"]


def test_summary_manifest_shares_nested_expansion_budget(tmp_path):
    from test_containers import zip_bytes

    nested = zip_bytes([("Example.class", b"class")])
    path = artifact(tmp_path, {"classes.jar": nested, "AndroidManifest.xml": MANIFEST}, "aar")
    result = inspect(path, include_summary=True, max_uncompressed_bytes=len(nested))
    assert result["status"] == "ok" and result["jvm_class_count"] == 1
    assert result["summary"]["manifest"]["code"] == "container_limit"


def test_abi_summary_has_explicit_count_and_truncation(tmp_path):
    path = artifact(tmp_path, {f"lib/abi{i:03}/liba.so": b"" for i in range(101)})
    summary = inspect(path, include_summary=True)["summary"]
    assert summary["native_library_count"] == summary["native_abi_count"] == 101
    assert summary["native_abis_truncated"] and len(summary["native_abis"]) == 100
    assert summary["native_abis"] == [f"abi{i:03}" for i in range(100)]


def test_comparison_summary_is_explicitly_the_input_artifact(tmp_path):
    old = artifact(tmp_path, {"AndroidManifest.xml": MANIFEST, "Before.class": b"class"})
    newer = tmp_path / "new.jar"
    with zipfile.ZipFile(newer, "w") as archive:
        archive.writestr("After.class", b"class")
    result = inspect(old, compare_to=str(newer), include_summary=True)
    assert result["status"] == "ok" and result["counts"]["added"] == 1
    assert result["summary"]["manifest"]["package_name"] == "example.summary"
    assert result["summary"]["entry_count"] == 2


@pytest.mark.parametrize("value", [None, 0, 1, "true", [], {}])
def test_summary_flag_is_strict_at_service_and_worker_boundaries(tmp_path, value):
    path = artifact(tmp_path, {"AndroidManifest.xml": MANIFEST})
    assert inspect(path, include_summary=value)["code"] == "invalid_query"
    service = DroidAscService(replace(Settings.from_env(), allowed_roots=(tmp_path,)))
    try:
        with pytest.raises(ValueError, match="boolean"):
            service.inspect_artifact(str(path), include_summary=value)
    finally:
        service.close()


def test_summary_cannot_escape_final_identity_validation(tmp_path, monkeypatch):
    path = artifact(tmp_path, {"AndroidManifest.xml": MANIFEST})
    original = worker._query

    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        with path.open("ab") as handle:
            handle.write(b"changed")
        return result

    monkeypatch.setattr(worker, "_query", mutate)
    result = inspect(path, include_summary=True)
    assert result["status"] == "error" and result["code"] == "input_changed"
    assert "summary" not in result


@pytest.mark.parametrize("failure", ["encrypted", "incomplete"])
def test_summary_reports_unreadable_manifest_explicitly(tmp_path, monkeypatch, failure):
    from droidasc_mcp import artifact_summary

    path = artifact(tmp_path, {"AndroidManifest.xml": MANIFEST})
    if failure == "encrypted":
        original = worker._entries

        def encrypted(archive):
            entries = original(archive)
            entries["AndroidManifest.xml"].flag_bits |= 1
            return entries

        monkeypatch.setattr(worker, "_entries", encrypted)
    else:
        monkeypatch.setattr(artifact_summary, "_read", lambda *args: (b"<manifest", False))
    result = inspect(path, include_summary=True)
    assert result["status"] == "ok"
    header = result["summary"]["manifest"]
    assert header["status"] == "error"
    assert header["code"] == ("encrypted_entry" if failure == "encrypted" else "invalid_archive")
    assert "package_name" not in header


def test_summary_preserves_zip_safety_checks(tmp_path):
    path = artifact(tmp_path, {"../AndroidManifest.xml": MANIFEST})
    result = inspect(path, include_summary=True)
    assert result["status"] == "error" and result["code"] == "unsafe_entry"
    assert "summary" not in result
