"""Capability routing, safe snapshots and container provenance."""

import hashlib
import io
import threading
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


@pytest.mark.parametrize("kind", ["apk", "aar"])
def test_preparation_releases_validated_resource_inventory_before_dex_reads(
    settings, tmp_path, monkeypatch, kind
):
    from droidasc_mcp.containers import selected_dex
    from droidasc_mcp.preparation_zip import PreparationZipFile

    observed = []
    initialize = PreparationZipFile.__init__

    def capture(self, *args):
        initialize(self, *args)
        observed.append(self)

    monkeypatch.setattr(PreparationZipFile, "__init__", capture)
    dex = b"unchanged DEX bytes"
    code = (
        ("classes.dex", dex)
        if kind == "apk"
        else ("classes.jar", zip_bytes([("classes.dex", dex)]))
    )
    path = tmp_path / f"resources.{kind}"
    path.write_bytes(zip_bytes([code, *[(f"res/raw/{i}.bin", b"resource") for i in range(5000)]]))
    with selected_dex(settings, path, 1024**2, None) as (inputs, metadata):
        root = observed[0]
        assert root.inventory == {}, (
            "Validated resource names must not overlap live DEX/class buffers"
        )
        selected = list(inputs)
        assert len(selected) == 1 and metadata["dex_analysis"]
        reader, info, origin = selected[0]
        assert origin == ("classes.dex" if kind == "apk" else "classes.jar!/classes.dex")
        with reader.open(info) as stream:
            assert stream.read() == dex


@pytest.mark.parametrize("streaming", [False, True])
def test_snapshot_decompresses_two_entries_concurrently_with_exact_bytes(
    settings, tmp_path, monkeypatch, streaming
):
    from droidasc_mcp.containers import prefetched_entries, selected_dex, snapshot

    originals = {"classes.dex": b"first" * 200000, "classes2.dex": b"second" * 200000}
    data = zip_bytes(list(originals.items()))
    path = tmp_path / "parallel.apk"
    path.write_bytes(data)
    root = tmp_path / "snapshot"
    root.mkdir()
    rendezvous = threading.Barrier(2, timeout=3)
    lock = threading.Lock()
    started = set()
    original_read = zipfile.ZipExtFile.read

    def read(stream, count=-1):
        assert 0 < count <= 256 * 1024, "Concurrent extraction buffers must be bounded"
        with lock:
            first = stream.name in originals and stream.name not in started
            started.add(stream.name)
        if first:
            rendezvous.wait()
        return original_read(stream, count)

    monkeypatch.setattr(zipfile.ZipExtFile, "read", read)
    if streaming:
        actual = {}
        with (
            selected_dex(settings, path, 4 * 1024**2, None) as (inputs, metadata),
            prefetched_entries(inputs) as streams,
        ):
            for source, _, name in streams:
                chunks = []
                while block := source.read(256 * 1024):
                    chunks.append(block)
                actual[name] = b"".join(chunks)
        assert actual == originals
    else:
        paths, origins, metadata = snapshot(settings, path, root, 4 * 1024**2, None)
        assert dict(zip(origins, (item.read_bytes() for item in paths), strict=True)) == originals
    assert metadata["artifact_sha256"] == hashlib.sha256(data).hexdigest()
    assert path.read_bytes() == data


def test_preparation_validates_first_entry_before_remaining_decompression_finishes(
    settings, tmp_path, monkeypatch
):
    from test_dex import empty_dex

    from droidasc_mcp import dex_worker
    from droidasc_mcp.runner import DroidAscRunner

    dex = bytes(empty_dex())
    data = zip_bytes([("classes.dex", dex), ("classes2.dex", dex)])
    artifact = tmp_path / "pipeline.apk"
    artifact.write_bytes(data)
    root = tmp_path / "preparation"
    root.mkdir()
    first_validated = threading.Event()
    original_read, original_copy = zipfile.ZipExtFile.read, dex_worker.copy_dex_stream

    def read(stream, count=-1):
        if stream.name == "classes2.dex":
            assert first_validated.wait(3), "Validate each DEX before advancing to the next entry"
        return original_read(stream, count)

    def copy(source, *args):
        result = original_copy(source, *args)
        if source.name == "classes.dex":
            first_validated.set()
        return result

    monkeypatch.setattr(zipfile.ZipExtFile, "read", read)
    monkeypatch.setattr(dex_worker, "copy_dex_stream", copy)
    request = DroidAscRunner(settings)._dex_request([], {"offset": 0, "limit": 10})
    request.update(artifact_path=str(artifact), max_uncompressed_bytes=1024**2, prepare=True)
    result = dex_worker.analyze(request, root)
    assert result["status"] == "ok", result
    assert result["artifact_sha256"] == hashlib.sha256(data).hexdigest()
    assert [row["container_entry"] for row in result["sources"]] == ["classes.dex", "classes2.dex"]
    assert all(row["sha256"] == hashlib.sha256(dex).hexdigest() for row in result["sources"])
    assert not list(root.glob("import-*.dex"))
    assert not list(root.glob("dex-container-*"))
    assert artifact.read_bytes() == data


