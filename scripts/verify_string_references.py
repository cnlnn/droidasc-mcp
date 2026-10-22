"""Compare every literal string-use site with independent Androguard decoding.

Scanner accuracy only: this does not measure MCP startup, preparation or memory.
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
        row["string_index"],
        row["value"],
        row["instruction_offset"],
        row["opcode"],
    )


def main(args):
    from androguard.core.dex import DEX
    from loguru import logger

    from droidasc_mcp.config import Settings
    from droidasc_mcp.native_strings import query_strings

    logger.remove()
    runtime_before = runtime_identity()
    verifier_paths = (Path(__file__), Path(__file__).with_name("verify_fuzzy_references.py"))
    verifiers = {path.name: digest(path) for path in verifier_paths}
    original = digest(args.apk)
    needle = args.value.lower() if args.ignore_case else args.value
    expected = []
    methods = instructions = without_code = high_jumbo = 0
    with tempfile.TemporaryDirectory(prefix="string-oracle-") as directory:
        bundle = Path(directory) / "analysis.apk"
        with zipfile.ZipFile(args.apk) as source, zipfile.ZipFile(bundle, "w") as target:
            entries = sorted(
                name
                for name in source.namelist()
                if "/" not in name and name.startswith("classes") and name.endswith(".dex")
            )
            assert entries and len(entries) == len(set(entries)) <= 64
            for entry in entries:
                target.writestr(entry, source.read(entry), compress_type=zipfile.ZIP_STORED)
        result = query_strings(
            replace(Settings.from_env(), max_page_size=2**31 - 1),
            bundle,
            {
                "operation": "find_string_refs",
                "value": args.value,
                "case_sensitive": not args.ignore_case,
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
                        without_code += method.get_code() is None
                        caller = (
                            method.get_class_name()
                            + "->"
                            + method.get_name()
                            + "".join(method.get_descriptor().split())
                        )
                        for offset, instruction in method.get_instructions_idx():
                            instructions += 1
                            if instruction.get_op_value() not in {0x1A, 0x1B}:
                                continue
                            index = instruction.get_ref_kind()
                            high_jumbo += instruction.get_op_value() == 0x1B and index > 65535
                            text = dex.get_cm_string(index)
                            if needle in (text.lower() if args.ignore_case else text):
                                expected.append(
                                    (
                                        entry,
                                        caller,
                                        index,
                                        text,
                                        offset // 2,
                                        instruction.get_name(),
                                    )
                                )
                cls = method = None
                del dex
                gc.collect()
                print(json.dumps({"entry": entry, "verified_sites": len(expected)}), flush=True)
    actual = [site(row) for row in result["items"]]
    assert Counter(actual) == Counter(expected), "Complete string-use multiset differs"
    assert result["scanned_instructions"] == instructions
    assert result["scanned_methods"] == methods
    assert result["methods_without_code"] == without_code
    assert original == digest(args.apk)
    assert runtime_before == runtime_identity(), "Runtime changed during string verification"
    assert verifiers == {path.name: digest(path) for path in verifier_paths}
    report = {
        "status": "all_literal_string_sites_equal",
        "apk_sha256": original,
        "runtime_sha256": runtime_before,
        "runtime_unchanged": True,
        "verifier_sha256": verifiers,
        "verifiers_unchanged": True,
        "original_unchanged": True,
        "scope": __doc__,
        "value": args.value,
        "case_sensitive": not args.ignore_case,
        "total_sites": len(expected),
        "scanned_methods": methods,
        "scanned_instructions": instructions,
        "methods_without_code": without_code,
        "scanned_high_id_jumbo_sites": high_jumbo,
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
    parser.add_argument("--value", required=True)
    parser.add_argument("--ignore-case", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.value:
        parser.error("value must be nonempty")
    main(args)
