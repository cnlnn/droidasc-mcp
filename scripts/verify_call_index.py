"""Independently accept a complete calls-only index for ordinary pre-041 APK DEX files.

The oracle walks every instruction, not only emitted graph edges. Graph replay still
uses the product's bounded traversal; this gate does not independently prove BFS,
ordering/budget policy, runtime dispatch, or DEX 041 normalization.
"""

import argparse
import gc
import hashlib
import json
import sqlite3
import struct
import tempfile
import zipfile
import zlib
from contextlib import closing
from pathlib import Path

from verify_fuzzy_references import digest, method_reference_index, runtime_identity
from verify_mcp_reference_pages import fingerprint, original_bundle

STATUS = "all_persisted_call_sites_equal"
SCOPE = (
    "complete declared call operands, method definitions/scan counts, and unresolved dynamic "
    "metadata in ordinary top-level multidex APKs (DEX 035/037/038/039/040 only); "
    "not DEX 041, runtime target resolution, or an independent graph traversal algorithm"
)


def verifier_identity():
    return {
        name: digest(Path(__file__).with_name(name))
        for name in (
            "verify_call_index.py",
            "verify_fuzzy_references.py",
            "verify_mcp_reference_pages.py",
        )
    }


def decoder_identity():
    import androguard
    import mutf8

    root = Path(androguard.__file__).parent
    return {
        "name": "androguard",
        "version": androguard.__version__,
        "mutf8": {
            "version": mutf8.__version__,
            "implementation": mutf8.decode_modified_utf8.__module__,
            "files_sha256": {
                path.name: digest(path)
                for path in sorted(Path(mutf8.__file__).parent.iterdir())
                if path.suffix in {".py", ".so", ".pyd"}
            },
        },
        "python_sources_sha256": {
            path.relative_to(root).as_posix(): digest(path) for path in sorted(root.rglob("*.py"))
        },
    }


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def site(entry, caller, callee, offset, opcode, prototype=""):
    return encoded([entry, caller, callee, offset, opcode, prototype])


