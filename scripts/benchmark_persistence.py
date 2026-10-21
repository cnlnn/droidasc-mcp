"""Verify real MCP index reuse after server exit against every DEX in a local APK."""

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from benchmark_backends import sha256
from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def benchmark(args):
    apk = args.apk.resolve(strict=True)
    args.cache_dir = args.cache_dir.absolute()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "apk_sha256": sha256(apk),
        "apk_bytes": apk.stat().st_size,
        "index_mib": args.index_mib,
        "cache_mib": args.cache_mib,
        "operations": [],
        "status": "running",
    }

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    with tempfile.TemporaryDirectory(prefix="droidasc-persistence-") as directory:
        root = Path(directory)
        paths = []
        with zipfile.ZipFile(apk) as archive:
            names = [n for n in archive.namelist() if re.fullmatch(r"classes\d*\.dex", n)]
            names.sort(key=lambda n: 1 if n == "classes.dex" else int(n[7:-4]))
            for name in names:
                path = root / name
                with archive.open(name) as source, path.open("wb") as target:
                    shutil.copyfileobj(source, target)
                paths.append(str(path))
        report["dex_entries"] = names
        env = {
            **os.environ,
            "DROIDASC_MCP_ALLOWED_ROOTS": str(root),
            "DROIDASC_MCP_TIMEOUT_SECONDS": "900",
            "DROIDASC_MCP_XREF_CACHE_DIR": str(args.cache_dir),
            "DROIDASC_MCP_MAX_XREF_CACHE_BYTES": str(args.cache_mib * 1024**2),
            "DROIDASC_MCP_MAX_XREF_INDEX_BYTES": str(args.index_mib * 1024**2),
            "DROIDASC_MCP_MAX_DEX_SESSION_BYTES": str((args.index_mib + 2048) * 1024**2),
        }

        async def call(client, label, tool, **params):
            started = time.monotonic()
            reply = await client.call_tool(tool, params)
            result = reply.structured_content
            assert not reply.is_error and result and result.get("status", "ok") == "ok", reply
            metric = {"label": label, "seconds": round(time.monotonic() - started, 4)}
            for key in ("total", "index", "edge_counts", "class_count", "input_id"):
                if key in result:
                    metric[key] = result[key]
            report["operations"].append(metric)
            save()
            print(json.dumps(metric), flush=True)
            return result

        query = {
            "operation": "find_field_refs",
            "field_descriptor": "Landroid/os/Build;->MODEL:Ljava/lang/String;",
            "limit": 1000,
        }
        try:
            for restarted in (False, True):
                if restarted:
                    env["DROIDASC_MCP_JAVA"] = "missing-java-proves-index-reuse"
                endpoint = StdioServerParameters(
                    command=sys.executable, args=["-m", "droidasc_mcp"], env=env
                )
                async with Client(endpoint) as client:
                    opened = await call(
                        client, f"open:{restarted}", "asc_open_dex_session", dex_paths=paths
                    )
                    key = opened["session_id"]
                    if not restarted:
                        before = await call(
                            client,
                            "reference:before",
                            "asc_query_dex_session",
                            session_id=key,
                            **query,
                        )
                        built = await call(
                            client,
                            "index:build",
                            "asc_query_dex_session",
                            session_id=key,
                            operation="build_xref_index",
                        )
                        assert built["index"]["durable_cache"] in ("stored", "restored")
                    else:
                        after = await call(
                            client,
                            "reference:restart",
                            "asc_query_dex_session",
                            session_id=key,
                            **query,
                        )
                        assert after["index"]["durable_cache"] == "restored", after
                        assert (
                            after["total"]
                            == before["total"]
                            == len(after["items"])
                            == len(before["items"])
                        )
                        assert after["items"] == before["items"]
                        assert after["input_id"] == before["input_id"]
                        report["all_field_rows_identical_after_restart"] = True
                    await call(
                        client, f"close:{restarted}", "asc_close_dex_session", session_id=key
                    )
            report["source_hash_unchanged"] = sha256(apk) == report["apk_sha256"]
            assert report["source_hash_unchanged"]
            report["status"] = "passed"
        except BaseException as exc:
            report.update(status="failed", error=str(exc))
            raise
        finally:
            save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--index-mib", type=int, default=4096)
    parser.add_argument("--cache-mib", type=int, default=6144)
    asyncio.run(benchmark(parser.parse_args()))
