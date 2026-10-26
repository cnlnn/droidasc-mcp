"""Private inflater parity, fail-closed capabilities and untouched normal ZIP I/O."""

import io
import struct
import subprocess
import sys
import zipfile
import zlib
from types import SimpleNamespace

import pytest

from droidasc_mcp import _preparation_inflate as inflater
from droidasc_mcp import preparation_zip


def archive_bytes(compression=zipfile.ZIP_DEFLATED):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=compression) as archive:
        archive.writestr("classes.dex", bytes(range(256)) * 100)
        archive.writestr("assets/end", b"end")
    return stream.getvalue()


@pytest.fixture(params=["forced_adapter", "selected_reader"])
def adapter(request):
    # Exercise the adapter even when the optional dependency is absent. Actual
    # optional-native selection is additionally required by the extra profile.
    return (
        inflater.open_member
        if request.param == "selected_reader"
        else inflater._build_adapter(zlib)
    )


@pytest.mark.parametrize("compression", [zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED])
def test_read_read1_peek_seek_and_eof_match_standard(adapter, compression):
    wire = archive_bytes(compression)
    with (
        zipfile.ZipFile(io.BytesIO(wire)) as archive,
        archive.open("classes.dex") as standard,
        adapter(archive, "classes.dex") as private,
    ):
        for method, argument in [
            ("read", 7),
            ("peek", 13),
            ("read1", 11),
            ("seek", 1),
            ("read", 257),
            ("seek", 17000),
            ("read1", 19),
            ("seek", 0),
            ("read", -1),
            ("read1", 20),
            ("peek", 1),
        ]:
            assert getattr(private, method)(argument) == getattr(standard, method)(argument)
            assert private.tell() == standard.tell()
        assert private.read() == standard.read() == b""


def test_private_reader_retains_current_stdlib_code_and_factory_identity():
    adapter = inflater._build_adapter(zlib)
    with (
        zipfile.ZipFile(io.BytesIO(archive_bytes())) as archive,
        adapter(archive, "classes.dex") as reader,
    ):
        cls = type(reader)
        assert cls is not zipfile.ZipExtFile
        for name in ("__init__", "seek", "_update_crc"):
            actual, expected = getattr(cls, name), getattr(zipfile.ZipExtFile, name)
            assert actual.__code__ is expected.__code__
            assert actual.__defaults__ == expected.__defaults__
            assert actual.__kwdefaults__ == expected.__kwdefaults__
            assert actual.__globals__ is not expected.__globals__
        assert cls._read1 is zipfile.ZipExtFile._read1
        factory = cls.__init__.__globals__["_get_decompressor"].__globals__["zlib"]
        assert factory.decompressobj._implementation is zlib.decompressobj
        assert type(reader._decompressor._decoder) is type(zlib.decompressobj(-15))


def test_adapter_does_not_mutate_module_or_normal_readers_writers():
    before = dict(vars(zipfile))
    methods = (
        zipfile.ZipFile.open,
        zipfile.ZipExtFile.__init__,
        zipfile.ZipExtFile.seek,
        zipfile.ZipExtFile._read1,
        zipfile.ZipExtFile._update_crc,
    )
    adapter = inflater._build_adapter(zlib)
    assert vars(zipfile) == before
    assert methods == (
        zipfile.ZipFile.open,
        zipfile.ZipExtFile.__init__,
        zipfile.ZipExtFile.seek,
        zipfile.ZipExtFile._read1,
        zipfile.ZipExtFile._update_crc,
    )
    target = io.BytesIO()
    with (
        zipfile.ZipFile(target, "w") as archive,
        adapter(archive, "classes.dex", "w") as output,
    ):
        assert type(output) is zipfile._ZipWriteFile
        output.write(b"unchanged normal writer")
    with zipfile.ZipFile(target) as archive, archive.open("classes.dex") as reader:
        assert type(reader) is zipfile.ZipExtFile
        assert reader.read() == b"unchanged normal writer"


