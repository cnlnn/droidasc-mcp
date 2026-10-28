"""Validate DEX inputs and run the public ASC entry point inside one supervised worker."""

from __future__ import annotations

import hashlib
import io
import json
import struct
import sys
import zipfile
import zlib
from contextlib import ExitStack
from pathlib import Path

from .archive_errors import ArchiveError
from .worker_errors import DroidAscError
from .worker_runtime import WorkerRuntime, WorkerSettings


class DexInputError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


OWNER_OPERATIONS = {
    "get_class_source_metadata",
    "get_method_source",
    "list_classes",
    "get_class_source",
}


def write_json_bounded(path, value, budget):
    """Serialize large directories without allocating full JSON and encoded copies."""
    used, buffered = 0, 0
    chunks = []
    with path.open("wb") as output:
        for chunk in json.JSONEncoder().iterencode(value):
            # The default encoder escapes non-ASCII, including unpaired DEX surrogates.
            used += len(chunk)
            if used > budget:
                raise DexInputError("metadata_limit", "Prepared DEX metadata exceeds budget")
            chunks.append(chunk)
            buffered += len(chunk)
            if buffered >= 65536:
                output.write("".join(chunks).encode("ascii"))
                chunks.clear()
                buffered = 0
        if chunks:
            output.write("".join(chunks).encode("ascii"))
    return used


def preparation_progress(root, completed, total, message):
    # Append instead of replacing a file that a Windows reader may have open.
    encoded = json.dumps({"completed": completed, "total": total, "message": message}).encode()
    with (root / "progress.jsonl").open("ab") as stream:
        stream.write(encoded + b"\n")


def build_class_directory(bundle, records, root, settings, progress):
    from .class_directory import ClassDirectory
    from .native_dex import InvalidDex
    from .native_directory import class_entries

    duplicates = []
    try:
        with ClassDirectory(root / "owners.sqlite", budget=settings.max_output_bytes) as owners:
            for index, (entry, names) in enumerate(class_entries(bundle)):
                record = records[entry]
                record["class_count"] = len(names)
                if len(names) != record["declared_class_count"]:
                    raise DexInputError(
                        "class_count_mismatch",
                        f"Engine class count differs from DEX header: {record['path']}",
                    )
                duplicates.extend(owners.add(names, entry)[: max(0, 20 - len(duplicates))])
                del names
                if progress:
                    preparation_progress(
                        root,
                        len(records) + index + 1,
                        len(records) * 2,
                        "Validated class directory",
                    )
            return len(owners), duplicates, owners.metadata_bytes
    except InvalidDex as exc:
        raise DexInputError("invalid_dex", str(exc)) from exc


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


def __getattr__(name):
    # Preserve existing internal imports without loading the CLI into native workers.
    if name == "PublicCliRunner":
        from .cli_worker import PublicCliRunner

        return PublicCliRunner
    raise AttributeError(name)


def engine_version(request=None):
    if request is not None and "engine_version" in request:
        value = request["engine_version"]
        if not isinstance(value, str) or not value:
            raise DexInputError("invalid_query", "Invalid host engine version")
        return value
    # Compatibility for direct library callers predating host-bound requests.
    from importlib.metadata import version

    return version("droidasc")


