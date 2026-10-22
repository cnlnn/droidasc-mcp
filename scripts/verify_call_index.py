"""Compare every persisted call-index site with independent Androguard decoding."""

import argparse
import gc
import hashlib
import json
import sqlite3
import struct
import tempfile
import zipfile
from contextlib import closing
from pathlib import Path

from verify_fuzzy_references import digest, method_reference_index, runtime_identity


def site(entry, caller, callee, offset, opcode, prototype=""):
    return json.dumps(
        [entry, caller, callee, offset, opcode, prototype], separators=(",", ":")
    ).encode()


def main(args):
    from androguard.core.dex import DEX
    from loguru import logger

    from droidasc_mcp.config import Settings
    from droidasc_mcp.native_index import build
    from droidasc_mcp.xref_index import _unpack_edge

    logger.remove()
    runtime_before = runtime_identity()
    verifier_paths = (Path(__file__), Path(__file__).with_name("verify_fuzzy_references.py"))
    verifier_before = {path.name: digest(path) for path in verifier_paths}
    original = digest(args.apk)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # This is an acceptance-side oracle, not a resident runtime graph/cache.
    with tempfile.TemporaryDirectory(prefix="call-oracle-", dir=args.output.parent) as directory:
        root = Path(directory)
        bundle, index = root / "analysis.apk", root / "calls.sqlite"
        with zipfile.ZipFile(args.apk) as source, zipfile.ZipFile(bundle, "w") as target:
            entries = sorted(
                name
                for name in source.namelist()
                if "/" not in name and name.startswith("classes") and name.endswith(".dex")
            )
            assert entries and len(entries) == len(set(entries)) <= 64
            for entry in entries:
                target.writestr(entry, source.read(entry), compress_type=zipfile.ZIP_STORED)
        build(Settings.from_env(), bundle, index, root, {"oracle": "complete"}, calls_only=True)
        print(json.dumps({"index_bytes": index.stat().st_size}), flush=True)
        with (
            closing(sqlite3.connect(index)) as native,
            closing(sqlite3.connect(root / "comparison.sqlite")) as db,
        ):
            db.execute("PRAGMA journal_mode=OFF")
            db.execute("PRAGMA synchronous=OFF")
            db.execute("PRAGMA cache_size=-4096")
            db.execute(
                "CREATE TABLE sites (site BLOB PRIMARY KEY, candidate INTEGER, oracle INTEGER)"
            )
            counters = native.execute(
                "SELECT count(*),sum(instructions),sum(without_code) FROM methods"
            ).fetchone()
            for entry, caller, callee, data in native.execute(
                "SELECT d.entry,src.name,dst.name,e.data FROM edges e "
                "JOIN symbols src ON src.id=e.source JOIN symbols dst ON dst.id=e.target "
                "JOIN definitions d ON d.name=e.source AND d.kind='method' "
                "WHERE e.kind='method' AND e.relation='instruction' ORDER BY e.id"
            ):
                row = _unpack_edge("method", data, caller, callee, "instruction", entry)
                key = site(
                    entry,
                    caller,
                    callee,
                    row["instruction_offset"],
                    row["opcode"],
                    row.get("call_site_prototype", ""),
                )
                db.execute(
                    "INSERT INTO sites VALUES (?,1,0) ON CONFLICT(site) DO UPDATE "
                    "SET candidate=candidate+1",
                    (key,),
                )
            methods = instructions = without_code = dynamic = 0
            with zipfile.ZipFile(bundle) as archive:
                for entry in entries:
                    dex = DEX(archive.read(entry))
                    for cls in dex.get_classes():
                        for method in cls.get_methods():
                            methods += 1
                            without_code += method.get_code() is None
                            caller = (
                                method.get_class_name()
                                + "->"
                                + method.get_name()
                                + "".join(method.get_descriptor().split())
                            )
                            for offset, instruction in method.get_instructions_idx():
                                instructions += 1
                                op = instruction.get_op_value()
                                dynamic += op in {0xFA, 0xFB, 0xFC, 0xFD, 0xFE}
                                if not (
                                    0x6E <= op <= 0x72 or 0x74 <= op <= 0x78 or op in {0xFA, 0xFB}
                                ):
                                    continue
                                owner, name, proto = dex.get_cm_method(
                                    method_reference_index(instruction)
                                )
                                callee = owner + "->" + name + "".join("".join(proto).split())
                                prototype = ""
                                if op in {0xFA, 0xFB}:
                                    proto_id = instruction.HHHH
                                    prototype = "".join("".join(dex.CM.get_proto(proto_id)).split())
                                key = site(
                                    entry,
                                    caller,
                                    callee,
                                    offset // 2,
                                    instruction.get_name(),
                                    prototype,
                                )
                                db.execute(
                                    "INSERT INTO sites VALUES (?,0,1) ON CONFLICT(site) DO UPDATE "
                                    "SET oracle=oracle+1",
                                    (key,),
                                )
                    cls = method = None
                    del dex
                    gc.collect()
                    print(json.dumps({"entry": entry, "methods": methods}), flush=True)
            assert counters == (methods, instructions, without_code), (
                counters,
                methods,
                instructions,
            )
            assert native.execute("SELECT count(*) FROM dynamic").fetchone()[0] == dynamic
            assert (
                db.execute("SELECT count(*) FROM sites WHERE candidate<>oracle").fetchone()[0] == 0
            ), "Persisted call-site multiset differs from independent decoder"
            total = db.execute("SELECT sum(candidate) FROM sites").fetchone()[0]
            multiset = hashlib.sha256()
            for key, count in db.execute("SELECT site,candidate FROM sites ORDER BY site"):
                multiset.update(struct.pack("<II", len(key), count))
                multiset.update(key)
            report = {
                "verifier_sha256": verifier_before,
                "verifier_unchanged": verifier_before
                == {path.name: digest(path) for path in verifier_paths},
                "runtime_sha256": runtime_before,
                "runtime_unchanged": runtime_before == runtime_identity(),
                "status": "all_persisted_call_sites_equal",
                "apk_sha256": original,
                "index_bytes": index.stat().st_size,
                "total_call_sites": total,
                "methods": methods,
                "scanned_instructions": instructions,
                "methods_without_code": without_code,
                "dynamic_sites": dynamic,
                "site_multiset_sha256": multiset.hexdigest(),
                "oracle": "Androguard sequential instruction decoder; exact SQLite multiset",
                "scope": "all persisted declared call operands, not runtime target resolution",
                "original_unchanged": original == digest(args.apk),
            }
            assert report["original_unchanged"]
            assert report["runtime_unchanged"], "Runtime changed during call-index parity checks"
            assert report["verifier_unchanged"], "Verifier changed during call-index parity checks"
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
