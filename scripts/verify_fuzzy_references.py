"""Compare a complete native fuzzy union with independent Androguard decoding."""

import argparse
import gc
import hashlib
import json
import tempfile
import zipfile
from dataclasses import replace
from pathlib import Path


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024**2):
            result.update(block)
    return result.hexdigest()


def runtime_identity():
    import droidasc_mcp

    return {
        path.name: digest(path)
        for path in sorted(Path(droidasc_mcp.__file__).parent.iterdir())
        if path.suffix in {".py", ".java", ".c", ".so", ".pyd", ".json"}
    }


def method_reference_index(instruction):
    # Androguard's 45cc/4rcc decoders expose BBBB but inherit an unimplemented get_ref_kind.
    if instruction.get_op_value() in {0xFA, 0xFB}:
        return instruction.BBBB
    return instruction.get_ref_kind()


def main(args):
    from androguard.core.dex import DEX
    from loguru import logger

    from droidasc_mcp.config import Settings
    from droidasc_mcp.native_dex import query_references

    logger.remove()
    runtime_before = runtime_identity()
    verifier_before = digest(Path(__file__))
    original = digest(args.apk)
    expected = []
    target_names = set()
    scanned_instructions = 0
    with tempfile.TemporaryDirectory(prefix="fuzzy-oracle-") as directory:
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
        settings = replace(Settings.from_env(), max_page_size=2**31 - 1)
        result = query_references(
            settings,
            bundle,
            {
                "operation": "search_refs",
                "kind": "method",
                "value": "equal",
                "member_match": "name",
                "class_name": "java/lang",
                "fuzzy_class": True,
                "offset": 0,
                "limit": 2**31 - 1,
            },
        )
        assert result["status"] == "ok" and result["instruction_scan_complete"]
        assert len(result["items"]) == result["total"]
        with zipfile.ZipFile(bundle) as archive:
            for entry in entries:
                dex = DEX(archive.read(entry))
                targets = {}
                for index, method in enumerate(dex.get_methods()):
                    owner, name = method.get_class_name(), method.get_name()
                    if "java/lang" in owner and "equal" in name:
                        targets[index] = (
                            owner + "->" + name + "".join(method.get_descriptor().split())
                        )
                for cls in dex.get_classes():
                    for method in cls.get_methods():
                        caller = (
                            method.get_class_name()
                            + "->"
                            + method.get_name()
                            + "".join(method.get_descriptor().split())
                        )
                        for offset, instruction in method.get_instructions_idx():
                            scanned_instructions += 1
                            op = instruction.get_op_value()
                            if not (0x6E <= op <= 0x72 or 0x74 <= op <= 0x78 or op in {0xFA, 0xFB}):
                                continue
                            callee = targets.get(method_reference_index(instruction))
                            if callee is not None:
                                target_names.add(callee)
                                expected.append(
                                    (entry, caller, callee, offset // 2, instruction.get_name())
                                )
                del targets, dex
                gc.collect()
                print(json.dumps({"entry": entry, "verified_sites": len(expected)}), flush=True)
    actual = [
        (row["dex_entry"], row["caller"], row["callee"], row["instruction_offset"], row["opcode"])
        for row in result["items"]
    ]
    assert sorted(actual) == sorted(expected), "Complete fuzzy reference multiset differs"
    assert result["matched_targets"] == len(target_names)
    assert result["scanned_instructions"] == scanned_instructions
    assert original == digest(args.apk)
    assert runtime_before == runtime_identity(), "Runtime changed during fuzzy parity checks"
    assert verifier_before == digest(Path(__file__)), "Verifier changed during fuzzy parity checks"
    report = {
        "verifier_sha256": verifier_before,
        "verifier_unchanged": True,
        "runtime_sha256": runtime_before,
        "runtime_unchanged": True,
        "status": "all_fuzzy_sites_equal",
        "apk_sha256": original,
        "scope": "complete fuzzy method union: owner contains java/lang, name contains equal",
        "oracle": "Androguard method ID pools and sequential instruction decoding",
        "total_sites": len(expected),
        "matched_targets": sorted(target_names),
        "scanned_instructions": scanned_instructions,
        "site_multiset_sha256": hashlib.sha256(
            json.dumps(sorted(expected), separators=(",", ":")).encode()
        ).hexdigest(),
        "original_unchanged": True,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
