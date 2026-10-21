"""Measure real MCP cold/warm graphs; optionally verify emitted sites with Androguard."""

import argparse
import asyncio
import gc
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


def dex_names(archive):
    names = [n for n in archive.namelist() if re.fullmatch(r"classes(?:[2-9]|[1-9]\d+)?\.dex", n)]
    assert names and len(names) <= 64 and len(names) == len(set(names))
    assert sum(archive.getinfo(n).file_size for n in names) <= 2 * 1024**3
    return sorted(names, key=lambda n: 1 if n == "classes.dex" else int(n[7:-4]))


async def benchmark(args):
    apk = args.apk.resolve(strict=True)
    report = {"status": "running", "apk_sha256": sha256(apk), "operations": []}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="droidasc-graph-") as directory:
        root = Path(directory)
        paths = []
        with zipfile.ZipFile(apk) as archive:
            report["dex_entries"] = dex_names(archive)
            for name in report["dex_entries"]:
                path = root / name
                with archive.open(name) as source, path.open("wb") as target:
                    shutil.copyfileobj(source, target)
                paths.append(str(path))
        env = {
            **os.environ,
            "DROIDASC_MCP_ALLOWED_ROOTS": str(root),
            "DROIDASC_MCP_TIMEOUT_SECONDS": "900",
            "DROIDASC_MCP_MAX_XREF_INDEX_BYTES": str(4096 * 1024**2),
            "DROIDASC_MCP_MAX_DEX_SESSION_BYTES": str(6144 * 1024**2),
        }
        env.pop("DROIDASC_MCP_XREF_CACHE_DIR", None)
        endpoint = StdioServerParameters(
            command=sys.executable, args=["-m", "droidasc_mcp"], env=env
        )
        try:
            async with Client(endpoint) as client:

                async def call(label, tool, **params):
                    started = time.monotonic()
                    reply = await client.call_tool(tool, params)
                    result = reply.structured_content
                    assert not reply.is_error and result and result["status"] == "ok", reply
                    metric = {
                        "label": label,
                        "seconds": round(time.monotonic() - started, 4),
                        **{
                            k: result[k]
                            for k in (
                                "input_id",
                                "index",
                                "node_count",
                                "edge_count",
                                "truncation_reasons",
                                "dynamic_sites",
                            )
                            if k in result
                        },
                    }
                    report["operations"].append(metric)
                    save()
                    print(json.dumps(metric), flush=True)
                    return result

                opened = await call("open", "asc_open_dex_session", dex_paths=paths)
                key = opened["session_id"]
                query = {
                    "session_id": key,
                    "operation": "get_call_graph",
                    "method_descriptor": args.method_descriptor,
                    "direction": "incoming",
                    "depth": 2,
                    "max_nodes": 64,
                    "max_edges": 96,
                }
                cold = await call(
                    "graph:cold_including_full_index", "asc_query_dex_session", **query
                )
                assert not cold["index"]["reused"]
                report["graph"] = cold
                for i in range(3):
                    warm = await call(f"graph:warm:{i}", "asc_query_dex_session", **query)
                    assert warm["index"]["reused"]
                    assert warm["nodes"] == cold["nodes"] and warm["edges"] == cold["edges"]
                stress = await call(
                    "graph:fanout",
                    "asc_query_dex_session",
                    **{
                        **query,
                        "depth": 5,
                        "direction": "both",
                        "max_nodes": 500,
                        "max_edges": 1000,
                    },
                )
                assert stress["node_count"] <= 500 and stress["edge_count"] <= 1000
                report["fanout_graph"] = stress
                await call("close", "asc_close_dex_session", session_id=key)
            report["original_unchanged"] = sha256(apk) == report["apk_sha256"]
            assert report["original_unchanged"]
            report["status"] = "passed"
        except BaseException as exc:
            report.update(status="failed", error=str(exc))
            raise
        finally:
            save()


def verify_sites(args):
    from androguard.core.dex import DEX
    from loguru import logger

    logger.remove()
    report = json.loads(args.output.read_text(encoding="utf-8"))
    assert sha256(args.apk) == report["apk_sha256"]
    edges = [e for key in ("graph", "fanout_graph") for e in report[key]["edges"]]
    wanted = {(e["dex_entry"], e["caller"]) for e in edges}
    oracle = set()
    with zipfile.ZipFile(args.apk) as archive:
        for name in dex_names(archive):
            if not any(entry == name for entry, _ in wanted):
                continue
            dex = DEX(archive.read(name))
            for cls in dex.get_classes():
                for method in cls.get_methods():
                    caller = (
                        method.get_class_name()
                        + "->"
                        + method.get_name()
                        + "".join(method.get_descriptor().split())
                    )
                    if (name, caller) not in wanted:
                        continue
                    for offset, instruction in method.get_instructions_idx():
                        op = instruction.get_op_value()
                        if 0x6E <= op <= 0x72 or 0x74 <= op <= 0x78 or op in {0xFA, 0xFB}:
                            owner, member, prototype = dex.get_cm_method(instruction.get_ref_kind())
                            callee = owner + "->" + member + "".join("".join(prototype).split())
                            oracle.add((name, caller, callee, offset // 2, instruction.get_name()))
            del dex
            gc.collect()
    expected = {
        (e["dex_entry"], e["caller"], e["callee"], e["instruction_offset"], e["opcode"])
        for e in edges
    }
    assert expected <= oracle, sorted(expected - oracle)[:5]
    report["independent_emitted_site_oracle"] = {
        "backend": "androguard sequential method instruction decoding",
        "matched_unique_call_sites": len(expected),
        "scope": "emitted graph sites, not full-corpus graph completeness",
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["independent_emitted_site_oracle"]))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--method-descriptor",
        default=("Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;"),
    )
    parser.add_argument("--verify-sites", action="store_true")
    arguments = parser.parse_args()
    if arguments.verify_sites:
        verify_sites(arguments)
    else:
        asyncio.run(benchmark(arguments))
