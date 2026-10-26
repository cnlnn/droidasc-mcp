"""Assert real base/optional preparation selection; never install or select an engine."""

import argparse
import io
import json
import zipfile
import zlib
from importlib import import_module
from importlib.metadata import version
from importlib.util import find_spec
from pathlib import Path


def check_inflate(inflater, profile, native=None):
    payload = b"profile proof: " + bytes(range(256)) * 2
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("proof.bin", payload)
    buffer.seek(0)
    with zipfile.ZipFile(buffer) as archive, inflater.open_member(archive, "proof.bin") as reader:
        decoder = reader._decompressor
        if profile == "preparation":
            decoder = getattr(decoder, "_decoder", None)
            assert type(decoder) is type(native.decompressobj(-15)), "Inflater label is not proof"
        else:
            assert inflater.open_member is zipfile.ZipFile.open
            assert type(decoder) is type(zlib.decompressobj(-15))
        assert reader.read(len(payload) + 1) == payload
        assert reader.read(1) == b""
    return type(decoder).__module__ + "." + type(decoder).__qualname__


def check_profile(profile):
    if profile not in {"base", "preparation"}:
        raise ValueError("Unknown preparation profile")
    backend = import_module("droidasc_mcp._preparation_backend")
    inflater = import_module("droidasc_mcp._preparation_inflate")
    expected_inflate = "zlib-ng" if profile == "preparation" else "stdlib"
    assert expected_inflate == inflater.INFLATE_BACKEND_NAME
    assert backend.ADLER_BACKEND_NAME == "stdlib" and backend.adler32 is zlib.adler32
    observed = {
        "profile": profile,
        "crc": backend.CRC_BACKEND_NAME,
        "adler": backend.ADLER_BACKEND_NAME,
        "inflate": inflater.INFLATE_BACKEND_NAME,
        "product_module": str(Path(backend.__file__).resolve()),
    }
    native = None
    if profile == "base":
        assert find_spec("zlib_ng") is None, "Base profile contaminated by optional dependency"
        assert backend.CRC_BACKEND_NAME == "stdlib" and backend.crc32 is zlib.crc32
    else:
        assert version("zlib-ng") == "1.0.0", "Unexpected optional dependency version"
        package = import_module("zlib_ng")
        native = import_module("zlib_ng.zlib_ng")
        assert package.__version__ == "1.0.0"
        origin = Path(native.__file__).resolve(strict=True)
        assert origin.parent == Path(package.__file__).resolve(strict=True).parent
        assert origin.suffix in {".so", ".pyd"}, "Expected actual optional native module"
        assert backend.CRC_BACKEND_NAME == "zlib-ng", "Optional CRC silently fell back"
        assert backend.crc32 is native.crc32, "CRC implementation differs from reported engine"
        observed.update(optional_version=package.__version__, optional_native=str(origin))
    observed["actual_inflate_decoder"] = check_inflate(inflater, profile, native)
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=("base", "preparation"))
    args = parser.parse_args()
    if not __debug__:
        parser.error("Profile verification requires assertions enabled")
    print(json.dumps(check_profile(args.profile), sort_keys=True))


if __name__ == "__main__":
    main()