def _identity(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def copy_dex(source: Path, archive: zipfile.ZipFile, entry: str, budget: int) -> dict:
    before = source.stat()
    with source.open("rb") as handle:
        record = copy_dex_stream(handle, before.st_size, str(source), archive, entry, budget)
    if _identity(before) != _identity(source.stat()):
        raise DexInputError("input_changed", "DEX changed during import; retry with stable files")
    return record


def copy_dex_stream(handle, supplied_size, source, archive, entry, budget, header=None):
    """Validate and snapshot one standard DEX without an intermediate raw file."""
    if supplied_size > budget:
        raise DexInputError("input_limit", "Combined DEX size exceeds configured size limit")
    header = handle.read(112) if header is None else header
    if len(header) < 112:
        raise DexInputError("truncated_dex", f"DEX header is truncated: {source}")
    if header[:4] != b"dex\n" or header[7] != 0:
        raise DexInputError("invalid_magic", f"Expected a standard DEX header: {source}")
    version = header[4:7].decode("ascii", errors="replace")
    if version not in {"035", "037", "038", "039", "040"}:
        raise DexInputError("unsupported_dex", f"Unsupported DEX version: {version}")
    size, header_size, endian = struct.unpack_from("<III", header, 32)
    if header_size != 112 or endian != 0x12345678:
        raise DexInputError("unsupported_dex", "Expected a 112-byte little-endian DEX header")
    if size != supplied_size:
        raise DexInputError("size_mismatch", "DEX file_size differs from the supplied file size")
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
        while block := handle.read(min(256 * 1024, size - copied + 1)):
            copied += len(block)
            if copied > size:
                raise DexInputError(
                    "input_changed", "DEX grew during import; retry with stable files"
                )
            digest.update(block)
            signature.update(block)
            checksum = zlib.adler32(block, checksum)
            target.write(block)
    if copied != size:
        raise DexInputError("input_changed", "DEX changed during import; retry with stable files")
    if signature.digest() != header[12:32] or checksum != struct.unpack_from("<I", header, 8)[0]:
        raise DexInputError(
            "integrity_mismatch", "DEX checksum/signature mismatch; input was not repaired"
        )
    return {
        "path": source,
        "dex_entry": entry,
        "size_bytes": size,
        "sha256": digest.hexdigest(),
        "dex_version": version,
        "declared_class_count": struct.unpack_from("<I", header, 96)[0],
    }


def prepare_bundle(settings, request, root, common, directory=None):
    import shutil

    from .dex_container import expand

    remaining, count = settings.max_apk_bytes, 0
    artifact = None

    def next_entry():
        if count >= 64:
            raise DexInputError("dex_count_limit", "Select at most 64 logical DEX files")
        return "classes.dex" if count == 0 else f"classes{count + 1}.dex"

    def append(record, origin=None):
        nonlocal count, remaining
        if artifact is not None:
            record.update(path=str(artifact), container_entry=origin)
        common["sources"].append(record)
        if directory is not None:
            directory.accept(archive, record)
        count += 1
        remaining -= record["size_bytes"]
        if request.get("prepare"):
            preparation_progress(root, count, None, "Validated DEX snapshot")

    def consume_file(original, index, origin=None):
        workspace = root / f"dex-container-{index}"
        workspace.mkdir()
        for source, provenance in expand(settings, original, workspace):
            try:
                record = copy_dex(source, archive, next_entry(), remaining)
            except DexInputError as exc:
                exc.source_path = str(source)
                raise
            if provenance:
                record.update(provenance, path=str(original))
            append(record, origin)
        shutil.rmtree(workspace)

    with ExitStack() as stack:
        if request.get("artifact_path"):
            from .containers import prefetched_entries, selected_dex, validate_budget

            artifact = settings.validate_artifact(request["artifact_path"])
            budget = validate_budget(request["max_uncompressed_bytes"], settings)
            identity = (
                {"expected_sha256": request["expected_sha256"]}
                if request.get("expected_sha256") is not None
                else {}
            )
            inputs, metadata = stack.enter_context(
                selected_dex(settings, artifact, budget, request.get("module"), **identity)
            )
            inputs = stack.enter_context(prefetched_entries(inputs))
            common.update(metadata, input_kind="container", has_manifest=False)
        else:
            inputs = settings.validate_dex_paths(request["paths"])
        archive = stack.enter_context(
            zipfile.ZipFile(root / "analysis.apk", "w", compression=zipfile.ZIP_STORED)
        )
        for index, item in enumerate(inputs):
            if artifact is None:
                consume_file(item, index)
                continue
            source, info, origin = item
            header = source.read(112)
            if header[:8] != b"dex\n041\0":
                try:
                    record = copy_dex_stream(
                        source, info.file_size, origin, archive, next_entry(), remaining, header
                    )
                except DexInputError as exc:
                    exc.source_path = origin
                    raise
                append(record, origin)
                continue
            # Only 041 requires a seekable private input for strict normalization.
            original = root / f"import-{index}.dex"
            copied = len(header)
            with original.open("wb") as output:
                output.write(header)
                while block := source.read(min(256 * 1024, info.file_size - copied + 1)):
                    copied += len(block)
                    if copied > info.file_size:
                        raise ArchiveError("container_limit", "Expanded DEX exceeds declared size")
                    output.write(block)
            if copied != info.file_size:
                raise ArchiveError("invalid_entry", "DEX size differs from its declaration")
            consume_file(original, index, origin)
            original.unlink()
    return count


def analyze(request: dict, root: Path) -> dict:
    settings = WorkerSettings(request)
    query = request["query"]
    runner = WorkerRuntime(settings)
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
        if request.get("prepared_root"):
            prepared = Path(request["prepared_root"])
            metadata = json.loads((prepared / "prepared.json").read_text(encoding="utf-8"))
            common = metadata["common"]
            if common["engine_version"] != engine_version(request):
                raise DexInputError("engine_changed", "Reopen the session with the current engine")
            from .reference_spool import ReferenceSpool

            with ReferenceSpool(
                request.get("reference_cache"), prepared, settings.max_output_bytes
            ) as spool:
                runner.reference_spool = spool
                result = query_prepared(runner, prepared / "analysis.apk", common, query, root)
                spool.finish(result)
                return result
        if request.get("prepare"):
            preparation_progress(root, 0, None, "Validating and snapshotting input")
        from .preparation_directory import PreparationDirectory

        with PreparationDirectory(root, settings.max_output_bytes) as directory:
            logical_count = prepare_bundle(settings, request, root, common, directory)
        if request.get("expected_sha256") is not None:
            # Bind the prepared bytes (including raw 041 provenance) to the artifact handle.
            hashes = {
                source.get("container_sha256", source["sha256"]) for source in common["sources"]
            }
            actual = common.get("artifact_sha256")
            if (actual is not None and actual != request["expected_sha256"]) or (
                actual is None and hashes != {request["expected_sha256"]}
            ):
                raise DexInputError(
                    "input_changed", "Artifact snapshot no longer matches its handle"
                )
            common.update(
                artifact_path=request["original_path"], artifact_sha256=request["expected_sha256"]
            )
            for source in common["sources"]:
                source["path"] = request["original_path"]
        bundle = root / "analysis.apk"
        count, duplicates, directory_bytes = directory.result
        if duplicates:
            return {
                **common,
                "status": "error",
                "code": "duplicate_class",
                "message": "Duplicate class definitions; select an unambiguous DEX set",
                "duplicates": duplicates,
            }
        common["class_count"] = count
        common["engine_version"] = engine_version(request)
        identity = {
            "schema": 1,
            "engine": common["engine_version"],
            "dex_sha256": [item["sha256"] for item in common["sources"]],
        }
        common["input_id"] = hashlib.sha256(
            json.dumps(identity, sort_keys=True).encode()
        ).hexdigest()
        if request.get("prepare"):
            used = write_json_bounded(
                root / "prepared.json", {"common": common}, settings.max_output_bytes
            )
            if directory_bytes + used > settings.max_output_bytes:
                raise DexInputError("metadata_limit", "Prepared DEX metadata exceeds budget")
            preparation_progress(
                root,
                logical_count * 2,
                logical_count * 2,
                "Validated session ready; indexes remain on demand",
            )
            return {**common, "status": "ok"}
        return query_prepared(runner, bundle, common, query, root)
    except (DexInputError, ArchiveError) as exc:
        return {
            **common,
            "status": "error",
            "code": exc.code,
            "message": str(exc),
            **({"source_path": exc.source_path} if hasattr(exc, "source_path") else {}),
        }
    except DroidAscError as exc:
        return {**common, "status": "error", "code": "engine_error", "message": str(exc)}
    except ValueError as exc:
        return {**common, "status": "error", "code": "invalid_query", "message": str(exc)}
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError, OSError) as exc:
        return {**common, "status": "error", "code": "invalid_container", "message": str(exc)}