def oracle_records(bundle):
    """Yield independent records, including methods with no calls or no code."""
    from androguard.core.dex import DEX
    from loguru import logger

    logger.remove()
    with zipfile.ZipFile(bundle) as archive:
        entries = archive.namelist()
        assert entries and len(entries) == len(set(entries)) <= 64
        for entry in entries:
            raw = archive.read(entry)
            assert raw[:8] in {
                b"dex\n" + v + b"\0" for v in (b"035", b"037", b"038", b"039", b"040")
            }, "Independent call-index oracle supports ordinary pre-041 DEX only"
            dex = DEX(raw)
            del raw
            for cls in dex.get_classes():
                for method in cls.get_methods():
                    caller = (
                        method.get_class_name()
                        + "->"
                        + method.get_name()
                        + "".join(method.get_descriptor().split())
                    )
                    instructions = 0
                    for offset, instruction in method.get_instructions_idx():
                        instructions += 1
                        op, opcode = instruction.get_op_value(), instruction.get_name()
                        assert offset % 2 == 0
                        if op in {0xFA, 0xFB, 0xFC, 0xFD, 0xFE}:
                            yield (
                                "dynamic",
                                encoded(
                                    [
                                        entry,
                                        caller,
                                        {
                                            "caller": caller,
                                            "dex_entry": entry,
                                            "instruction_offset": offset // 2,
                                            "opcode": opcode,
                                            "reason": "dynamic_target_not_resolved",
                                        },
                                    ]
                                ),
                            )
                        if not (0x6E <= op <= 0x72 or 0x74 <= op <= 0x78 or op in {0xFA, 0xFB}):
                            continue
                        owner, name, proto = dex.get_cm_method(method_reference_index(instruction))
                        callee = owner + "->" + name + "".join("".join(proto).split())
                        prototype = ""
                        if op in {0xFA, 0xFB}:
                            prototype = "".join("".join(dex.CM.get_proto(instruction.HHHH)).split())
                        yield "calls", site(entry, caller, callee, offset // 2, opcode, prototype)
                    yield (
                        "methods",
                        encoded([entry, caller, instructions, int(method.get_code() is None)]),
                    )
            cls = method = instruction = None
            del dex
            gc.collect()
            print(json.dumps({"independently_decoded_entry": entry}), flush=True)


def candidate_records(native):
    """Read the persisted wire format, rejecting rows hidden by an inner join/filter."""
    definitions = native.execute("SELECT count(*) FROM definitions").fetchone()[0]
    methods = native.execute("SELECT count(*) FROM methods").fetchone()[0]
    assert definitions == methods, "Calls-only method definition inventory differs"
    assert not native.execute("SELECT 1 FROM definitions WHERE kind<>'method'").fetchone(), (
        "Expected a calls-only index"
    )
    for entry, caller, instructions, without_code in native.execute(
        "SELECT d.entry,s.name,m.instructions,m.without_code FROM methods m "
        "LEFT JOIN symbols s ON s.id=m.source "
        "LEFT JOIN definitions d ON d.name=m.source AND d.kind='method'"
    ):
        assert entry and caller, "Dangling method or missing method definition"
        assert type(instructions) is int and instructions >= 0
        assert type(without_code) is int and without_code in {0, 1}
        yield "methods", encoded([entry, caller, instructions, without_code])
    for kind, relation, entry, caller, callee, data in native.execute(
        "SELECT e.kind,e.relation,d.entry,src.name,dst.name,e.data FROM edges e "
        "LEFT JOIN symbols src ON src.id=e.source LEFT JOIN symbols dst ON dst.id=e.target "
        "LEFT JOIN definitions d ON d.name=e.source AND d.kind='method'"
    ):
        assert kind == "method" and relation == "instruction", "Unexpected calls-only edge"
        assert entry and caller and callee, "Dangling call-site provenance"
        row = json.loads(data)
        assert isinstance(row, list) and len(row) == 3, "Malformed persisted call site"
        offset, opcode, prototype = row
        assert type(offset) is int and offset >= 0 and isinstance(opcode, str)
        if opcode in {"invoke-polymorphic", "invoke-polymorphic/range"}:
            assert isinstance(prototype, str) and prototype, "Missing polymorphic prototype"
        else:
            assert prototype is None, "Unexpected prototype on ordinary call site"
        yield "calls", site(entry, caller, callee, offset, opcode, prototype or "")
    for entry, caller, data in native.execute(
        "SELECT d.entry,s.name,u.data FROM dynamic u "
        "LEFT JOIN symbols s ON s.id=u.source "
        "LEFT JOIN definitions d ON d.name=u.source AND d.kind='method'"
    ):
        assert entry and caller, "Dangling dynamic-site provenance"
        yield "dynamic", encoded([entry, caller, json.loads(zlib.decompress(data))])


def compare_index(index, independent_records, workspace):
    """Compare exact disk-backed multisets; independent_records never reads the index."""
    with (
        closing(sqlite3.connect(f"{index.resolve().as_uri()}?mode=ro", uri=True)) as native,
        tempfile.TemporaryDirectory(prefix="call-multiset-", dir=workspace) as directory,
        closing(sqlite3.connect(Path(directory) / "comparison.sqlite")) as db,
    ):
        db.execute("PRAGMA journal_mode=OFF")
        db.execute("PRAGMA synchronous=OFF")
        db.execute("PRAGMA cache_size=-4096")
        db.execute(
            "CREATE TABLE records (kind TEXT, record BLOB, candidate INTEGER, oracle INTEGER, "
            "PRIMARY KEY(kind,record))"
        )
        for column, records in (
            ("candidate", candidate_records(native)),
            ("oracle", independent_records),
        ):
            for kind, record in records:
                assert kind in {"calls", "methods", "dynamic"}
                db.execute(
                    f"INSERT INTO records VALUES (?,?,{int(column == 'candidate')},"
                    f"{int(column == 'oracle')}) ON CONFLICT(kind,record) DO UPDATE "
                    f"SET {column}={column}+1",
                    (kind, record),
                )
        counts, hashes = {}, {}
        for kind in ("calls", "methods", "dynamic"):
            mismatch = db.execute(
                "SELECT record,candidate,oracle FROM records WHERE kind=? AND candidate<>oracle "
                "LIMIT 1",
                (kind,),
            ).fetchone()
            assert mismatch is None, (
                f"Persisted {kind} multiset differs from independent decoder: {mismatch!r}"
            )
            counts[kind] = db.execute(
                "SELECT coalesce(sum(candidate),0) FROM records WHERE kind=?", (kind,)
            ).fetchone()[0]
            multiset = hashlib.sha256()
            for key, count in db.execute(
                "SELECT record,candidate FROM records WHERE kind=? ORDER BY record", (kind,)
            ):
                multiset.update(struct.pack("<II", len(key), count))
                multiset.update(key)
            hashes[kind] = multiset.hexdigest()
        instructions = without_code = 0
        for key, count in db.execute("SELECT record,oracle FROM records WHERE kind='methods'"):
            row = json.loads(key)
            instructions += row[2] * count
            without_code += row[3] * count
        return {
            "total_call_sites": counts["calls"],
            "methods": counts["methods"],
            "scanned_instructions": instructions,
            "methods_without_code": without_code,
            "dynamic_sites": counts["dynamic"],
            "site_multiset_sha256": hashes["calls"],
            "method_multiset_sha256": hashes["methods"],
            "dynamic_multiset_sha256": hashes["dynamic"],
        }


def verify_index(bundle, index, workspace):
    return compare_index(index, oracle_records(bundle), workspace)


def validate_acceptance(
    receipt, apk, bundle, index, sources, *, input_id=None, engine_version=None
):
    """Fail closed if a graph replay is no longer using the accepted inputs/index/runtime."""
    assert receipt["status"] == STATUS and receipt["schema"] == 2
    assert receipt["scope"] == SCOPE
    assert receipt["sources"] == sources and receipt["sources_sha256"] == fingerprint(sources), (
        "Source provenance differs from accepted full index"
    )
    assert receipt["input_id"] == input_id and receipt["engine_version"] == engine_version
    for key, path in (("apk_sha256", apk), ("bundle_sha256", bundle), ("index_sha256", index)):
        assert receipt[key] == digest(path), f"Accepted {key} changed"
    assert receipt["runtime_sha256"] == runtime_identity(), "Accepted runtime changed"
    assert receipt["verifier_sha256"] == verifier_identity(), "Accepted verifier changed"
    assert receipt["decoder_identity"] == decoder_identity(), "Accepted independent decoder changed"


def accept_index(
    apk, bundle, index, sources, workspace, *, byte_limit, input_id=None, engine_version=None
):
    """Accept a freshly built calls-only index, bound to the original APK/session provenance."""
    assert (input_id is None) == (engine_version is None), "Bind input ID with its engine version"
    if input_id is not None:
        identity = {
            "schema": 1,
            "engine": engine_version,
            "dex_sha256": [r["sha256"] for r in sources],
        }
        assert (
            input_id == hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        ), "Input ID differs from canonical source hashes/engine"
    receipt = {
        "schema": 2,
        "status": STATUS,
        "scope": SCOPE,
        "apk_sha256": digest(apk),
        "bundle_sha256": digest(bundle),
        "index_sha256": digest(index),
        "index_bytes": index.stat().st_size,
        "sources": json.loads(json.dumps(sources)),
        "sources_sha256": fingerprint(sources),
        "input_id": input_id,
        "engine_version": engine_version,
        "runtime_sha256": runtime_identity(),
        "verifier_sha256": verifier_identity(),
        "decoder_identity": decoder_identity(),
        "oracle": "Androguard sequential instruction decoder; exact SQLite multisets",
    }
    with tempfile.TemporaryDirectory(prefix="original-call-oracle-", dir=workspace) as directory:
        original = Path(directory) / "original-canonical.apk"
        original_bundle(apk, original, sources, byte_limit)
        with zipfile.ZipFile(original) as expected, zipfile.ZipFile(bundle) as supplied:
            assert supplied.namelist() == expected.namelist(), "Canonical bundle inventory differs"
            for row in sources:
                entry = row["dex_entry"]
                assert digest_stream(supplied.open(entry)) == row["sha256"], (
                    "Canonical DEX bytes differ"
                )
                with expected.open(entry) as stream:
                    header = stream.read(112)
                assert header[:8] in {
                    b"dex\n" + version + b"\0"
                    for version in (b"035", b"037", b"038", b"039", b"040")
                }, "Independent call-index oracle supports ordinary pre-041 DEX only"
                if "path" in row:
                    assert Path(row["path"]).resolve() == apk.resolve(), (
                        "Original source path differs"
                    )
                if "dex_version" in row:
                    assert row["dex_version"] == header[4:7].decode("ascii")
                if "declared_class_count" in row:
                    assert row["declared_class_count"] == struct.unpack_from("<I", header, 96)[0]
        receipt.update(verify_index(original, index, Path(directory)))
    validate_acceptance(
        receipt, apk, bundle, index, sources, input_id=input_id, engine_version=engine_version
    )
    receipt.update(original_unchanged=True, runtime_unchanged=True, verifier_unchanged=True)
    return receipt


def digest_stream(stream):
    with stream:
        checksum = hashlib.sha256()
        while block := stream.read(256 * 1024):
            checksum.update(block)
        return checksum.hexdigest()


def main(args):
    from droidasc_mcp.config import Settings
    from droidasc_mcp.dex_worker import analyze
    from droidasc_mcp.native_index import build
    from droidasc_mcp.runner import DroidAscRunner

    args.apk = args.apk.resolve(strict=True)
    assert not args.output.exists(), "Preserve previous acceptance attempts"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    settings = Settings(
        allowed_roots=(args.apk.parent,), max_xref_index_bytes=args.index_mib * 1024**2
    )
    runtime_before, input_before = runtime_identity(), digest(args.apk)
    verifier_before = verifier_identity()
    report = {"status": "running", "scope": SCOPE}
    try:
        with tempfile.TemporaryDirectory(
            prefix="call-oracle-", dir=args.output.parent
        ) as directory:
            root = Path(directory)
            request = DroidAscRunner(settings)._dex_request([], {"offset": 0, "limit": 100})
            request.update(
                artifact_path=str(args.apk),
                max_uncompressed_bytes=args.expanded_mib * 1024**2,
                prepare=True,
            )
            prepared = analyze(request, root)
            assert prepared["status"] == "ok", prepared
            bundle, index = root / "analysis.apk", root / "calls.sqlite"
            build(settings, bundle, index, root, {}, calls_only=True)
            print(json.dumps({"index_bytes": index.stat().st_size}), flush=True)
            report = accept_index(
                args.apk,
                bundle,
                index,
                prepared["sources"],
                root,
                byte_limit=args.expanded_mib * 1024**2,
                input_id=prepared["input_id"],
                engine_version=prepared["engine_version"],
            )
            assert report["runtime_sha256"] == runtime_before, "Runtime changed during index build"
            assert report["apk_sha256"] == input_before, "Input changed during index build"
            assert report["verifier_sha256"] == verifier_before, (
                "Verifier changed during index build"
            )
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--expanded-mib", type=int, choices=range(1, 2049), default=512)
    parser.add_argument("--index-mib", type=int, choices=range(1, 8193), default=4096)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
