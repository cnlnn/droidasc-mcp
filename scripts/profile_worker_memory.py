"""Diagnose fresh preparation-worker RSS and allocator effects, not MCP latency.

The normal supervised runner and validation path are unchanged. Diagnostic allocator
variants apply only to fresh child processes and are not production defaults.
"""

import argparse
import json
import os
import platform
import tempfile
import threading
import time
from contextlib import suppress
from pathlib import Path

import psutil
from verify_fuzzy_references import digest, runtime_identity

from droidasc_mcp.config import Settings
from droidasc_mcp.runner import DroidAscRunner


def trial(args, variant):
    for name in ("PYTHONMALLOC", "MALLOC_ARENA_MAX"):
        os.environ.pop(name, None)
    if "malloc" in variant:
        os.environ["PYTHONMALLOC"] = "malloc"
    if "arena1" in variant:
        os.environ["MALLOC_ARENA_MAX"] = "1"
    stop = threading.Event()
    parent, peak = psutil.Process(), 0
    phases, peak_maps = {}, []
    settings = Settings(allowed_roots=(args.apk.parent,), java_executable="java-must-not-run")
    with tempfile.TemporaryDirectory(prefix="droidasc-memory-") as temporary:
        root = Path(temporary)

        def monitor():
            nonlocal peak, peak_maps
            while not stop.is_set():
                try:
                    lines = (root / "progress.jsonl").read_text(encoding="utf-8").splitlines()
                    phase = json.loads(lines[-1])["message"] if lines else "startup"
                except (OSError, ValueError, KeyError):
                    phase = "startup"
                total = 0
                for child in parent.children(recursive=True):
                    with suppress(psutil.Error):
                        total += child.memory_info().rss
                if total > peak and args.memory_maps:
                    maps = []
                    for child in parent.children(recursive=True):
                        with suppress(psutil.Error, NotImplementedError):
                            maps.extend(
                                {"pid": child.pid, "path": row.path, "rss_bytes": row.rss}
                                for row in child.memory_maps()
                            )
                    peak_maps = sorted(maps, key=lambda row: row["rss_bytes"], reverse=True)
                peak = max(peak, total)
                phases[phase] = max(phases.get(phase, 0), total)
                stop.wait(0.005)

        watcher = threading.Thread(target=monitor)
        watcher.start()
        started = time.monotonic()
        try:
            result = DroidAscRunner(settings).prepare_artifact(
                args.apk, root, args.expanded_mib * 1024**2, None
            )
        finally:
            stop.set()
            watcher.join()
        assert result["status"] == "ok", result
        return {
            "variant": variant,
            "peak_worker_tree_rss_bytes": peak,
            "phase_peaks": phases,
            "class_count": result["class_count"],
            "peak_maps_diagnostic": peak_maps,
            "seconds_with_sampling_overhead": time.monotonic() - started,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--expanded-mib", type=int, default=128)
    parser.add_argument("--memory-maps", action="store_true")
    args = parser.parse_args()
    assert args.rounds > 0 and 0 < args.expanded_mib <= 2048
    args.apk = args.apk.resolve(strict=True)
    source, identity = digest(args.apk), runtime_identity()
    variants = ["default", "malloc"]
    if platform.system() == "Linux":
        variants += ["arena1", "malloc-arena1"]
    before = {name: os.environ.get(name) for name in ("PYTHONMALLOC", "MALLOC_ARENA_MAX")}
    results = []
    try:
        for number in range(args.rounds):
            for variant in variants if number % 2 == 0 else reversed(variants):
                result = trial(args, variant)
                results.append({"round": number, **result})
                print(json.dumps(result), flush=True)
    finally:
        for name, value in before.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
    report = {
        "input_sha256": source,
        "runtime_sha256": identity,
        "runtime_unchanged": runtime_identity() == identity,
        "input_unchanged": digest(args.apk) == source,
        "platform": platform.platform(),
        "trials": results,
        "notes": "Worker-only diagnostic; includes sampling overhead, not MCP latency authority. "
        "Allocator variants are experimental, not production defaults.",
    }
    assert report["runtime_unchanged"] and report["input_unchanged"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
