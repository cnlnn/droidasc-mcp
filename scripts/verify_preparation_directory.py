"""Verify every prepared class/owner and snapshot against original APK DEX bytes.

The oracle uses the pure Python DEX cursor, never the mapped C directory reader.
Its whole-inventory dictionary is acceptance-only, not a product memory policy.
"""

import argparse
import hashlib
import json
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from itertools import zip_longest
from pathlib import Path

from verify_fuzzy_references import digest, runtime_identity

from droidasc_mcp.native_dex import Dex


def verify_ownership(apk, root, prepared):
    expected = {}
    records = prepared["sources"]
    with zipfile.ZipFile(apk) as original, zipfile.ZipFile(root / "analysis.apk") as snapshot:
        selected = sorted(name for name in original.namelist() if name.lower().endswith(".dex"))
        assert len(selected) == len(records), "Original DEX inventory mismatch"
        assert snapshot.namelist() == [record["dex_entry"] for record in records]
        for index, (name, record) in enumerate(zip(selected, records, strict=True)):
            entry = "classes.dex" if index == 0 else f"classes{index + 1}.dex"
            assert record["container_entry"] == name and record["dex_entry"] == entry
            data = original.read(name)
            sha256 = hashlib.sha256(data).hexdigest()
            assert sha256 == record["sha256"] and len(data) == record["size_bytes"]
            copied = hashlib.sha256()
            with snapshot.open(entry) as stream:
                while block := stream.read(256 * 1024):
                    copied.update(block)
            assert copied.hexdigest() == sha256, "Snapshot differs from original DEX"
            dex = Dex(data)
            try:
                names = [name for name, _ in dex.classes(accelerator=False, ordered=False)]
            finally:
                dex.close()
            assert len(names) == record["class_count"] == record["declared_class_count"]
            for name in names:
                assert name not in expected, "Ambiguous original class definition"
                expected[name] = entry
    assert len(expected) == prepared["class_count"]
    matched = hashlib.sha256()
    with closing(sqlite3.connect((root / "owners.sqlite").as_uri() + "?mode=ro", uri=True)) as db:
        version = db.execute("PRAGMA user_version").fetchone()[0]
        assert version in (0, 1, 2), "Unsupported ownership key format"
        if version == 2:
            assert db.execute("SELECT id,name FROM entries ORDER BY id").fetchall() == [
                (index + 1, record["dex_entry"]) for index, record in enumerate(records)
            ], "DEX ownership dictionary differs"
            actual = db.execute(
                "SELECT classes.name,entries.name FROM classes LEFT JOIN entries "
                "ON classes.entry=entries.id ORDER BY classes.name"
            )
        else:
            actual = db.execute("SELECT name,entry FROM classes ORDER BY name")
        ordered = sorted(
            expected.items(), key=lambda row: row[0].encode("utf-16-be", "surrogatepass")
        )
        for wanted, row in zip_longest(ordered, actual):
            assert wanted is not None and row is not None, "Class inventory size differs"
            name, entry = row
            # Deliberately independent of the product key encoder/decoder. Encode
            # the oracle name one UTF-16 code unit at a time for the compact format.
            expected_key = wanted[0].encode("utf-16-be", "surrogatepass")
            if version >= 1:
                expected_key = b"".join(
                    chr(int.from_bytes(expected_key[i : i + 2], "big")).encode(
                        "utf-8", "surrogatepass"
                    )
                    for i in range(0, len(expected_key), 2)
                )
            assert (name, entry) == (expected_key, wanted[1]), (
                "Class identity/ownership mismatch",
                wanted,
            )
            matched.update((json.dumps(wanted, ensure_ascii=True) + "\n").encode("ascii"))
    metadata = json.loads((root / "prepared.json").read_text(encoding="utf-8"))["common"]
    assert metadata == {key: value for key, value in prepared.items() if key != "status"}
    return {
        "dex_count": len(records),
        "exact_classes_and_owners": len(expected),
        "ordered_class_owner_sha256": matched.hexdigest(),
        "snapshot_bytes_match_original": True,
        "common_metadata_exact_match": True,
        "owners_stored_bytes": (root / "owners.sqlite").stat().st_size,
        "snapshot_stored_bytes": (root / "analysis.apk").stat().st_size,
    }


def main(args):
    from droidasc_mcp.config import Settings
    from droidasc_mcp.runner import DroidAscRunner

    args.apk = args.apk.resolve(strict=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "running",
        "apk_sha256": digest(args.apk),
        "runtime_sha256": runtime_identity(),
        "verifier_sha256": digest(Path(__file__)),
        "scope": "all_standard_direct_apk_dex_classes_owners_and_snapshot_bytes",
        "oracle": "pure_python_original_dex_cursor_accelerator_false",
        "notes": "Accuracy diagnostic only; whole-oracle memory is not product RSS or MCP latency.",
    }
    try:
        settings = Settings(allowed_roots=(args.apk.parent,), java_executable="java-must-not-run")
        with tempfile.TemporaryDirectory(prefix="ownership-oracle-") as temporary:
            root = Path(temporary)
            prepared = DroidAscRunner(settings).prepare_artifact(
                args.apk, root, args.expanded_mib * 1024**2, None
            )
            assert prepared["status"] == "ok", prepared
            report.update(
                input_id=prepared["input_id"], **verify_ownership(args.apk, root, prepared)
            )
        report["input_unchanged"] = digest(args.apk) == report["apk_sha256"]
        report["runtime_unchanged"] = runtime_identity() == report["runtime_sha256"]
        assert report["input_unchanged"] and report["runtime_unchanged"]
        report["status"] = "passed"
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "runtime_sha256"}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--expanded-mib", type=int, choices=range(1, 2049), default=512)
    parser.add_argument("--output", type=Path, required=True)
    main(parser.parse_args())