def query_prepared(runner, bundle, common, query, workspace):
    from .reference_page import reference_page, selected_query

    result = _select_query_prepared(runner, bundle, common, query, workspace)
    if selected_query(query):
        return reference_page(result, runner.settings.max_output_bytes)
    return result


def _select_query_prepared(runner, bundle, common, query, workspace):
    if query["operation"] in OWNER_OPERATIONS or query.get("method_name") is not None:
        from .class_directory import ClassDirectory

        with ClassDirectory(bundle.parent / "owners.sqlite") as owners:
            if query.get("method_name") is not None:
                from .native_structure import resolve_method

                owner = query["class_name"]
                try:
                    entry = owners[owner]
                except KeyError:
                    entry = None
                selection = resolve_method(
                    bundle,
                    entry,
                    owner,
                    query["method_name"],
                    query.get("target_descriptor"),
                )
                if selection["status"] != "ok":
                    return {**common, **selection}
                result = _query_prepared(
                    runner,
                    bundle,
                    common,
                    owners,
                    {**query, "method_descriptor": selection["method_descriptor"]},
                    workspace,
                )
                return {
                    **result,
                    **{key: value for key, value in selection.items() if key != "status"},
                }
            return _query_prepared(runner, bundle, common, owners, query, workspace)
    return _query_prepared(runner, bundle, common, {}, query, workspace)


