"""Bounded APK inventory, resource and manifest semantics."""

import base64
import hashlib
import logging
import runpy
import stat
import struct
import zipfile
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from droidasc_mcp import archive_worker as worker
from droidasc_mcp.config import ApkPathError
from droidasc_mcp.runner import DroidAscError, DroidAscRunner
from droidasc_mcp.service import DroidAscService

MANIFEST = b"""<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="org.example" android:versionName="1.2">
  <uses-sdk android:minSdkVersion="23" android:targetSdkVersion="35"/>
  <uses-permission android:name="android.permission.INTERNET"/>
  <uses-permission-sdk-23 android:name="android.permission.CAMERA"/>
  <permission android:name="org.example.GUARD" android:protectionLevel="signature"/>
  <application android:permission="org.example.APP" android:enabled="true">
    <meta-data android:name="api" android:resource="@xml/config"/>
    <activity android:name=".Main" android:exported="true" android:permission="org.example.TARGET">
      <intent-filter android:priority="2">
        <action android:name="android.intent.action.VIEW"/>
        <category android:name="android.intent.category.BROWSABLE"/>
        <data android:scheme="sample" android:host="host" android:pathPrefix="/open"/>
      </intent-filter>
    </activity>
    <activity-alias android:name="Alias" android:targetActivity=".Main"/>
    <activity-alias android:name=".Guarded" android:targetActivity=".Main"
        android:permission="org.example.ALIAS"/>
    <service android:name="Sync" android:permission="" android:enabled="false"/>
    <receiver android:name="other.Receiver" android:exported="@bool/public"/>
    <provider android:name=".Data" android:authorities="org.example.data"
        android:permission="org.example.DATA" android:readPermission="org.example.READ"
        android:writePermission="" android:grantUriPermissions="true">
      <path-permission android:pathPrefix="/private" android:readPermission="org.example.PATH"/>
      <grant-uri-permission android:pathPrefix="/shared"/>
      <meta-data android:name="provider-mode" android:value="test"/>
    </provider>
    <provider android:name=".Inherited"/>
  </application>
</manifest>"""


@pytest.fixture
def archive_apk(tmp_path):
    path = tmp_path / "resources with spaces.apk"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in {
            "AndroidManifest.xml": MANIFEST,
            "assets/settings.json": b'{"url":"https://example.test"}',
            "assets/binary.bin": b"\x00\xff\x01\x02",
            "assets/large.txt": b"x" * 400_000,
            "res/xml/config.xml": b'<config><url value="https://example.test"/></config>',
            "resources.arsc": b"\x02\x00",
            "lib/arm64-v8a/libexample.so": b"\x7fELF",
            "classes.dex": b"dex\n035\0",
            "META-INF/CERT.SF": b"Signature-Version: 1.0",
            "readme.txt": b"example",
        }.items():
            archive.writestr(name, data)
        archive.writestr("assets/empty/", b"")
    return path


def analyze(path, **query):
    return worker.analyze(
        {
            "apk_path": str(path),
            "allowed_roots": [str(path.parent)],
            "max_input_bytes": 16 * 1024**2,
            "max_page_size": 100,
            "query": query,
        }
    )


def test_inventory_provenance_pagination_and_filters(archive_apk):
    first = analyze(archive_apk, operation="list_entries", limit=3)
    assert first["status"] == "ok"
    assert first["apk_sha256"] == hashlib.sha256(archive_apk.read_bytes()).hexdigest()
    assert first["apk_size_bytes"] == archive_apk.stat().st_size
    assert first["total"] == 10 and first["next_offset"] == 3
    remaining = analyze(archive_apk, operation="list_entries", offset=3, limit=100)
    rows = first["items"] + remaining["items"]
    assert [r["path"] for r in rows] == sorted(r["path"] for r in rows)
    assert {r["kind"] for r in rows} == worker.KINDS
    native = analyze(archive_apk, operation="list_entries", kind="native")["items"]
    assert len(native) == 1 and native[0]["abi"] == "arm64-v8a"
    assert native[0]["size_bytes"] == 4 and native[0]["encrypted"] is False
    filtered = analyze(archive_apk, operation="list_entries", prefix="assets/s")
    assert [r["path"] for r in filtered["items"]] == ["assets/settings.json"]
    assert analyze(archive_apk, operation="list_entries", prefix="ASSETS")["total"] == 0
    assert remaining["has_more"] is False and remaining["next_offset"] is None


