"""Exercise concurrent workers for a fixed interval and check resource recovery."""

from __future__ import annotations

import argparse
import gc
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psutil

from droidasc_mcp.config import Settings
from droidasc_mcp.runner import DroidAscRunner


def _resource_count(process: psutil.Process) -> int:
    return process.num_handles() if os.name == "nt" else process.num_fds()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apks", nargs="+", type=Path)
    parser.add_argument("--duration", type=float, default=300)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--max-worker-memory-mib", type=int, default=2048)
    parser.add_argument("--max-host-rss-growth-mib", type=int, default=256)
    args = parser.parse_args()
    if args.duration <= 0 or args.workers <= 0:
        parser.error("--duration and --workers must be greater than zero")

    apks = [path.resolve(strict=True) for path in args.apks]
    roots = tuple(dict.fromkeys(path.parent for path in apks))
    settings = Settings(
        allowed_roots=roots,
        timeout_seconds=args.timeout,
        max_parallel=args.workers,
        max_worker_memory_bytes=args.max_worker_memory_mib * 1024**2,
    )
    runner = DroidAscRunner(settings)
    owner = psutil.Process()

    # Warm imports and platform supervision before taking the resource baseline.
    for apk in apks:
        runner.apk_info(apk, False)
    baseline_rss = owner.memory_info().rss
    peak_rss = baseline_rss
    baseline_resources = _resource_count(owner)
    deadline = time.monotonic() + args.duration
    stop = threading.Event()
    counts = [0] * args.workers
    errors: list[str] = []

    def exercise(worker: int) -> None:
        iteration = 0
        while not stop.is_set() and time.monotonic() < deadline:
            apk = apks[(worker + iteration) % len(apks)]
            try:
                if iteration % 2:
                    runner.list_classes(
                        apk,
                        prefix=f"__droidasc_stability_{worker}_{iteration}",
                        threads=2,
                        offset=0,
                        limit=1,
                    )
                else:
                    runner.apk_info(apk, include_sha256=False)
                counts[worker] += 1
            except BaseException as exc:
                errors.append(f"worker={worker} iteration={iteration}: {exc!r}")
                stop.set()
                return
            iteration += 1

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(exercise, worker) for worker in range(args.workers)]
        while not stop.wait(0.05) and time.monotonic() < deadline:
            peak_rss = max(peak_rss, owner.memory_info().rss)
        stop.set()
        for future in futures:
            future.result(timeout=args.timeout + 5)

    gc.collect()
    time.sleep(0.2)
    final_rss = owner.memory_info().rss
    final_resources = _resource_count(owner)
    live_children = [
        child.pid
        for child in owner.children(recursive=True)
        if child.is_running() and child.status() != psutil.STATUS_ZOMBIE
    ]
    summary = {
        "duration_seconds": args.duration,
        "workers": args.workers,
        "operations": sum(counts),
        "operations_per_worker": counts,
        "errors": errors,
        "baseline_rss_bytes": baseline_rss,
        "peak_rss_bytes": peak_rss,
        "final_rss_bytes": final_rss,
        "final_rss_growth_bytes": final_rss - baseline_rss,
        "baseline_resources": baseline_resources,
        "final_resources": final_resources,
        "live_child_pids": live_children,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    max_growth = args.max_host_rss_growth_mib * 1024**2
    if errors:
        raise SystemExit("stability operations failed")
    if sum(counts) < args.workers * 2:
        raise SystemExit("too few stability operations completed")
    if final_rss - baseline_rss > max_growth:
        raise SystemExit("host RSS did not recover within the configured allowance")
    if final_resources > baseline_resources + 4:
        raise SystemExit("host handles/file descriptors did not recover")
    if live_children:
        raise SystemExit("worker processes remained after stability run")


if __name__ == "__main__":
    main()