def test_standard_container_preparation_never_materializes_raw_dex(settings, tmp_path, monkeypatch):
    from test_dex import empty_dex

    from droidasc_mcp import dex_worker
    from droidasc_mcp.runner import DroidAscRunner

    artifact = tmp_path / "streamed.apk"
    dex = bytes(empty_dex())
    artifact.write_bytes(zip_bytes([("classes.dex", dex)]))
    root = tmp_path / "streamed"
    root.mkdir()

    def forbidden(*args, **kwargs):
        pytest.fail("Standard archive DEX must be validated directly from the entry stream")

    monkeypatch.setattr(dex_worker, "copy_dex", forbidden)
    request = DroidAscRunner(settings)._dex_request([], {"offset": 0, "limit": 10})
    request.update(artifact_path=str(artifact), max_uncompressed_bytes=1024**2, prepare=True)
    result = dex_worker.analyze(request, root)
    assert result["status"] == "ok", result
    assert result["sources"][0]["sha256"] == hashlib.sha256(dex).hexdigest()
    assert not list(root.glob("import-*.dex"))
    assert not list(root.glob("dex-container-*"))


@pytest.mark.parametrize("nested", [False, True])
def test_preparation_never_constructs_full_resource_zipinfo_inventory(
    settings, tmp_path, monkeypatch, nested
):
    from test_dex import empty_dex

    from droidasc_mcp import containers, dex_worker
    from droidasc_mcp.runner import DroidAscRunner

    data = zip_bytes(
        [("classes.dex", bytes(empty_dex()))]
        + [(f"res/raw/{number}.bin", b"resource") for number in range(100)]
    )
    path = tmp_path / ("compact.aar" if nested else "compact.apk")
    path.write_bytes(zip_bytes([("classes.jar", data)]) if nested else data)
    root = tmp_path / "compact-preparation"
    root.mkdir()

    def forbidden(*args, **kwargs):
        pytest.fail("Preparation must use checked compact inventories, including nested JARs")

    monkeypatch.setattr(containers, "_entries", forbidden)
    request = DroidAscRunner(settings)._dex_request([], {"offset": 0, "limit": 10})
    request.update(artifact_path=str(path), max_uncompressed_bytes=1024**2, prepare=True)
    result = dex_worker.analyze(request, root)
    assert result["status"] == "ok", result
    assert result["class_count"] == 0
    assert result["artifact_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["sources"][0]["container_entry"] == (
        "classes.jar!/classes.dex" if nested else "classes.dex"
    )


@pytest.mark.parametrize("failure", [False, True])
def test_prefetch_preserves_bytes_and_late_error_without_leaking_threads(failure):
    from droidasc_mcp.containers import prefetched

    data = b"0123456789" * 90000

    class Source(io.BytesIO):
        name = "bounded.dex"

        def read(self, count):
            assert count == 256 * 1024
            block = super().read(count)
            if not block and failure:
                raise zipfile.BadZipFile("late CRC failure")
            return block

    with Source(data) as source, prefetched(source) as stream:
        result = stream.read(112)
        while len(result) < len(data):
            result += stream.read(min(256 * 1024, len(data) - len(result)))
        assert result == data
        if failure:
            with pytest.raises(zipfile.BadZipFile, match="late CRC"):
                stream.read(1)
        else:
            assert stream.read(1) == b""
    assert not any(thread.name == "droidasc-dex-prefetch" for thread in threading.enumerate())


def test_prefetch_consumer_failure_stops_a_full_queue():
    from droidasc_mcp.containers import prefetched

    class Source(io.BytesIO):
        name = "abandoned.dex"

    with (
        pytest.raises(RuntimeError, match="stop consumer"),
        Source(b"x" * 1024**2) as source,
        prefetched(source),
    ):
        raise RuntimeError("stop consumer")
    assert not any(thread.name == "droidasc-dex-prefetch" for thread in threading.enumerate())


