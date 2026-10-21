"""Capability routing, safe snapshots and container provenance."""

import hashlib
import io
import zipfile
from dataclasses import replace

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService


def zip_bytes(entries):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return stream.getvalue()


@pytest.fixture
def container_service(tmp_path):
    service = DroidAscService(
        replace(Settings.from_env(), allowed_roots=(tmp_path,), timeout_seconds=90)
    )
    try:
        yield service
    finally:
        service.close()


@pytest.mark.parametrize("kind", ["apk", "jar", "aar", "aab"])
def test_container_capability_snapshot_hash_and_original_entry(
    container_service, review_dex_files, tmp_path, kind
):
    dex = review_dex_files[0].read_bytes()
    origin = "base/dex/classes.dex" if kind == "aab" else "classes.dex"
    data = zip_bytes([(origin, dex)])
    if kind == "aar":
        data = zip_bytes([("classes.jar", data), ("AndroidManifest.xml", b"<manifest/>")])
        origin = "classes.jar!/classes.dex"
    path = tmp_path / ("input." + kind)
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    inventory = container_service.inspect_artifact(str(path), offset=0, limit=1)
    assert inventory["status"] == "ok", inventory
    assert inventory["artifact_sha256"] == digest
    assert inventory["dex_analysis"] and inventory["dex_entries"] == [origin]
    opened = container_service.open_artifact_session(str(path))
    assert opened["status"] == "ok", opened
    assert opened["artifact_sha256"] == digest and opened["artifact_kind"] == kind
    assert opened["sources"][0]["container_entry"] == origin
    assert opened["sources"][0]["path"] == str(path)
    assert opened["sources"][0]["sha256"] == hashlib.sha256(dex).hexdigest()
    path.write_bytes(b"replaced original")
    result = container_service.query_dex_session(
        opened["session_id"], operation="list_classes", prefix=None, threads=1, offset=0, limit=100
    )
    assert result["status"] == "ok" and result["items"][0]["class_name"] == "Lreview/C;"
    assert result["artifact_sha256"] == digest
    container_service.sessions.close(opened["session_id"])
    assert not container_service.sessions.entries


@pytest.mark.parametrize("kind", ["jar", "aar", "apks", "xapk"])
def test_inventory_only_inputs_never_silently_decompile(container_service, tmp_path, kind):
    if kind in {"jar", "aar"}:
        entries = [("pkg/Example.class", b"\xca\xfe\xba\xbe")]
        data = zip_bytes(entries)
        if kind == "aar":
            data = zip_bytes([("classes.jar", data)])
    else:
        data = zip_bytes([("splits/base.apk", zip_bytes([("classes.dex", b"dex")]))])
    path = tmp_path / ("inventory." + kind)
    path.write_bytes(data)
    inventory = container_service.inspect_artifact(str(path), offset=0, limit=100)
    assert inventory["status"] == "ok" and not inventory["dex_analysis"]
    assert inventory["jvm_class_count"] == (1 if kind in {"jar", "aar"} else 0)
    assert not inventory["jvm_decompilation"] and not inventory["split_reconstruction"]
    result = container_service.open_artifact_session(str(path))
    assert result["code"] == "no_analyzable_dex"
    assert not container_service.sessions.entries and container_service.sessions.reserved == 0


def test_aab_exact_module_selection_and_duplicate_diagnostics(
    container_service, review_dex_files, tmp_path
):
    dex = review_dex_files[0].read_bytes()
    path = tmp_path / "modules.aab"
    path.write_bytes(zip_bytes([("base/dex/classes.dex", dex), ("feature/dex/classes.dex", dex)]))
    info = container_service.inspect_artifact(str(path))
    assert info["modules"] == ["base", "feature"]
    assert info["dex_entries"] == ["base/dex/classes.dex"]
    chosen = container_service.open_artifact_session(str(path), module="feature")
    assert (
        chosen["status"] == "ok"
        and chosen["sources"][0]["container_entry"] == "feature/dex/classes.dex"
    )
    path = tmp_path / "duplicates.jar"
    path.write_bytes(zip_bytes([("classes.dex", dex), ("classes2.dex", dex)]))
    assert container_service.open_artifact_session(str(path))["code"] == "duplicate_class"
    assert (
        container_service.open_artifact_session(str(path), module="base")["code"] == "invalid_query"
    )


@pytest.mark.parametrize("name", ["../classes.dex", "/classes.dex", "x/../classes.dex"])
def test_unsafe_archive_names_rejected(container_service, tmp_path, name):
    path = tmp_path / "unsafe.jar"
    path.write_bytes(zip_bytes([(name, b"data")]))
    assert container_service.inspect_artifact(str(path))["code"] == "unsafe_entry"


def test_nested_archive_expansion_budget_and_malformed_input(container_service, tmp_path):
    path = tmp_path / "huge.aar"
    path.write_bytes(zip_bytes([("classes.jar", b"0" * 4096)]))
    assert (
        container_service.inspect_artifact(str(path), max_uncompressed_bytes=10)["code"]
        == "container_limit"
    )
    assert (
        container_service.open_artifact_session(str(path), max_uncompressed_bytes=10)["code"]
        == "container_limit"
    )
    assert container_service.inspect_artifact(str(path))["code"] == "invalid_archive"
    path.write_bytes(zip_bytes([("classes.jar", zip_bytes([("../classes.dex", b"x")]))]))
    assert container_service.open_artifact_session(str(path))["code"] == "unsafe_entry"
    path.write_bytes(b"not a ZIP")
    assert container_service.open_artifact_session(str(path))["code"] == "invalid_container"


