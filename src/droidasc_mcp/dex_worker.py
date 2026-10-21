"""Validate DEX inputs and run the public ASC entry point inside one supervised worker."""

from __future__ import annotations

import hashlib
import io
import json
import runpy
import struct
import sys
import zipfile
import zlib
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from .config import Settings
from .runner import DroidAscError, DroidAscRunner, _clean_error


class DexInputError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class BoundedText(io.StringIO):
    def __init__(self, budget: int):
        super().__init__()
        self.budget = budget
        self.used = 0

    def write(self, value: str) -> int:
        self.used += len(value.encode("utf-8", errors="replace"))
        if self.used > self.budget:
            raise DroidAscError("CLI output exceeds configured stream limit")
        return super().write(value)


class PublicCliRunner(DroidAscRunner):
    """The outer supervisor already enforces process, memory, time and output limits."""

    def _execute(self, args: list[str], *, module_name: str | None = None) -> bytes:
        assert module_name is None
        argv = sys.argv
        with (
            BoundedText(self.settings.max_output_bytes) as output,
            BoundedText(65536) as errors,
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            sys.argv = ["droidasc", *args]
            try:
                runpy.run_module("droidasc", run_name="__main__")
            except SystemExit as exc:
                if exc.code:
                    raise DroidAscError(_clean_error(errors.getvalue()) or "ASC failed") from None
            finally:
                sys.argv = argv
            return output.getvalue().encode("utf-8", errors="replace")


def _identity(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def copy_dex(source: Path, archive: zipfile.ZipFile, entry: str, budget: int) -> dict:
    """Stream-copy exact bytes, validating the standard header and integrity fields."""
    before = source.stat()
    if before.st_size > budget:
        raise DexInputError("input_limit", "Combined DEX size exceeds configured size limit")
    with source.open("rb") as handle:
        header = handle.read(112)
        if len(header) < 112:
            raise DexInputError("truncated_dex", f"DEX header is truncated: {source.name}")
        if header[:4] != b"dex\n" or header[7] != 0:
            raise DexInputError("invalid_magic", f"Expected a standard DEX header: {source.name}")
        version = header[4:7].decode("ascii", errors="replace")
        if version not in {"035", "037", "038", "039", "040"}:
            raise DexInputError("unsupported_dex", f"Unsupported DEX version: {version}")
        size, header_size, endian = struct.unpack_from("<III", header, 32)
        if header_size != 112 or endian != 0x12345678:
            raise DexInputError("unsupported_dex", "Expected a 112-byte little-endian DEX header")
        if size != before.st_size:
            raise DexInputError(
                "size_mismatch", "DEX file_size differs from the supplied file size"
            )
        # Standard fixed-width ID tables must fit before passing data to the engine.
        for start, width in ((56, 4), (64, 4), (72, 12), (80, 8), (88, 8), (96, 32)):
            count, offset = struct.unpack_from("<II", header, start)
            if (count and (offset < 112 or offset % 4 or offset + count * width > size)) or (
                not count and offset
            ):
                raise DexInputError("invalid_table", "DEX ID table is outside the file bounds")
        digest = hashlib.sha256(header)
        signature = hashlib.sha1(header[32:])
        checksum = zlib.adler32(header[12:])
        copied = len(header)
        with archive.open(entry, "w") as target:
            target.write(header)
            while block := handle.read(1024 * 1024):
                copied += len(block)
                if copied > size or copied > budget:
                    raise DexInputError(
                        "input_changed", "DEX grew during import; retry with stable files"
                    )
                digest.update(block)
                signature.update(block)
                checksum = zlib.adler32(block, checksum)
                target.write(block)
    if copied != size or _identity(before) != _identity(source.stat()):
        raise DexInputError("input_changed", "DEX changed during import; retry with stable files")
    if signature.digest() != header[12:32] or checksum != struct.unpack_from("<I", header, 8)[0]:
        raise DexInputError(
            "integrity_mismatch", "DEX checksum/signature mismatch; input was not repaired"
        )
    return {
        "path": str(source),
        "dex_entry": entry,
        "size_bytes": size,
        "sha256": digest.hexdigest(),
        "dex_version": version,
        "declared_class_count": struct.unpack_from("<I", header, 96)[0],
    }


def analyze(request: dict, root: Path) -> dict:
    settings = Settings(
        allowed_roots=tuple(Path(p) for p in request["allowed_roots"]),
        max_apk_bytes=request["max_input_bytes"],
        max_output_bytes=request["max_output_bytes"],
        max_page_size=request["max_page_size"],
    )
    paths = settings.validate_dex_paths(request["paths"])
    query = request["query"]
    operation = query["operation"]
    runner = PublicCliRunner(settings)
    page = {"offset": query["offset"], "limit": query["limit"]}
    common = {
        "input_kind": "dex_set",
        "coverage": "supplied_files_only",
        "runtime_completeness": "unknown",
        "has_manifest": False,
        "sources": [],
    }
    try:
        runner._page_bounds(**page)
        bundle = root / "analysis.apk"
        remaining = settings.max_apk_bytes
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for index, source in enumerate(paths):
                entry = "classes.dex" if index == 0 else f"classes{index + 1}.dex"
                try:
                    record = copy_dex(source, archive, entry, remaining)
                except DexInputError as exc:
                    return {
                        **common,
                        "status": "error",
                        "code": exc.code,
                        "message": str(exc),
                        "source_path": str(source),
                    }
                common["sources"].append(record)
                remaining -= record["size_bytes"]
        # Inspect each DEX independently so duplicate definitions cannot be hidden by merging.
        owners = {}
        duplicates = []
        with zipfile.ZipFile(bundle) as archive:
            for record in common["sources"]:
                single = root / (record["dex_entry"] + ".apk")
                with (
                    zipfile.ZipFile(single, "w", compression=zipfile.ZIP_DEFLATED) as out,
                    archive.open(record["dex_entry"]) as source,
                    out.open("classes.dex", "w") as target,
                ):
                    while block := source.read(1024 * 1024):
                        target.write(block)
                names = runner._get_snapshot(["listclass", "--threads", "1", str(single)]).lines
                single.unlink()
                record["class_count"] = len(names)
                if len(names) != record["declared_class_count"]:
                    raise DexInputError(
                        "class_count_mismatch",
                        f"Engine class count differs from DEX header: {record['path']}",
                    )
                for name in names:
                    if name in owners:
                        if len(duplicates) < 20:
                            duplicates.append(
                                {
                                    "class_name": name,
                                    "dex_entries": [owners[name], record["dex_entry"]],
                                }
                            )
                    else:
                        owners[name] = record["dex_entry"]
        if duplicates:
            return {
                **common,
                "status": "error",
                "code": "duplicate_class",
                "message": "Duplicate class definitions; select an unambiguous DEX set",
                "duplicates": duplicates,
            }
        common["class_count"] = len(owners)
        if operation == "info":
            return {**common, "status": "ok"}
        if operation == "get_manifest":
            return {
                **common,
                "status": "not_applicable",
                "code": "no_manifest",
                "message": "DEX files do not contain AndroidManifest.xml",
            }
        if operation == "list_classes":
            result = runner.list_classes(
                bundle, prefix=query["prefix"], threads=query["threads"], **page
            ).as_dict()
            result["items"] = [
                {"class_name": name, "dex_entry": owners[name]} for name in result["items"]
            ]
        elif operation == "get_class_source":
            name = query["class_name"]
            if not name:
                raise DexInputError("invalid_query", "class_name is required")
            if name not in owners:
                raise DexInputError(
                    "class_not_found", "Class is absent from the supplied DEX files"
                )
            result = runner.get_class_source(
                bundle, class_name=name, threads=query["threads"], **page
            ).as_dict()
            result.update(
                {
                    "class_name": name,
                    "dex_entry": owners[name],
                    "source": "\n".join(result.pop("items")),
                }
            )
        elif operation == "find_refs":
            result = runner.find_refs(
                bundle,
                kind=query["kind"],
                value=query["value"],
                class_name=query["class_name"],
                fuzzy_class=query["fuzzy_class"],
                threads=query["threads"],
                **page,
            )
        else:
            raise DexInputError("invalid_query", "Unknown DEX operation")
        return {**common, **result, "status": "ok"}
    except DexInputError as exc:
        return {**common, "status": "error", "code": exc.code, "message": str(exc)}
    except DroidAscError as exc:
        return {**common, "status": "error", "code": "engine_error", "message": str(exc)}
    except ValueError as exc:
        return {**common, "status": "error", "code": "invalid_query", "message": str(exc)}


def main():
    request_path = Path(sys.argv[1])
    result = analyze(json.loads(request_path.read_text(encoding="utf-8")), request_path.parent)
    encoded = json.dumps(result)
    if len(encoded.encode()) > 256 * 1024:
        encoded = json.dumps(
            {
                "status": "error",
                "code": "response_limit",
                "message": "DEX response exceeds budget; reduce limit or narrow the query",
            }
        )
    print(encoded)


if __name__ == "__main__":
    main()