def test_backward_seek_recreates_the_selected_decoder():
    calls = []

    def factory(*args, **kwargs):
        calls.append(True)
        return zlib.decompressobj(*args, **kwargs)

    adapter = inflater._build_adapter(SimpleNamespace(decompressobj=factory, error=zlib.error))
    before = len(calls)
    with (
        zipfile.ZipFile(io.BytesIO(archive_bytes())) as archive,
        adapter(archive, "classes.dex") as reader,
    ):
        first = reader._decompressor
        assert reader.read(10000)
        reader.seek(0)
        assert reader._decompressor is not first
        assert reader.read() == bytes(range(256)) * 100
    assert len(calls) == before + 2


def outcome(opener, wire):
    try:
        with (
            zipfile.ZipFile(io.BytesIO(wire)) as archive,
            opener(archive, "classes.dex") as reader,
        ):
            return "ok", reader.read(), reader.read()
    except Exception as exc:
        return "error", type(exc)


@pytest.mark.parametrize("failure", ["crc", "deflate", "truncated", "local_name", "overlap"])
def test_corruption_and_truncation_match_standard(adapter, failure):
    wire = bytearray(archive_bytes())
    first = wire.index(zipfile.stringCentralDir)
    if failure == "crc":
        struct.pack_into("<I", wire, first + 16, 123)
    elif failure == "deflate":
        wire[30 + len("classes.dex")] = 7  # Invalid raw-deflate block type.
    elif failure == "truncated":
        size = struct.unpack_from("<I", wire, first + 20)[0] - 2
        struct.pack_into("<I", wire, first + 20, size)
        struct.pack_into("<I", wire, 18, size)
    elif failure == "local_name":
        wire[30] = ord("x")
    else:
        second = wire.index(zipfile.stringCentralDir, first + 4)
        struct.pack_into("<I", wire, second + 42, 1)
    assert outcome(adapter, wire) == outcome(zipfile.ZipFile.open, wire)


def test_legacy_overlap_guard_still_precedes_private_open(monkeypatch):
    wire = bytearray(archive_bytes())
    first = wire.index(zipfile.stringCentralDir)
    second = wire.index(zipfile.stringCentralDir, first + 4)
    struct.pack_into("<I", wire, second + 42, 1)
    monkeypatch.setattr(preparation_zip, "_MEMBER_BOUNDS", False)

    def forbidden(*args, **kwargs):
        pytest.fail("Overlap must be rejected before the selected member reader")

    with (
        preparation_zip.PreparationZipFile(io.BytesIO(wire)) as archive,
        pytest.raises(zipfile.BadZipFile, match="Overlapped"),
    ):
        monkeypatch.setattr(archive, "_open_member", forbidden)
        archive.read("classes.dex")


@pytest.mark.parametrize("failure", [ImportError("absent"), OSError("unloadable")])
def test_missing_backend_selects_standard_before_input(monkeypatch, failure):
    def unavailable(name):
        raise failure

    monkeypatch.setattr(inflater, "import_module", unavailable)
    selected, name, _ = inflater._select_adapter()
    assert selected is zipfile.ZipFile.open and name == "stdlib"


def test_unpinned_backend_is_not_imported(monkeypatch):
    calls = []

    def imported(name):
        calls.append(name)
        return SimpleNamespace(__version__="not-pinned")

    monkeypatch.setattr(inflater, "import_module", imported)
    assert inflater._select_adapter()[0] is zipfile.ZipFile.open
    assert calls == ["zlib_ng"]


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(9)])
def test_selection_does_not_swallow_process_control(monkeypatch, error):
    def stopped(name):
        raise error

    monkeypatch.setattr(inflater, "import_module", stopped)
    with pytest.raises(type(error)):
        inflater._select_adapter()


@pytest.mark.parametrize("name", ["__init__", "seek", "_read1", "_update_crc"])
def test_unrecognized_stdlib_function_is_rejected_before_input(monkeypatch, name):
    original = getattr(zipfile.ZipExtFile, name)

    def changed(*args, **kwargs):
        return original(*args, **kwargs)

    monkeypatch.setattr(zipfile.ZipExtFile, name, changed)
    with pytest.raises(ValueError, match="Unrecognized stdlib"):
        inflater._build_adapter(zlib)