@pytest.mark.parametrize("kind", ["apk", "jar", "zip", "aar", "apks", "xapk", "aab"])
def test_arbitrary_direct_dex_paths(container_service, review_dex_files, tmp_path, kind):
    origin = "payload/nested/CUSTOM.DEX"
    if kind == "aab":
        origin = "base/dex/" + origin
    path = tmp_path / ("nonstandard." + kind)
    path.write_bytes(zip_bytes([(origin, review_dex_files[0].read_bytes())]))
    info = container_service.inspect_artifact(str(path))
    assert info["status"] == "ok" and info["dex_entries"] == [origin]
    opened = container_service.open_artifact_session(str(path))
    assert opened["status"] == "ok", opened
    assert opened["sources"][0]["container_entry"] == origin


def test_aar_direct_and_nested_dex_share_one_budget(container_service, review_dex_files, tmp_path):
    first, second = (path.read_bytes() for path in review_dex_files[:2])
    nested = zip_bytes([("nested/custom.dex", second)])
    path = tmp_path / "combined.aar"
    path.write_bytes(zip_bytes([("direct.dex", first), ("classes.jar", nested)]))
    info = container_service.inspect_artifact(str(path))
    assert info["dex_entries"] == ["classes.jar!/nested/custom.dex", "direct.dex"]
    # These two revisions deliberately overlap declarations, so both must be validated.
    assert container_service.open_artifact_session(str(path))["code"] == "duplicate_class"
    result = container_service.open_artifact_session(
        str(path), max_uncompressed_bytes=len(nested) + len(first) + len(second) - 1
    )
    assert result["code"] == "container_limit"


def test_nonstandard_dex_is_validated_not_silently_skipped(container_service, tmp_path):
    path = tmp_path / "invalid.zip"
    path.write_bytes(zip_bytes([("assets/hidden.dex", b"not a dex")]))
    assert container_service.inspect_artifact(str(path))["dex_analysis"]
    assert container_service.open_artifact_session(str(path))["status"] == "error"
    assert not container_service.sessions.entries


def test_aar_ambiguous_provenance_rejected(container_service, review_dex_files, tmp_path):
    dex = review_dex_files[0].read_bytes()
    path = tmp_path / "ambiguous.aar"
    path.write_bytes(
        zip_bytes([("classes.jar!/x.dex", dex), ("classes.jar", zip_bytes([("x.dex", dex)]))])
    )
    assert container_service.inspect_artifact(str(path))["code"] == "ambiguous_entry"
    assert container_service.open_artifact_session(str(path))["code"] == "ambiguous_entry"
    assert not container_service.sessions.entries


def test_nested_jar_class_inventory_and_revision_diff(container_service, tmp_path):
    old, new = tmp_path / "old.zip", tmp_path / "new.zip"
    old.write_bytes(
        zip_bytes(
            [
                ("a/Keep.CLASS", b"class"),
                ("libs/one.jar", zip_bytes([("p/Removed.class", b"class")])),
            ]
        )
    )
    new.write_bytes(
        zip_bytes(
            [("a/Keep.CLASS", b"class"), ("libs/two.jar", zip_bytes([("p/Added.class", b"class")]))]
        )
    )
    inventory = container_service.inspect_artifact(str(old))
    assert inventory["status"] == "ok", inventory
    assert inventory["jvm_class_count"] == 2
    assert {row["class_name"] for row in inventory["items"]} == {"La/Keep;", "Lp/Removed;"}
    result = container_service.inspect_artifact(str(old), compare_to=str(new))
    assert result["status"] == "ok", result
    assert result["counts"] == {"added": 1, "removed": 1, "common": 1}
    assert result["items"] == [
        {"class_name": "Lp/Added;", "change": "added"},
        {"class_name": "Lp/Removed;", "change": "removed"},
    ]
    assert result["new_artifact_sha256"] == hashlib.sha256(new.read_bytes()).hexdigest()
    assert not result["dex_comparison_required"]
    filtered = container_service.inspect_artifact(
        str(old), class_query="REMOVED", class_prefix="p."
    )
    assert filtered["total"] == 1
    assert filtered["items"][0]["class_name"] == "Lp/Removed;"


def test_generic_archive_reads_all_bytes_with_paging(container_service, tmp_path):
    import base64

    data = bytes(range(256)) * 4097
    path = tmp_path / "resources.jar"
    path.write_bytes(
        zip_bytes([("data.bin", data), ("AndroidManifest.xml", b"<manifest package='oracle'/>")])
    )
    chunks, offset = [], 0
    while True:
        result = container_service.query_archive(
            str(path),
            operation="read_entry",
            entry_path="data.bin",
            max_bytes=131072,
            byte_offset=offset,
        )
        assert result["status"] in {"ok", "partial"}, result
        assert result["artifact_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
        chunks.append(base64.b64decode(result["content"]))
        if result["content_complete"]:
            break
        assert result["next_byte_offset"] > offset
        offset = result["next_byte_offset"]
    assert b"".join(chunks) == data
    eof = container_service.query_archive(
        str(path), operation="read_entry", entry_path="data.bin", byte_offset=len(data) + 1
    )
    assert eof["content_complete"] and eof["next_byte_offset"] is None
    manifest = container_service.query_archive(
        str(path), operation="manifest_xml", offset=0, limit=100
    )
    assert manifest["status"] == "ok" and 'package="oracle"' in manifest["xml"]