@pytest.mark.parametrize(
    "query",
    [
        {"operation": "unknown"},
        {"operation": "list_entries", "offset": -1},
        {"operation": "list_entries", "limit": 101},
        {"operation": "list_entries", "limit": True},
        {"operation": "list_entries", "prefix": 4},
        {"operation": "list_entries", "kind": "signature"},
        {"operation": "read_entry", "entry_path": "readme.txt", "max_bytes": 0},
        {"operation": "read_entry", "entry_path": "readme.txt", "max_bytes": 131073},
        {"operation": "read_entry", "entry_path": "readme.txt", "decode_xml": "true"},
    ],
)
def test_invalid_queries(archive_apk, query):
    result = analyze(archive_apk, **query)
    assert result["status"] == "error" and result["code"] == "invalid_query"


def test_reads_are_bounded_without_extraction(archive_apk, monkeypatch):
    def no_whole_entry_read(*args, **kwargs):
        raise AssertionError("Entry reads must use a bounded stream")

    monkeypatch.setattr(zipfile.ZipFile, "read", no_whole_entry_read)
    result = analyze(
        archive_apk, operation="read_entry", entry_path="assets/large.txt", max_bytes=17
    )
    assert result["content"] == "x" * 17 and result["returned_bytes"] == 17
    assert result["truncated"] and not result["content_complete"]
    assert result["crc_verified"] is False and result["status"] == "partial"
    raw = analyze(archive_apk, operation="read_entry", entry_path="assets/binary.bin")
    assert base64.b64decode(raw["content"]) == b"\x00\xff\x01\x02"
    assert raw["encoding"] == "base64" and raw["crc_verified"]
    assert raw["content_complete"] and not raw["decoded"]
    missing = analyze(archive_apk, operation="read_entry", entry_path="missing")
    assert missing["code"] == "entry_not_found"
    directory = analyze(archive_apk, operation="read_entry", entry_path="assets/empty/")
    assert directory["code"] == "entry_is_directory"
    assert sorted(p.name for p in archive_apk.parent.iterdir()) == [archive_apk.name]


def test_xml_decoding_and_output_truncation_are_separate(archive_apk):
    result = analyze(
        archive_apk, operation="read_entry", entry_path="res/xml/config.xml", max_bytes=15
    )
    assert result["decoded"] and result["decoding_status"] == "ok"
    assert result["xml_format"] == "text_xml" and result["crc_verified"]
    assert result["truncated"] and result["returned_bytes"] == 15
    raw = analyze(
        archive_apk, operation="read_entry", entry_path="res/xml/config.xml", decode_xml=False
    )
    assert not raw["decoded"] and raw["decoding_status"] == "not_requested"


def test_manifest_permission_precedence_and_source(archive_apk):
    result = analyze(archive_apk, operation="manifest_summary")
    assert result["status"] == "ok" and result["package_name"] == "org.example"
    assert result["resource_values_resolved"] is False
    assert result["exported_defaults_resolved"] is False
    main, alias, guarded, service, receiver, provider, inherited = result["items"]
    assert main["name"] == "org.example.Main" and main["exported"] is True
    assert main["effective_permission"]["value"] == "org.example.TARGET"
    assert alias["effective_permission"] == {
        "value": None,
        "source": "alias_default",
        "resolved": True,
    }
    assert alias["target_activity"] == main["name"]
    assert alias["target_activity_status"] == "declared_before_alias"
    assert guarded["effective_permission"]["value"] == "org.example.ALIAS"
    assert service["effective_permission"]["value"] is None
    assert service["effective_permission"]["source"] == "component"
    assert service["effective_enabled"] is False
    assert receiver["effective_permission"]["value"] == "org.example.APP"
    assert receiver["exported"] is None
    assert receiver["exported_status"] == "unspecified_or_unresolved"
    assert provider["effective_read_permission"]["value"] == "org.example.READ"
    assert provider["effective_write_permission"]["value"] is None
    assert provider["path_permissions"] and provider["grant_uri_permissions"]
    assert inherited["effective_read_permission"]["value"] == "org.example.APP"
    assert len(result["requested_permissions"]) == 2 and result["declared_permissions"]
    assert result["application_metadata"] and provider["metadata"]
    intent = main["intent_filters"][0]
    assert intent["actions"] and intent["categories"] and intent["data"]
    assert main["source"] == {"entry": "AndroidManifest.xml", "component_index": 0}
    second = analyze(archive_apk, operation="manifest_summary", offset=5, limit=1)
    assert second["items"] == [provider] and second["next_offset"] == 6