def test_mutated_stdlib_checksum_binding_is_rejected(monkeypatch):
    monkeypatch.setattr(zipfile, "crc32", lambda *args: 0)
    with pytest.raises(ValueError, match="checksum bindings"):
        inflater._build_adapter(zlib)


def test_incompatible_decoder_preflight_falls_back(monkeypatch):
    candidate = SimpleNamespace(error=zlib.error, decompressobj=lambda *args: object())
    monkeypatch.setattr(
        inflater,
        "import_module",
        lambda name: SimpleNamespace(__version__="1.0.0") if name == "zlib_ng" else candidate,
    )
    selected, name, _ = inflater._select_adapter()
    assert selected is zipfile.ZipFile.open and name == "stdlib"


@pytest.mark.parametrize("error", [RuntimeError("runtime failure"), MemoryError("allocation")])
def test_actual_stream_failure_propagates_without_retry(error):
    state = {"fail": False, "calls": 0}

    class Decoder:
        def __init__(self, *args, **kwargs):
            self.raw = zlib.decompressobj(*args, **kwargs)

        def __getattr__(self, name):
            return getattr(self.raw, name)

        def decompress(self, *args, **kwargs):
            if state["fail"]:
                state["calls"] += 1
                raise error
            return self.raw.decompress(*args, **kwargs)

    adapter = inflater._build_adapter(SimpleNamespace(decompressobj=Decoder, error=zlib.error))
    with (
        zipfile.ZipFile(io.BytesIO(archive_bytes())) as archive,
        adapter(archive, "classes.dex") as reader,
    ):
        state["fail"] = True
        with pytest.raises(type(error), match=str(error)):
            reader.read(20)
    assert state["calls"] == 1


def test_only_backend_decompression_errors_are_normalized():
    class BackendError(Exception):
        pass

    class Broken:
        def decompress(self, *args):
            raise BackendError("invalid compressed input")

        def flush(self, *args):
            raise KeyError("not a decompression error")

    decoder = inflater._Decoder(Broken(), BackendError)
    with pytest.raises(zlib.error, match="invalid compressed input"):
        decoder.decompress(b"input", 7)
    with pytest.raises(KeyError, match="not a decompression error"):
        decoder.flush()


def test_open_clone_preserves_keyword_defaults():
    copied = inflater._clone(zipfile.ZipFile.open, {"ZipExtFile": zipfile.ZipExtFile})
    assert copied.__code__ is zipfile.ZipFile.open.__code__
    assert copied.__defaults__ == zipfile.ZipFile.open.__defaults__
    assert copied.__kwdefaults__ == zipfile.ZipFile.open.__kwdefaults__
    assert copied.__kwdefaults__ is not zipfile.ZipFile.open.__kwdefaults__


def test_mislabeled_standard_reader_is_not_native_identity(monkeypatch):
    monkeypatch.setattr(inflater, "INFLATE_BACKEND_NAME", "zlib-ng")
    with (
        zipfile.ZipFile(io.BytesIO(archive_bytes())) as archive,
        zipfile.ZipFile.open(archive, "classes.dex") as reader,
    ):
        assert not isinstance(reader._decompressor, inflater._Decoder)
        assert not hasattr(reader._decompressor, "_decoder")


def test_importing_inventory_class_does_not_select_optional_backend():
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; from droidasc_mcp import preparation_zip; "
                "assert 'droidasc_mcp._preparation_inflate' not in sys.modules; "
                "assert 'zlib_ng' not in sys.modules"
            ),
        ],
        check=True,
        capture_output=True,
        timeout=10,
    )


@pytest.mark.parametrize("name", ["classes.dex", "missing"])
def test_closed_archive_error_precedes_member_lookup(adapter, name):
    archive = zipfile.ZipFile(io.BytesIO(archive_bytes()))
    archive.close()
    with pytest.raises(ValueError, match="closed"):
        adapter(archive, name)
