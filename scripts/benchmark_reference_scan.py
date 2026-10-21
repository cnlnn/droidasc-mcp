"""Alternating fresh-JVM scans; compare every row and diagnostic with a frozen baseline."""

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--jadx-home", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--candidate-java-option", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    import droidasc_mcp

    sources = {
        "baseline": args.baseline_source.resolve(strict=True),
        "candidate": Path(droidasc_mcp.__file__).with_name("MethodBridge.java").resolve(),
    }
    report = {
        "apk_sha256": hashlib.sha256(args.apk.read_bytes()).hexdigest(),
        "source_sha256": {
            k: hashlib.sha256(v.read_bytes()).hexdigest() for k, v in sources.items()
        },
        "candidate_java_options": args.candidate_java_option,
        "notes": "Fresh JVM/source compilation per call, alternating order, OS cache not dropped. "
        "Direct backend scan, not MCP latency. Equality covers all rows and diagnostics.",
        "operations": [],
    }
    jars = os.pathsep.join(map(str, sorted((args.jadx_home.resolve() / "lib").glob("*.jar"))))
    with tempfile.TemporaryDirectory(prefix="reference-scan-") as directory:
        bundle = Path(directory) / "analysis.apk"
        with zipfile.ZipFile(args.apk) as original, zipfile.ZipFile(bundle, "w") as prepared:
            for name in sorted(original.namelist()):
                if "/" not in name and name.startswith("classes") and name.endswith(".dex"):
                    prepared.writestr(name, original.read(name), compress_type=zipfile.ZIP_STORED)
        for operation, descriptor in (
            ("find_method_refs", "Ljava/lang/String;->equals(Ljava/lang/Object;)Z"),
            ("find_field_refs", "Landroid/os/Build;->MODEL:Ljava/lang/String;"),
        ):
            expected = None
            for number in range(args.rounds):
                for label in list(sources) if number % 2 == 0 else list(reversed(sources)):
                    start = time.monotonic()
                    reply = subprocess.run(
                        [
                            str(args.java.resolve()),
                            "-Xmx512m",
                            "-Xss512k",
                            "-XX:+UseSerialGC",
                            "-XX:CompressedClassSpaceSize=64m",
                            "-XX:ReservedCodeCacheSize=64m",
                            *(args.candidate_java_option if label == "candidate" else []),
                            "-cp",
                            jars,
                            str(sources[label]),
                            str(bundle),
                            "",
                            "",
                            operation,
                            descriptor,
                            "auto",
                            "0",
                            str(2**31 - 1),
                            "all",
                        ],
                        capture_output=True,
                        check=True,
                        timeout=120,
                    )
                    elapsed = time.monotonic() - start
                    result = json.loads(reply.stdout)
                    assert result["status"] == "ok" and result["instruction_scan_complete"], result
                    assert len(result["items"]) == result["total"]
                    if expected is None:
                        expected = result
                    assert result == expected, f"Full result mismatch: {operation}, {label}"
                    metric = {
                        "operation": operation,
                        "implementation": label,
                        "round": number,
                        "seconds": round(elapsed, 4),
                        "total": result["total"],
                        "full_result_sha256": hashlib.sha256(
                            json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
                        ).hexdigest(),
                        "scanned_instructions": result["scanned_instructions"],
                    }
                    report["operations"].append(metric)
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
                    print(json.dumps(metric), flush=True)
    assert report["apk_sha256"] == hashlib.sha256(args.apk.read_bytes()).hexdigest()
    assert report["source_sha256"] == {
        k: hashlib.sha256(v.read_bytes()).hexdigest() for k, v in sources.items()
    }
    report["input_and_sources_unchanged"] = True
    report["status"] = "all_full_results_equal"
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