@pytest.mark.parametrize("value", ["@string/permission", "?attr/permission", "${permission}"])
def test_unresolved_permissions_and_missing_alias_target(tmp_path, value):
    path = tmp_path / "unresolved.apk"
    xml = MANIFEST.replace(b"org.example.APP", value.encode()).replace(
        b'android:targetActivity=".Main"', b'android:targetActivity=".Missing"'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("AndroidManifest.xml", xml)
    rows = analyze(path, operation="manifest_summary")["items"]
    assert rows[4]["effective_permission"]["resolved"] is False
    assert rows[1]["target_activity_status"] == "unresolved_or_missing"


@pytest.mark.parametrize("name", ["../out", "/absolute", "a/../b", "a\\b", "C:/file", "a//b"])
def test_unsafe_entries_rejected_before_selection(tmp_path, name):
    path = tmp_path / "unsafe.apk"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("readme.txt", b"safe")
        info = zipfile.ZipInfo("raw-entry")
        # ZipInfo construction normalizes native backslashes on Windows.
        info.filename = info.orig_filename = name
        archive.writestr(info, b"unsafe")
    result = analyze(path, operation="read_entry", entry_path="readme.txt")
    assert result["code"] == "unsafe_entry" and "content" not in result


@pytest.mark.parametrize("codepoint", range(32))
def test_safe_name_rejects_every_c0_control(codepoint):
    from droidasc_mcp.archive_worker import safe_name

    with pytest.raises(ValueError, match="safe relative ZIP path"):
        safe_name("resource/part" + chr(codepoint) + "end")


@pytest.mark.parametrize(
    "name", ["res/\u4e2d\u6587.xml", "res/\x7f\x80\uffff", "assets/a:b/", "x/\ud800"]
)
def test_safe_name_preserves_other_unicode_and_relative_names(name):
    from droidasc_mcp.archive_worker import safe_name

    assert safe_name(name) == name


def test_duplicates_and_special_files(tmp_path):
    path = tmp_path / "duplicate.apk"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("a", b"first")
        with pytest.warns(UserWarning, match="Duplicate"):
            archive.writestr("a", b"second")
    assert analyze(path, operation="list_entries")["code"] == "duplicate_entry"
    info = zipfile.ZipInfo("link")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(info, b"/outside")
    assert analyze(path, operation="list_entries")["code"] == "special_entry"


@pytest.mark.parametrize(
    "xml,code",
    [
        (b"<manifest>", "invalid_xml"),
        (
            b'<!DOCTYPE manifest [<!ENTITY x SYSTEM "file:///etc/passwd">]><manifest>&x;</manifest>',
            "invalid_xml",
        ),
        (b"<wrong/>", "invalid_manifest"),
        (b"<manifest><application/><application/></manifest>", "invalid_manifest"),
        (b"\x03\x00\x08\x00" + struct.pack("<I", 8), "invalid_xml"),
        (b"\x03\x00\x08\x00" + struct.pack("<I", 32), "invalid_xml"),
        (b"<manifest>" + b"<a/>" * 20_001 + b"</manifest>", "xml_limit"),
    ],
    ids=["unclosed", "dtd", "root", "applications", "binary-empty", "binary-length", "nodes"],
)
def test_invalid_manifest_is_explicit(tmp_path, xml, code):
    path = tmp_path / "invalid.apk"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("AndroidManifest.xml", xml)
    result = analyze(path, operation="manifest_summary")
    assert result["status"] == "error" and result["code"] == code
    raw = analyze(path, operation="read_entry", entry_path="AndroidManifest.xml")
    if code == "invalid_xml":
        assert raw["decoded"] is False and raw["decoding_status"] == code


def test_xml_input_limit(tmp_path):
    path = tmp_path / "large.apk"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("AndroidManifest.xml", b"x" * (worker.MAX_XML_BYTES + 1))
    result = analyze(path, operation="read_entry", entry_path="AndroidManifest.xml", max_bytes=16)
    assert result["decoding_status"] == "input_limit" and not result["decoded"]
    assert result["truncated"] and not result["crc_verified"]
    assert analyze(path, operation="manifest_summary")["code"] == "xml_limit"


def test_input_change_discards_result(archive_apk, monkeypatch):
    query = worker._query

    def changed(*args):
        result = query(*args)
        with archive_apk.open("ab") as handle:
            handle.write(b"changed")
        return result

    monkeypatch.setattr(worker, "_query", changed)
    result = analyze(archive_apk, operation="list_entries")
    assert result["code"] == "input_changed" and "items" not in result


@pytest.mark.parametrize("change", ["content", "path"])
def test_final_hash_change_discards_result(archive_apk, monkeypatch, change):
    replacement = archive_apk.with_name("replacement.apk")
    replacement.write_bytes(archive_apk.read_bytes())
    original_hash, original_open, calls = worker._digest, Path.open, []

    def digest(stream):
        value = original_hash(stream)
        calls.append(value)
        if change == "content" and len(calls) == 2:
            with original_open(archive_apk, "ab") as output:
                output.write(b"changed after final hash")
        return value

    def path_open(self, *args, **kwargs):
        if change == "path" and self == archive_apk and len(calls) == 2:
            return original_open(replacement, *args, **kwargs)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(worker, "_digest", digest)
    monkeypatch.setattr(Path, "open", path_open)
    result = analyze(archive_apk, operation="list_entries")
    assert result["code"] == "input_changed" and "items" not in result
    assert len(calls) == 2


def test_path_and_handle_timestamp_semantics_are_not_mixed(archive_apk, monkeypatch):
    query, path_stat = worker._query, Path.stat

    def changed_stat(path, *args, **kwargs):
        info = path_stat(path, *args, **kwargs)
        if path != archive_apk:
            return info
        return SimpleNamespace(
            **{
                name: getattr(info, name) for name in ("st_dev", "st_ino", "st_size", "st_mtime_ns")
            },
            st_ctime_ns=info.st_ctime_ns + 100,
        )

    def queried(*args):
        result = query(*args)
        monkeypatch.setattr(Path, "stat", changed_stat)
        return result

    monkeypatch.setattr(worker, "_query", queried)
    result = analyze(archive_apk, operation="list_entries")
    assert result["status"] == "ok", result


def test_reopened_path_must_still_identify_the_original_file(archive_apk, monkeypatch):
    replacement = archive_apk.with_name("replacement.apk")
    replacement.write_bytes(archive_apk.read_bytes())
    query, path_open = worker._query, Path.open

    def replaced_open(path, *args, **kwargs):
        return path_open(replacement if path == archive_apk else path, *args, **kwargs)

    def queried(*args):
        result = query(*args)
        monkeypatch.setattr(Path, "open", replaced_open)
        return result

    monkeypatch.setattr(worker, "_query", queried)
    result = analyze(archive_apk, operation="list_entries")
    assert result["code"] == "input_changed" and "items" not in result


def test_supervised_worker_scope_and_page_budget(archive_apk, settings):
    service = DroidAscService(replace(settings, max_page_size=2))
    outside = DroidAscService(replace(settings, allowed_roots=(archive_apk.parent / "other",)))
    try:
        result = service.query_archive(str(archive_apk), operation="manifest_summary", limit=100)
        assert result["status"] == "ok" and len(result["items"]) == 2
        assert result["limit"] == 2 and result["next_offset"] == 2
        with pytest.raises(ApkPathError, match="outside allowed roots"):
            outside.query_archive(str(archive_apk), operation="list_entries")
    finally:
        service.close()
        outside.close()


def test_supervised_response_limit(archive_apk, settings):
    runner = DroidAscRunner(replace(settings, max_output_bytes=512))
    result = runner.query_archive(archive_apk, {"operation": "manifest_summary"})
    assert result["status"] == "error" and result["code"] == "response_limit"


def test_archive_entry_limit(archive_apk, monkeypatch):
    monkeypatch.setattr(worker, "MAX_ENTRIES", 1)
    assert analyze(archive_apk, operation="list_entries")["code"] == "entry_limit"


def test_crc_failure_never_returns_content(tmp_path):
    path = tmp_path / "crc.apk"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("entry", b"original-payload")
    path.write_bytes(path.read_bytes().replace(b"original-payload", b"modified-payload"))
    result = analyze(path, operation="read_entry", entry_path="entry")
    assert result["code"] == "invalid_archive" and "content" not in result


def test_decoder_warnings_survive_successful_decode(monkeypatch):
    from axml.axml import AXMLPrinter

    def decode(self, data):
        logging.getLogger("axml").warning("Malformed closing tag repaired")

    monkeypatch.setattr(AXMLPrinter, "__init__", decode)
    monkeypatch.setattr(AXMLPrinter, "is_valid", lambda _: True)
    monkeypatch.setattr(AXMLPrinter, "is_packed", lambda _: False)
    monkeypatch.setattr(AXMLPrinter, "get_xml", lambda _, **kwargs: b"<manifest/>")
    start = struct.pack("<HHI", 0x0102, 16, 36) + bytes(8) + bytes(20)
    end = struct.pack("<HHI", 0x0103, 16, 24) + bytes(8) + bytes(8)
    binary = b"\x03\x00\x08\x00" + struct.pack("<I", 8 + len(start + end)) + start + end
    root, _, warnings = worker.xml_document(binary)
    assert root.tag == "manifest" and warnings == ["decoder_logged_warning_or_error"]


def test_binary_xml_unclosed_and_mismatched_tags_are_rejected():
    start = struct.pack("<HHI", 0x0102, 16, 36) + bytes(8) + bytes(20)
    wrong_end = struct.pack("<HHI", 0x0103, 16, 24) + bytes(8) + struct.pack("<II", 0, 1)
    for chunks in (start, start + wrong_end, start + b"short"):
        binary = b"\x03\x00\x08\x00" + struct.pack("<I", 8 + len(chunks)) + chunks
        with pytest.raises(worker.ArchiveError, match="Binary XML"):
            worker.xml_document(binary)


def test_failed_worker_cleans_parent_owned_storage(archive_apk, settings, monkeypatch):
    runner, requests = DroidAscRunner(settings), []

    def fail(args, **kwargs):
        assert kwargs["module_name"] == "droidasc_mcp.archive_worker"
        path = Path(args[0])
        assert path.is_file()
        requests.append(path)
        raise DroidAscError("Worker timed out")

    monkeypatch.setattr(runner, "_execute", fail)
    with pytest.raises(DroidAscError, match="timed out"):
        runner.query_archive(archive_apk, {"operation": "list_entries"})
    assert len(requests) == 1 and not requests[0].parent.exists()


def test_aapt_oracle_ignores_application_metadata_names(monkeypatch, tmp_path):
    script = Path(__file__).parents[1] / "scripts" / "verify_archive_workflow.py"
    tree = """  E: manifest (line=1)
      E: application (line=2)
          E: activity (line=3)
            A: http://schemas.android.com/apk/res/android:name(0x01010003)=".Main"
              E: meta-data (line=4)
                A: http://schemas.android.com/apk/res/android:name(0x01010003)="inner"
          E: meta-data (line=5)
            A: http://schemas.android.com/apk/res/android:name(0x01010003)="outer"
          E: service (line=6)
            A: http://schemas.android.com/apk/res/android:name(0x01010003)=".Sync"
"""
    monkeypatch.setattr("subprocess.run", lambda *a, **k: SimpleNamespace(stdout=tree))
    tags, components = runpy.run_path(str(script))["aapt_tree"]("aapt2", tmp_path, "manifest")
    assert len(tags) == 6 and components == [("activity", ".Main"), ("service", ".Sync")]
