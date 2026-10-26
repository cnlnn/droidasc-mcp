"""Private preparation readers using unchanged, capability-checked stdlib code."""

import zipfile
import zlib
from importlib import import_module
from types import FunctionType, SimpleNamespace

from ._preparation_backend import _PINNED_VERSION, crc32


class _Decoder:
    def __init__(self, decoder, error):
        self._decoder, self._error = decoder, error

    def __getattr__(self, name):
        return getattr(self._decoder, name)

    def decompress(self, *args, **kwargs):
        try:
            return self._decoder.decompress(*args, **kwargs)
        except self._error as exc:
            raise zlib.error(*exc.args) from exc

    def flush(self, *args, **kwargs):
        try:
            return self._decoder.flush(*args, **kwargs)
        except self._error as exc:
            raise zlib.error(*exc.args) from exc


def _trace(factory, wire):
    decoder = factory(-15)
    pending, rows = wire, []
    for _ in range(2048):
        data = decoder.decompress(pending, 73)
        tail, unused, eof = decoder.unconsumed_tail, decoder.unused_data, decoder.eof
        if (
            type(data) is not bytes
            or len(data) > 73
            or type(tail) is not bytes
            or len(tail) > len(wire)
            or type(unused) is not bytes
            or len(unused) > len(wire)
            or type(eof) is not bool
        ):
            raise ValueError("Incompatible bounded inflater output")
        rows.append((data, tail, unused, eof))
        pending = tail
        if eof or (not pending and not data):
            break
    else:
        raise ValueError("Inflater preflight did not terminate")
    final = decoder.flush()
    if type(final) is not bytes or len(final) > 8192:
        raise ValueError("Incompatible inflater flush")
    return rows, final, decoder.eof, decoder.unused_data


def _checked_factory(candidate):
    error = candidate.error
    decompressobj = candidate.decompressobj
    if not isinstance(error, type) or not issubclass(error, Exception) or error is Exception:
        raise ValueError("Missing specific inflater error type")

    def factory(*args, **kwargs):
        return _Decoder(decompressobj(*args, **kwargs), error)

    factory._implementation = decompressobj

    compressor = zlib.compressobj(wbits=-15)
    wire = compressor.compress(bytes(range(256)) * 32) + compressor.flush()
    for sample in (wire, wire + b"trailing", wire[:-1], b""):
        if _trace(factory, sample) != _trace(zlib.decompressobj, sample):
            raise ValueError("Inflater preflight differs from stdlib")
    try:
        factory(-15).decompress(b"\x07", 73)
    except zlib.error:
        pass
    else:
        raise ValueError("Inflater accepted an invalid deflate block")
    return factory


def _clone(function, replacements):
    if (
        type(function) is not FunctionType
        or function.__globals__ is not vars(zipfile)
        or function.__module__ != "zipfile"
        or function.__closure__
        or function.__code__.co_freevars
        or not replacements.keys() <= set(function.__code__.co_names)
    ):
        raise ValueError("Unrecognized stdlib reader function")
    namespace = {**function.__globals__, **replacements}
    copied = FunctionType(function.__code__, namespace, function.__name__, function.__defaults__)
    copied.__kwdefaults__ = function.__kwdefaults__.copy() if function.__kwdefaults__ else None
    return copied


def _build_adapter(candidate):
    if zipfile.zlib is not zlib or zipfile.crc32 is not zlib.crc32:
        raise ValueError("Unrecognized stdlib checksum bindings")
    read1 = zipfile.ZipExtFile._read1
    allowed = {
        "_eof",
        "_compress_type",
        "ZIP_DEFLATED",
        "_decompressor",
        "unconsumed_tail",
        "len",
        "_read2",
        "ZIP_STORED",
        "_compress_left",
        "max",
        "MIN_READ_SIZE",
        "decompress",
        "eof",
        "flush",
        "_left",
        "_update_crc",
    }
    _clone(read1, {})
    required = {"_decompressor", "unconsumed_tail", "decompress", "eof", "flush", "_update_crc"}
    names = set(read1.__code__.co_names)
    if not required <= names <= allowed:
        raise ValueError("Unrecognized stdlib decompressor protocol")
    _clone(zipfile._check_compression, {})
    factory = _checked_factory(candidate)
    proxy = SimpleNamespace(**{**vars(zlib), "decompressobj": factory})
    decompress = _clone(zipfile._get_decompressor, {"zlib": proxy})
    local_type = type(
        "_PreparationZipExtFile",
        (zipfile.ZipExtFile,),
        {
            "__init__": _clone(
                zipfile.ZipExtFile.__init__,
                {
                    "_get_decompressor": decompress,
                    "crc32": crc32,
                },
            ),
            "seek": _clone(zipfile.ZipExtFile.seek, {"_get_decompressor": decompress}),
            "_update_crc": _clone(zipfile.ZipExtFile._update_crc, {"crc32": crc32}),
        },
    )
    adapted = _clone(zipfile.ZipFile.open, {"ZipExtFile": local_type})
    original = zipfile.ZipFile.open

    def open_member(archive, name, mode="r", pwd=None, *, force_zip64=False):
        if mode != "r" or not archive.fp:
            return original(archive, name, mode, pwd, force_zip64=force_zip64)
        info = name if isinstance(name, zipfile.ZipInfo) else archive.getinfo(name)
        if (
            info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
            or info.flag_bits & 1
        ):
            return original(archive, name, mode, pwd, force_zip64=force_zip64)
        return adapted(archive, name, mode, pwd, force_zip64=force_zip64)

    return open_member


def _select_adapter():
    try:
        if import_module("zlib_ng").__version__ != _PINNED_VERSION:
            return zipfile.ZipFile.open, "stdlib", "optional backend unavailable or unpinned"
        adapter = _build_adapter(import_module("zlib_ng.zlib_ng"))
        return adapter, "zlib-ng", "bounded inflater and stdlib capability preflight passed"
    except Exception:
        # Selection occurs before the optional member decoder consumes input. Actual stream
        # failures propagate; they never fall back and retry consumed input.
        return zipfile.ZipFile.open, "stdlib", "optional inflater unavailable or incompatible"


open_member, INFLATE_BACKEND_NAME, INFLATE_BACKEND_REASON = _select_adapter()
