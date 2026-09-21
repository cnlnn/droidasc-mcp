"""Run every Droid ASC MCP operation against one or more local APKs."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apks", nargs="+", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--max-worker-memory-mib", type=int, default=1024)
    args = parser.parse_args()

    apks = [path.resolve(strict=True) for path in args.apks]
    roots = tuple(dict.fromkeys(path.parent for path in apks))
    settings = Settings(
        allowed_roots=roots,
        timeout_seconds=args.timeout,
        max_worker_memory_bytes=args.max_worker_memory_mib * 1024**2,
    )
    service = DroidAscService(settings)
    report = {
        "generated_at_unix": int(time.time()),
        "ping": service.ping(),
        "apks": [],
    }

    for apk in apks:
        started = time.monotonic()
        info = service.apk_info(str(apk))
        manifest = service.get_manifest(str(apk), offset=0, limit=1)
        classes = service.list_classes(str(apk), prefix=None, threads=8, offset=0, limit=1)
        if not classes["items"]:
            raise RuntimeError(f"No classes found in {apk}")
        source = service.get_class_source(
            str(apk),
            class_name=classes["items"][0],
            threads=8,
            offset=0,
            limit=10,
        )
        refs = service.find_refs(
            str(apk),
            kind="string",
            value="android",
            class_name=None,
            fuzzy_class=False,
            threads=8,
            offset=0,
            limit=5,
        )
        report["apks"].append(
            {
                "name": apk.name,
                "sha256": info["sha256"],
                "size_bytes": info["size_bytes"],
                "dex_entries": info["dex_entries"],
                "manifest_lines": manifest["total"],
                "class_count": classes["total"],
                "sample_class": classes["items"][0],
                "source_lines": source["total"],
                "android_string_refs": refs["total"],
                "elapsed_seconds": round(time.monotonic() - started, 3),
            }
        )

    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
