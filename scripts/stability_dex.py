"""Repeat concurrent immutable DEX/method session lifecycles and check resource recovery."""

import argparse
import gc
import json
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import psutil
from stability_check import _resource_count

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dex", nargs="+", type=Path)
    parser.add_argument("--method-descriptor", required=True)
    parser.add_argument("--iterations", type=int, default=6)
    args = parser.parse_args()
    if args.iterations < 2:
        parser.error("--iterations must be at least 2")
    paths = [str(p.resolve(strict=True)) for p in args.dex]
    settings = replace(Settings.from_env(), allowed_roots=tuple(Path(p).parent for p in paths))
    service = DroidAscService(settings)
    roots = []
    identities = []

    def cycle(mode=0):
        opened = service.open_dex_session(paths)
        assert opened["status"] == "ok", opened
        key = opened["session_id"]
        roots.append(Path(service.sessions.entries[key].storage.name))
        identities.append(opened["input_id"])
        try:
            query = {"operation": "info", "offset": 0, "limit": 100}
            if mode:
                query.update(
                    operation="get_method_calls" if mode == 2 else "get_method_source",
                    method_descriptor=args.method_descriptor,
                    source_format="smali" if mode == 3 else "auto",
                )
            result = service.query_dex_session(key, **query)
            assert result["status"] == "ok", result
            assert result["input_id"] == opened["input_id"]
            if mode == 2:
                assert result["instruction_scan_complete"] is True
                assert result["method_descriptor"] == args.method_descriptor
            elif mode:
                assert result["method_descriptor"] == args.method_descriptor and result["source"]
        finally:
            assert service.sessions.close(key)["cleanup_pending"] is False

    owner = psutil.Process()
    try:
        cycle(1)
        gc.collect()
        baseline_rss, baseline_handles = owner.memory_info().rss, _resource_count(owner)
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda index: cycle(index % 4), range(args.iterations * 2)))
    finally:
        service.close()
    gc.collect()
    time.sleep(0.2)
    children = [p.pid for p in owner.children(recursive=True) if p.status() != psutil.STATUS_ZOMBIE]
    summary = {
        "cycles": len(identities),
        "distinct_input_ids": len(set(identities)),
        "host_rss_growth": owner.memory_info().rss - baseline_rss,
        "handle_growth": _resource_count(owner) - baseline_handles,
        "live_children": children,
        "remaining_storage": [str(p) for p in roots if p.exists()],
        "remaining_sessions": len(service.sessions.entries),
        "reaper_alive": service.sessions.reaper.is_alive(),
    }
    print(json.dumps(summary, indent=2))
    assert summary["host_rss_growth"] < 128 * 1024**2
    assert summary["handle_growth"] <= 4
    assert summary["distinct_input_ids"] == 1
    assert not children and not summary["remaining_storage"]
    assert not summary["remaining_sessions"] and not summary["reaper_alive"]


if __name__ == "__main__":
    main()