def _query_prepared(runner, bundle, common, owners, query, workspace):
    from .xref_index import (
        DISCOVERY_OPERATIONS,
        INDEX_OPERATIONS,
        REFERENCE_OPERATIONS,
        STRUCTURE_OPERATIONS,
        query_index,
    )

    operation = query["operation"]
    page = {"offset": query["offset"], "limit": query["limit"]}
    from .reference_page import operand_query

    if operand_query(query):
        from .native_types import query_types

        return {
            **common,
            **query_types(runner.settings, bundle, query, emit=runner.reference_spool),
        }
    if operation == "find_string_refs":
        from .native_strings import query_strings

        return {
            **common,
            **query_strings(runner.settings, bundle, query, emit=runner.reference_spool),
        }
    if ((bundle.parent / "xrefs.sqlite").is_file() or runner.settings.xref_cache_dir) and (
        operation in REFERENCE_OPERATIONS - {"search_refs"}
        or (
            operation == "search_members"
            and query.get("case_sensitive", True)
            and query.get("member_match", "descriptor") == "descriptor"
        )
    ):
        indexed = query_index(runner.settings, bundle, common, query, workspace)
        if indexed is not None:
            return {**common, **indexed}
    if operation in {"find_method_refs", "get_method_calls", "find_field_refs", "search_refs"}:
        from .native_dex import query_references

        return {
            **common,
            **query_references(runner.settings, bundle, query, emit=runner.reference_spool),
        }
    if operation in DISCOVERY_OPERATIONS:
        from .native_discovery import query_discovery

        return {**common, **query_discovery(runner.settings, bundle, query, workspace)}
    if operation in STRUCTURE_OPERATIONS or operation == "list_methods":
        from .native_structure import query_structure

        return {**common, **query_structure(runner.settings, bundle, query, workspace)}
    if operation in {"revision_diff", "secret_candidates"}:
        from .review import query_review

        return {**common, **query_review(runner.settings, bundle, common, query, workspace)}
    if operation == "get_class_source_metadata":
        from .source_metadata import query_source_metadata

        name = query.get("class_name")
        if name not in owners:
            return {**common, "status": "error", "code": "class_not_found"}
        return {**common, **query_source_metadata(runner.settings, bundle, owners[name], query)}
    if operation in INDEX_OPERATIONS:
        indexed = query_index(runner.settings, bundle, common, query, workspace)
        if indexed is not None:
            return {**common, **indexed}
    if operation == "get_method_source":
        from .method_backend import query_methods

        name = query.get("class_name")
        if not name:
            raise ValueError("class_name is required")
        if name not in owners:
            return {**common, "status": "error", "code": "class_not_found"}
        if operation == "get_method_source" and query.get("source_format", "auto") != "java":
            return {**common, **asc_method_smali(runner, bundle, owners[name], query)}
        result = query_methods(runner.settings, bundle, owners[name], query, workspace)
        return {**common, **result, "class_name": name, "dex_entry": owners[name]}
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
        from .native_dex import page_result

        offset, limit = query["offset"], min(query["limit"], runner.settings.max_page_size)
        total, items = owners.page(query.get("prefix"), offset, limit)
        result = page_result(
            {"total": total, "items": items},
            query,
            runner.settings,
        )
    elif operation == "get_class_source":
        name = query["class_name"]
        if not name:
            raise DexInputError("invalid_query", "class_name is required")
        if name not in owners:
            raise DexInputError("class_not_found", "Class is absent from the supplied DEX files")
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


def asc_method_smali(runner, bundle, entry, query):
    descriptor = query["method_descriptor"]
    owner, signature = descriptor.split("->", 1)
    args = ["disassemble", "--threads", "1", str(bundle), owner, "--method=" + signature]
    if query.get("debug_info"):
        args.append("--debuginfo")
    try:
        page = runner._run_paged(args, offset=query["offset"], limit=query["limit"]).as_dict()
    except DroidAscError as exc:
        if str(exc) == (
            "Error: method not found or signature is not defined in the target DEX: " + signature
        ):
            return {"status": "error", "code": "method_not_found", "method_descriptor": descriptor}
        raise
    source = "\n".join(page.pop("items"))
    return {
        **page,
        "source": source,
        "status": "ok",
        "method_descriptor": descriptor,
        "class_name": owner,
        "dex_entry": entry,
        "backend": "droidasc",
        "backend_version": engine_version(),
        "format": "smali",
        "debug_info": bool(query.get("debug_info")),
        "fell_back": False,
        "fallback_reason": "",
    }


def main():
    from .worker_errors import response_limit

    request_path = Path(sys.argv[1])
    result = analyze(json.loads(request_path.read_text(encoding="utf-8")), request_path.parent)
    encoded = json.dumps(result)
    if len(encoded.encode()) > 256 * 1024:
        encoded = json.dumps(response_limit())
    print(encoded)


if __name__ == "__main__":
    main()
