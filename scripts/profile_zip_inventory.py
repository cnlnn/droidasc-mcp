"""Fresh-process directory diagnostics; not MCP startup or release acceptance.

Alternate stdlib and compact inventories over the identical immutable archive.
No input/member validation is bypassed; the diagnostic measures only directory
inventory construction, not decompression, preparation or first-result latency.
"""

import argparse
import hashlib
import json
import subprocess
import sys
import time
import zipfile
from contextlib import suppress
from pathlib import Path

import psutil
from verify_fuzzy_references import digest, runtime_identity

from droidasc_mcp.archive_worker import _entries
from droidasc_mcp.preparation_zip import PreparationZipFile


def worker(path, implementation):
    archive_type = zipfile.ZipFile if implementation == "stdlib" else PreparationZipFile
    started = time.monotonic()
    with path.open("rb") as source, archive_type(source) as archive:
        entries = _entries(archive) if implementation == "stdlib" else archive.inventory
        rows = []
        for name in sorted(entries):
            if name.lower().endswith((".dex", ".class", ".jar", ".apk")):
                info = entries[name]
                rows.append(
                    [
                        name,
                        info.file_size,
                        info.compress_size,
                        info.CRC,
                        info.flag_bits,
                        info.external_attr,
                        info.header_offset,
                        info._end_offset,
                    ]
                )
        print(
            json.dumps(
                {
                    "implementation": implementation,
                    "seconds": time.monotonic() - started,
                    "entry_count": len(entries),
                    "retained_info_count": len(archive.filelist),
                    "inventory_sha256": hashlib.sha256(
                        json.dumps(sorted(entries), ensure_ascii=True).encode()
                    ).hexdigest(),
                    "selected_metadata_sha256": hashlib.sha256(
                        json.dumps(rows, ensure_ascii=True).encode()
                    ).hexdigest(),
                }
            ),
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--worker", choices=["stdlib", "compact"])
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    args.apk = args.apk.resolve(strict=True)
    if args.worker:
        worker(args.apk, args.worker)
        return
    if not args.output or args.rounds < 1:
        parser.error("output and positive rounds are required")
    identity, original = runtime_identity(), digest(args.apk)
    trials = []
    for number in range(args.rounds):
        order = ["stdlib", "compact"] if number % 2 == 0 else ["compact", "stdlib"]
        for implementation in order:
            process = subprocess.Popen(
                [sys.executable, __file__, str(args.apk), "--worker", implementation],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            peak, observed = 0, psutil.Process(process.pid)
            try:
                deadline = time.monotonic() + 120
                while process.poll() is None:
                    with suppress(psutil.Error):
                        peak = max(peak, observed.memory_info().rss)
                    if time.monotonic() > deadline:
                        process.kill()
                        raise TimeoutError("Directory diagnostic exceeded 120 seconds")
                    time.sleep(0.005)
                stdout, stderr = process.communicate(timeout=5)
                if process.returncode:
                    raise RuntimeError(stderr.decode(errors="replace"))
                row = {"round": number, **json.loads(stdout), "peak_process_rss_bytes": peak}
                trials.append(row)
                print(json.dumps(row), flush=True)
            finally:
                if process.poll() is None:
                    process.kill()
                process.communicate()
    stable = runtime_identity() == identity and digest(args.apk) == original
    fields = ("entry_count", "inventory_sha256", "selected_metadata_sha256")
    equal = all(all(row[key] == trials[0][key] for key in fields) for row in trials)
    report = {
        "status": "passed" if stable and equal else "failed",
        "input_sha256": original,
        "runtime_sha256": identity,
        "runtime_and_input_unchanged": stable,
        "all_inventory_and_selected_metadata_equal": equal,
        "notes": "Directory-only fresh-process diagnostic, not MCP/startup performance authority.",
        "trials": trials,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    assert report["status"] == "passed", report


if __name__ == "__main__":
    main()
