"""Measure real MCP cold/warm graphs; optionally verify emitted sites with Androguard."""

import argparse
import asyncio
import gc
import hashlib
import json
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from benchmark_backends import sha256
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from verify_fuzzy_references import method_reference_index, runtime_identity


async def benchmark(args):
    apk = args.apk.resolve(strict=True)
    report = {
        "status": "running",
        "apk_sha256": sha256(apk),
        "runtime_sha256": runtime_identity(),
        "verifier_sha256": sha256(Path(__file__)),
        "oracle_sha256": sha256(Path(__file__).with_name("verify_fuzzy_references.py")),
        "operations": [],
        "notes": "Real stdio diagnostic, not a matched competitor comparison. "
        "Preparation is included in first-result time; no full index is built.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="droidasc-graph-") as directory:
        root = Path(directory)
        env = {
            **os.environ,
            "DROIDASC_MCP_ALLOWED_ROOTS": str(apk.parent),
            "DROIDASC_MCP_TIMEOUT_SECONDS": "900",
            "DROIDASC_MCP_MAX_OUTPUT_BYTES": str(64 * 1024**2),
            "DROIDASC_MCP_MAX_XREF_INDEX_BYTES": str(1024 * 1024**2),
            "DROIDASC_MCP_MAX_DEX_SESSION_BYTES": str((7 * args.expanded_mib + 1280) * 1024**2),
            "DROIDASC_MCP_JAVA": "java-must-not-run",
            "TMPDIR": str(root),
            "TEMP": str(root),
            "TMP": str(root),
        }
        for name in (
            "DROIDASC_MCP_XREF_CACHE_DIR",
            "DROIDASC_MCP_JADX_HOME",
            "DROIDASC_MCP_DEXLIB_HOME",
        ):
            env.pop(name, None)
        report["configured_budgets"] = {
            name: value for name, value in env.items() if name.startswith("DROIDASC_MCP_MAX_")
        }
        endpoint = StdioServerParameters(
            command=sys.executable, args=["-m", "droidasc_mcp"], env=env
        )
        try:
            process_started = time.monotonic()
            async with Client(endpoint) as client:

                async def call(label, tool, **params):
                    started = time.monotonic()
                    reply = await client.call_tool(tool, params)
                    result = reply.structured_content
                    assert not reply.is_error and result and result["status"] == "ok", reply
                    metric = {
                        "label": label,
                        "seconds": round(time.monotonic() - started, 4),
                        "response_from_start_seconds": round(time.monotonic() - process_started, 4),
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

                opened = await call(
                    "open",
                    "asc_open_artifact_session",
                    artifact_path=str(apk),
                    max_uncompressed_bytes=args.expanded_mib * 1024**2,
                )
                report["sources"] = opened["sources"]
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
                cold = await call("graph:cold_frontier", "asc_query_dex_session", **query)
                assert cold["backend"] == "native-dex-frontier" and "index" not in cold
                report["graph"] = cold
                for i in range(3):
                    warm = await call(f"graph:warm:{i}", "asc_query_dex_session", **query)
                    assert warm["query_cache"]["hit"]
                    assert {k: v for k, v in warm.items() if k != "query_cache"} == {
                        k: v for k, v in cold.items() if k != "query_cache"
                    }
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
            assert not list(root.iterdir()), "Server close left owned temporary files behind"
            report["original_unchanged"] = sha256(apk) == report["apk_sha256"]
            report["runtime_unchanged"] = runtime_identity() == report["runtime_sha256"]
            report["verifier_unchanged"] = sha256(Path(__file__)) == report["verifier_sha256"]
            report["oracle_unchanged"] = (
                sha256(Path(__file__).with_name("verify_fuzzy_references.py"))
                == report["oracle_sha256"]
            )
            assert (
                report["original_unchanged"]
                and report["runtime_unchanged"]
                and report["verifier_unchanged"]
                and report["oracle_unchanged"]
            )
            report["status"] = "passed"
        except BaseException as exc:
            report.update(status="failed", error=str(exc))
            raise
        finally:
            save()


def verify_sites(args):
    report = json.loads(args.output.read_text(encoding="utf-8"))
    report["independent_emitted_site_oracle"] = {"status": "running"}
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        report["independent_emitted_site_oracle"] = _verify_sites(args, report)
    except BaseException as exc:
        report["independent_emitted_site_oracle"] = {"status": "failed", "error": repr(exc)}
        raise
    finally:
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["independent_emitted_site_oracle"]))


def emitted_edges(report):
    combined = []
    for name in ("graph", "fanout_graph"):
        graph = report[name]
        edges = graph["edges"]
        identities = {(row["dex_entry"], row["caller"], row["instruction_offset"]) for row in edges}
        assert graph["edge_count"] == len(edges), "Graph edge count differs from emitted rows"
        assert len(identities) == len(edges), "Graph repeats an individual instruction site"
        combined.extend(edges)
    return combined


def _verify_sites(args, report):
    from androguard.core.dex import DEX
    from loguru import logger

    logger.remove()
    assert report["status"] == "passed", "Transport benchmark did not pass"
    assert sha256(args.apk) == report["apk_sha256"]
    assert report["runtime_sha256"] == runtime_identity(), "Runtime differs from measured graph"
    assert report["verifier_sha256"] == sha256(Path(__file__)), "Verifier changed after measurement"
    assert report["oracle_sha256"] == sha256(
        Path(__file__).with_name("verify_fuzzy_references.py")
    ), "Oracle changed after measurement"
    edges = emitted_edges(report)
    wanted = {(e["dex_entry"], e["caller"]) for e in edges}
    source_entries = {row["dex_entry"]: row for row in report["sources"]}
    assert len(source_entries) == len(report["sources"]), "Duplicate canonical source entry"
    oracle = set()
    with zipfile.ZipFile(args.apk) as archive:
        for name, source in source_entries.items():
            if not any(entry == name for entry, _ in wanted):
                continue
            raw = archive.read(source["container_entry"])
            assert hashlib.sha256(raw).hexdigest() == source["sha256"], "Source mapping differs"
            dex = DEX(raw)
            del raw
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
                            owner, member, prototype = dex.get_cm_method(
                                method_reference_index(instruction)
                            )
                            callee = owner + "->" + member + "".join("".join(prototype).split())
                            call_proto = ""
                            if op in {0xFA, 0xFB}:
                                index = instruction.HHHH
                                call_proto = "".join("".join(dex.CM.get_proto(index)).split())
                            oracle.add(
                                (
                                    name,
                                    caller,
                                    callee,
                                    offset // 2,
                                    instruction.get_name(),
                                    call_proto,
                                )
                            )
            del dex
            gc.collect()
    expected = {
        (
            e["dex_entry"],
            e["caller"],
            e["callee"],
            e["instruction_offset"],
            e["opcode"],
            e.get("call_site_prototype", ""),
        )
        for e in edges
    }
    assert expected <= oracle, sorted(expected - oracle)[:5]
    assert sha256(args.apk) == report["apk_sha256"], "Input changed during verification"
    assert report["runtime_sha256"] == runtime_identity(), "Runtime changed during verification"
    assert report["verifier_sha256"] == sha256(Path(__file__)), (
        "Verifier changed during verification"
    )
    assert report["oracle_sha256"] == sha256(
        Path(__file__).with_name("verify_fuzzy_references.py")
    ), "Oracle changed during verification"
    return {
        "status": "passed",
        "backend": "androguard sequential method instruction decoding",
        "matched_unique_call_sites": len(expected),
        "scope": "emitted graph sites, not full-corpus graph completeness",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expanded-mib", type=int, choices=range(1, 2049), default=128)
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
