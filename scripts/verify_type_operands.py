"""Compare a complete explicit-type operand scan with independent Androguard decoding.

This checks scanner accuracy, not real-MCP transport, startup latency or memory.
"""

import argparse
import gc
import hashlib
import json
import tempfile
import zipfile
from collections import Counter
from dataclasses import replace
from pathlib import Path

from verify_fuzzy_references import digest, runtime_identity


def site(row):
    return (
        row["dex_entry"],
        row["caller"],
        row["type_descriptor"],
        row["instruction_offset"],
        row["opcode"],
    )


def main(args):
    from androguard.core.dex import DEX
    from loguru import logger

    from droidasc_mcp.config import Settings
    from droidasc_mcp.native_types import query_types

    logger.remove()
    original = digest(args.apk)
    runtime = runtime_identity()
    verifier_paths = (Path(__file__), Path(__file__).with_name("verify_fuzzy_references.py"))
    verifiers = {p.name: digest(p) for p in verifier_paths}
    expected = []
    methods = instructions = without = 0
    with tempfile.TemporaryDirectory(prefix="type-operand-oracle-") as directory:
        bundle = Path(directory) / "analysis.apk"
        with zipfile.ZipFile(args.apk) as source, zipfile.ZipFile(bundle, "w") as target:
            entries = sorted(
                name
                for name in source.namelist()
                if "/" not in name and name.startswith("classes") and name.endswith(".dex")
            )
            assert entries and len(entries) == len(set(entries)) <= 64
            for name in entries:
                target.writestr(name, source.read(name), compress_type=zipfile.ZIP_STORED)
        result = query_types(
            replace(Settings.from_env(), max_page_size=2**31 - 1),
            bundle,
            {
                "operation": "find_type_refs",
                "type_descriptor": args.type_descriptor,
                "type_relation": "operand",
                "type_match": args.type_match,
                "offset": 0,
                "limit": 2**31 - 1,
            },
        )
        assert result["status"] == "ok" and result["instruction_scan_complete"]
        assert len(result["items"]) == result["total"]
        print(json.dumps({"native_sites": result["total"]}), flush=True)
        with zipfile.ZipFile(bundle) as archive:
            for entry in entries:
                dex = DEX(archive.read(entry))
                for cls in dex.get_classes():
                    for method in cls.get_methods():
                        methods += 1
                        without += method.get_code() is None
                        caller = (
                            method.get_class_name()
                            + "->"
                            + method.get_name()
                            + "".join(method.get_descriptor().split())
                        )
                        for offset, instruction in method.get_instructions_idx():
                            instructions += 1
                            if instruction.get_name() not in {
                                "const-class",
                                "check-cast",
                                "instance-of",
                                "new-instance",
                                "new-array",
                                "filled-new-array",
                                "filled-new-array/range",
                            }:
                                continue
                            descriptor = dex.get_cm_type(instruction.get_ref_kind())
                            matches = (
                                descriptor == args.type_descriptor
                                if args.type_match == "exact"
                                else args.type_descriptor in descriptor
                            )
                            if matches:
                                assert offset % 2 == 0
                                expected.append(
                                    (entry, caller, descriptor, offset // 2, instruction.get_name())
                                )
                cls = method = None
                del dex
                gc.collect()
                print(json.dumps({"entry": entry, "verified_sites": len(expected)}), flush=True)
    assert Counter(map(site, result["items"])) == Counter(expected), "Type operand sites differ"
    assert result["scanned_methods"] == methods
    assert result["scanned_instructions"] == instructions
    assert result["methods_without_code"] == without
    assert original == digest(args.apk)
    assert runtime == runtime_identity(), "Runtime changed during verification"
    assert verifiers == {p.name: digest(p) for p in verifier_paths}
    report = {
        "status": "all_explicit_type_operand_sites_equal",
        "scope": __doc__,
        "apk_sha256": original,
        "runtime_sha256": runtime,
        "runtime_unchanged": True,
        "verifier_sha256": verifiers,
        "verifiers_unchanged": True,
        "original_unchanged": True,
        "type_descriptor": args.type_descriptor,
        "type_match": args.type_match,
        "total_sites": len(expected),
        "scanned_methods": methods,
        "scanned_instructions": instructions,
        "methods_without_code": without,
        "oracle": "Androguard sequential decoding of every original DEX instruction",
        "site_multiset_sha256": hashlib.sha256(
            json.dumps(sorted(expected), separators=(",", ":")).encode()
        ).hexdigest(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--type-descriptor", required=True)
    parser.add_argument("--type-match", choices=["exact", "substring"], default="exact")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.type_descriptor:
        parser.error("type-descriptor must be nonempty")
    main(args)