def test_prefetch_full_chunks_are_transferred_without_copying():
    from droidasc_mcp.containers import prefetched

    block = b"x" * (256 * 1024)

    class Source:
        name = "owned.dex"
        emitted = False

        def read(self, count):
            if self.emitted:
                return b""
            self.emitted = True
            return block

    with prefetched(Source()) as stream:
        assert stream.read(len(block)) is block
        assert stream.read(1) == b""


@pytest.mark.parametrize("consume_block", [False, True])
def test_abandoned_prefetched_entries_bound_both_queues_and_join_threads(consume_block):
    from types import SimpleNamespace

    from droidasc_mcp.containers import prefetched_entries

    queued = {name: threading.Event() for name in ("first.dex", "second.dex")}
    sources = []
    block = b"x" * (256 * 1024)

    class Source(io.BytesIO):
        def __init__(self, name):
            super().__init__(block * 8)
            self.name, self.reads = name, 0

        def read(self, count):
            assert 0 < count <= len(block)
            self.block_size = count
            self.reads += 1
            if self.reads == 2:
                queued[self.name].set()
            return super().read(count)

    class Archive:
        def open(self, info):
            source = Source(info.filename)
            sources.append(source)
            return source

    inputs = [(Archive(), SimpleNamespace(filename=name), name) for name in queued]
    with (
        pytest.raises(RuntimeError, match="abandon both"),
        prefetched_entries(inputs) as entries,
    ):
        assert all(event.wait(3) for event in queued.values())
        assert [source.reads for source in sources] == [2, 2]
        if consume_block:
            stream, _, _ = next(entries)
            assert stream.read(len(block)) == block[: sources[0].block_size]
        raise RuntimeError("abandon both")
    assert all(source.closed for source in sources)
    assert sources[0].reads <= (3 if consume_block else 2)
    assert sources[1].reads == 2
    assert not any(thread.name == "droidasc-dex-prefetch" for thread in threading.enumerate())


def test_capability_routes_do_not_duplicate_resource_inventory():
    from droidasc_mcp.containers import capabilities

    data = zip_bytes([("classes.dex", b"dex"), ("res/large.bin", b"resource")])
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = {info.filename: info for info in archive.infolist()}
        metadata, _, nested, active, _, _ = capabilities(archive, entries, "apk", None, 1024)
        try:
            assert set(active) == {"classes.dex"}
            assert metadata["dex_entries"] == ["classes.dex"]
        finally:
            nested.close()


def test_nested_resource_entries_still_count_toward_inventory_limit():
    from droidasc_mcp.archive_errors import ArchiveError
    from droidasc_mcp.containers import capabilities

    data = zip_bytes([("classes.jar", zip_bytes([("resource.txt", b"x")]))])
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        info = archive.getinfo("classes.jar")
        entries = dict.fromkeys((f"res/{index}" for index in range(99999)), info)
        entries["classes.jar"] = info
        with pytest.raises(ArchiveError, match="inventory exceeds"):
            capabilities(archive, entries, "aar", None, 1024)


@pytest.mark.parametrize("failure", ["input_changed", "invalid_container"])
def test_pipelined_failure_never_reports_ready(settings, tmp_path, monkeypatch, failure):
    from test_dex import empty_dex

    from droidasc_mcp import dex_worker
    from droidasc_mcp.runner import DroidAscRunner

    artifact = tmp_path / "failed-pipeline.apk"
    artifact.write_bytes(zip_bytes([("classes.dex", bytes(empty_dex()))]))
    root = tmp_path / "failed"
    root.mkdir()
    original_copy = dex_worker.copy_dex_stream
    progress = []

    def copy(*args):
        record = original_copy(*args)
        if failure == "input_changed":
            with artifact.open("ab") as output:
                output.write(b"changed-after-copy")
        else:
            raise zipfile.BadZipFile("injected archive failure after first copy")
        return record

    monkeypatch.setattr(dex_worker, "copy_dex_stream", copy)
    monkeypatch.setattr(dex_worker, "preparation_progress", lambda *args: progress.append(args))
    request = DroidAscRunner(settings)._dex_request([], {"offset": 0, "limit": 10})
    request.update(artifact_path=str(artifact), max_uncompressed_bytes=1024**2, prepare=True)
    result = dex_worker.analyze(request, root)
    assert result["status"] == "error" and result["code"] == failure, result
    assert not any("ready" in row[-1] for row in progress)
    assert not (root / "prepared.json").exists()
    assert not (root / "owners.sqlite").exists()


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
