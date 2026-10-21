"""Real stdio MCP benchmark: original APK backends and all-DEX indexed/streamed parity."""

import argparse
import asyncio
import hashlib
import json
import os
import platform
import re
import shutil
import sys
import tempfile
import time
import zipfile
from contextlib import suppress
from pathlib import Path

import psutil
from mcp import Client
from mcp.client.stdio import StdioServerParameters


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


async def benchmark(args):
    apk = args.apk.resolve(strict=True)
    report = {
        "apk": apk.name,
        "apk_bytes": apk.stat().st_size,
        "apk_sha256": sha256(apk),
        "generated_at_unix": int(time.time()),
        "platform": platform.platform(),
        "python": sys.version,
        "operations": [],
        "status": "running",
        "notes": (
            "Wall time includes MCP/worker startup. Page comparisons are not a full-corpus oracle."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="droidasc-benchmark-") as directory:
        root = Path(directory)
        env = {
            **os.environ,
            "DROIDASC_MCP_ALLOWED_ROOTS": os.pathsep.join([str(apk.parent), str(root)]),
            "DROIDASC_MCP_TIMEOUT_SECONDS": "900",
            "DROIDASC_MCP_MAX_XREF_INDEX_BYTES": str(args.index_mib * 1024**2),
            "DROIDASC_MCP_MAX_DEX_SESSION_BYTES": str((args.index_mib + 2048) * 1024**2),
        }
        endpoint = StdioServerParameters(
            command=sys.executable, args=["-m", "droidasc_mcp"], env=env
        )
        async with Client(endpoint) as client:

            async def call(label, tool, **params):
                start = time.monotonic()
                peak = 0
                running = True

                async def sample():
                    nonlocal peak
                    while running:
                        total = 0
                        for child in psutil.Process().children(recursive=True):
                            with suppress(psutil.Error):
                                total += child.memory_info().rss
                        peak = max(peak, total)
                        await asyncio.sleep(0.05)

                monitor = asyncio.create_task(sample())
                try:
                    reply = await client.call_tool(tool, params)
                    result = reply.structured_content
                    assert not reply.is_error and result, reply
                    assert result.get("status", "ok") == "ok", result
                finally:
                    running = False
                    await monitor
                metric = {
                    "label": label,
                    "seconds": round(time.monotonic() - start, 4),
                    "peak_descendant_rss_bytes": peak,
                }
                for key in (
                    "total",
                    "class_count",
                    "index",
                    "edge_counts",
                    "definition_count",
                    "coverage",
                    "instruction_scan_complete",
                    "query_cache",
                ):
                    if key in result:
                        metric[key] = result[key]
                report["operations"].append(metric)
                save()
                print(json.dumps(metric), flush=True)
                return result

            try:
                ping = await call("capabilities", "asc_ping")
                report["engines"] = {
                    k: ping[k] for k in ("droidasc_version", "rust_backend", "method_backend")
                }
                counts = []
                for backend in () if args.interactive else ("droidasc", "rust_asc"):
                    result = await call(
                        backend + ":classes",
                        "asc_list_classes",
                        apk_path=str(apk),
                        backend=backend,
                        limit=10,
                        threads=2,
                    )
                    counts.append(result["total"])
                    await call(
                        backend + ":manifest",
                        "asc_get_manifest",
                        apk_path=str(apk),
                        backend=backend,
                        limit=5,
                    )
                    await call(
                        backend + ":source",
                        "asc_get_class_source",
                        apk_path=str(apk),
                        backend=backend,
                        class_name=result["items"][0],
                        limit=10,
                        threads=2,
                    )
                    await call(
                        backend + ":string",
                        "asc_find_refs",
                        apk_path=str(apk),
                        backend=backend,
                        kind="string",
                        value="https://",
                        limit=10,
                        threads=2,
                    )
                if counts:
                    report["backend_class_counts_equal"] = counts[0] == counts[1]
                    assert counts[0] == counts[1], counts
                if not args.backends_only:
                    paths = []
                    with zipfile.ZipFile(apk) as archive:
                        names = [
                            n
                            for n in archive.namelist()
                            if re.fullmatch(r"classes(?:[2-9]|[1-9][0-9]+)?\.dex", n)
                        ]
                        names.sort(key=lambda n: 1 if n == "classes.dex" else int(n[7:-4]))
                        for name in names:
                            path = root / name
                            with archive.open(name) as source, path.open("wb") as target:
                                shutil.copyfileobj(source, target)
                            paths.append(str(path))
                    report["dex_entries"] = names
                    opened = await call("session:open", "asc_open_dex_session", dex_paths=paths)
                    key = opened["session_id"]
                    queries = [
                        {
                            "operation": "find_method_refs",
                            "method_descriptor": "Ljava/lang/String;->equals(Ljava/lang/Object;)Z",
                        },
                        {
                            "operation": "find_field_refs",
                            "field_descriptor": "Landroid/os/Build;->MODEL:Ljava/lang/String;",
                        },
                    ]
                    if args.interactive:
                        queries[:0] = [
                            {"operation": "search_members", "kind": "method", "value": "->equals("},
                            {"operation": "search_strings", "value": "https://"},
                        ]
                    baseline = []
                    for query in queries:
                        baseline.append(
                            await call(
                                "stream:" + query["operation"],
                                "asc_query_dex_session",
                                session_id=key,
                                limit=100,
                                **query,
                            )
                        )
                    if not args.interactive:
                        await call(
                            "index:build",
                            "asc_query_dex_session",
                            session_id=key,
                            operation="build_xref_index",
                        )
                    for repeat in range(3):
                        for query, expected in zip(queries, baseline, strict=True):
                            mode = "cache" if args.interactive else "index"
                            actual = await call(
                                f"{mode}:{query['operation']}:{repeat}",
                                "asc_query_dex_session",
                                session_id=key,
                                limit=100,
                                **query,
                            )
                            ignored = {"index", "backend", "query_cache"}
                            assert {k: v for k, v in actual.items() if k not in ignored} == {
                                k: v for k, v in expected.items() if k not in ignored
                            }, "Stream/reuse parity failed"
                        if not args.interactive:
                            await call(
                                f"index:type:{repeat}",
                                "asc_query_dex_session",
                                session_id=key,
                                operation="find_type_refs",
                                type_descriptor="Landroid/app/Activity;",
                                limit=100,
                            )
                    await call("session:close", "asc_close_dex_session", session_id=key)
                    report["queries"] = queries
                    report["stream_reuse_parity"] = "complete counts/diagnostics and first 100 rows"
                assert sha256(apk) == report["apk_sha256"]
                report["original_unchanged"] = True
                report["status"] = "passed"
            except BaseException as exc:
                report["status"] = "failed"
                report["failure"] = str(exc)
                raise
            finally:
                save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--index-mib", type=int, default=4096)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--backends-only", action="store_true")
    mode.add_argument(
        "--interactive", action="store_true", help="Discovery and exact-page cache, no full index"
    )
    asyncio.run(benchmark(parser.parse_args()))


if __name__ == "__main__":
    main()
