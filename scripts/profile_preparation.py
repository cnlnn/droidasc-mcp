"""Profile validated preparation and the first native query, without hiding either cost.

This direct-worker diagnostic is not a replacement for real MCP/process-tree benchmarks.
"""

import argparse
import cProfile
import json
import pstats
import tempfile
import time
from pathlib import Path

from droidasc_mcp.config import Settings
from droidasc_mcp.dex_worker import analyze
from droidasc_mcp.runner import DroidAscRunner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--expanded-mib", type=int, default=128)
    args = parser.parse_args()
    if not 1 <= args.expanded_mib <= 2048:
        parser.error("expanded-mib must be between 1 and 2048")
    apk = args.apk.resolve(strict=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    runner = DroidAscRunner(Settings(allowed_roots=(apk.parent,)))
    results = {}
    with tempfile.TemporaryDirectory(prefix="droidasc-profile-") as temporary:
        root = Path(temporary)
        prepared = root / "prepared"
        prepared.mkdir()
        request = runner._dex_request([], {"offset": 0, "limit": 100})
        request.update(
            artifact_path=str(apk),
            max_uncompressed_bytes=args.expanded_mib * 1024**2,
            prepare=True,
        )
        phases = ("preparation",) if args.prepare_only else ("preparation", "first_query")
        for label in phases:
            if label == "first_query":
                request = runner._dex_request(
                    [],
                    {
                        "operation": "find_field_refs",
                        "field_descriptor": "Landroid/os/Build;->MODEL:Ljava/lang/String;",
                        "offset": 0,
                        "limit": 100,
                    },
                )
                request["prepared_root"] = str(prepared)
            profile = cProfile.Profile()
            started = time.perf_counter()
            result = profile.runcall(analyze, request, prepared if label == "preparation" else root)
            elapsed = time.perf_counter() - started
            assert result["status"] == "ok", result
            path = args.output.with_suffix("." + label + ".pstats")
            profile.dump_stats(path)
            results[label] = {
                "seconds": elapsed,
                "class_count": result.get("class_count"),
                "total": result.get("total"),
                "profile": str(path),
            }
            print(label, elapsed)
            pstats.Stats(profile).strip_dirs().sort_stats("cumulative").print_stats(30)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
