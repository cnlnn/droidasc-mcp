"""Check named-method MCP handoffs against exact queries and independent original DEX decoding.

Acceptance-only Androguard and the pinned competitor can be installed with
``uv run --with ./artifacts/aimard-asc-mcp python scripts/verify_method_selection.py ...``.
This is bounded workflow/accuracy evidence, not an exhaustive or performance comparison.
"""

import argparse
import asyncio
import gc
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path

from benchmark_competitor_runtime import competitor_runtime_identity, query_content
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from verify_fuzzy_references import digest, runtime_identity


def original_methods(apk):
    from androguard.core.dex import DEX
    from loguru import logger

    logger.remove()
    selected = overloaded = None
    with zipfile.ZipFile(apk) as archive:
        entry = sorted(
            name
            for name in archive.namelist()
            if "/" not in name and name.startswith("classes") and name.endswith(".dex")
        )[0]
        dex = DEX(archive.read(entry))
        for cls in sorted(dex.get_classes(), key=lambda row: row.get_name()):
            methods = list(cls.get_methods())
            counts = Counter(method.get_name() for method in methods)
            for method in methods:
                if overloaded is None and counts[method.get_name()] > 1:
                    overloaded = {
                        "class_name": cls.get_name(),
                        "method_name": method.get_name(),
                        "target_descriptor": "".join(method.get_descriptor().split()),
                        "candidate_count": counts[method.get_name()],
                    }
                if selected is not None or counts[method.get_name()] != 1:
                    continue
                instructions = list(method.get_instructions_idx())
                if not 1 <= len(instructions) <= 12 or any(
                    instruction.get_op_value() >= 0xFA for _, instruction in instructions
                ):
                    continue
                selected = {
                    "class_name": cls.get_name(),
                    "method_name": method.get_name(),
                    "prototype": "".join(method.get_descriptor().split()),
                    "container_entry": entry,
                    "instructions": [
                        (offset // 2, insn.get_name()) for offset, insn in instructions
                    ],
                }
            if selected is not None and overloaded is not None:
                break
    assert selected is not None and overloaded is not None
    return selected, overloaded


async def main(args):
    args.apk = args.apk.resolve(strict=True)
    assert not args.output.exists(), "Preserve previous acceptance attempts"
    runtime, helper, original = runtime_identity(), digest(Path(__file__)), digest(args.apk)
    competitor = competitor_runtime_identity(args.competitor)
    selected, overloaded = original_methods(args.apk)
    gc.collect()
    method = selected["class_name"] + "->" + selected["method_name"] + selected["prototype"]
    report = {
        "status": "running",
        "apk_sha256": original,
        "runtime_sha256": runtime,
        "verifier_sha256": helper,
        "selected": selected,
        "overloaded": overloaded,
        "competitor_runtime": competitor,
        "competitor_commit": subprocess.check_output(
            ["git", "-C", str(args.competitor), "rev-parse", "HEAD"],
            text=True,
        ).strip(),
        "scope": "one independently selected definition and overload in the original first DEX; "
        "five real-MCP named/exact operation pairs, plus competitor disassembly and ambiguity; "
        "not exhaustive class/site parity or a timing comparison",
        "operations": [],
    }
    environment = {
        **os.environ,
        "DROIDASC_MCP_ALLOWED_ROOTS": str(args.apk.parent),
        "ASC_MCP_ALLOWED_ROOTS": str(args.apk.parent),
        "DROIDASC_MCP_MAX_DEX_SESSION_BYTES": str(8192 * 1024**2),
        "DROIDASC_MCP_TIMEOUT_SECONDS": "180",
        "DROIDASC_MCP_JAVA": "java-must-not-run",
        "ASC_MCP_WORKERS": "2",
    }
    for key in ("DROIDASC_MCP_JADX_HOME", "DROIDASC_MCP_DEXLIB_HOME"):
        environment.pop(key, None)

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    def endpoint(module):
        return StdioServerParameters(command=sys.executable, args=["-m", module], env=environment)

    save()
    try:
        async with Client(endpoint("droidasc_mcp")) as client:

            async def call(tool, **params):
                reply = await client.call_tool(tool, params)
                assert not reply.is_error, reply
                return reply.structured_content

            opened = await call(
                "asc_open_artifact_session",
                artifact_path=str(args.apk),
                max_uncompressed_bytes=512 * 1024**2,
            )
            assert opened["status"] == "ok", opened
            key = opened["session_id"]

            async def query(operation, **selection):
                return await call(
                    "asc_query_dex_session",
                    session_id=key,
                    operation=operation,
                    limit=1000,
                    depth=1,
                    max_nodes=500,
                    max_edges=1000,
                    **selection,
                )

            try:
                for operation in (
                    "disassemble_method",
                    "get_method_source",
                    "get_method_calls",
                    "find_method_refs",
                    "get_call_graph",
                ):
                    named = await query(
                        operation,
                        class_name=selected["class_name"],
                        method_name=selected["method_name"],
                    )
                    exact = await query(operation, method_descriptor=method)
                    assert named["status"] == exact["status"] == "ok", (named, exact)
                    assert named["method_descriptor"] == method and named["candidate_count"] == 1
                    left, right = query_content(named), query_content(exact)
                    for field in (
                        "method_name",
                        "candidate_count",
                        "method_descriptor",
                        "class_name",
                        "dex_entry",
                    ):
                        left.pop(field, None)
                        right.pop(field, None)
                    assert left == right, operation
                    if operation == "disassemble_method":
                        assert not named["has_more"]
                        assert [
                            (row["instruction_offset"], row["opcode"]) for row in named["items"]
                        ] == selected["instructions"]
                    report["operations"].append(
                        {
                            "operation": operation,
                            "status": "passed",
                            "response_sha256": hashlib.sha256(
                                json.dumps(left, sort_keys=True).encode()
                            ).hexdigest(),
                        }
                    )
                    save()
                ambiguous = await query(
                    "disassemble_method",
                    class_name=overloaded["class_name"],
                    method_name=overloaded["method_name"],
                )
                assert ambiguous["code"] == "ambiguous_method", ambiguous
                assert ambiguous["candidate_count"] == overloaded["candidate_count"]
                resolved = await query(
                    "disassemble_method",
                    **{key: value for key, value in overloaded.items() if key != "candidate_count"},
                )
                assert resolved["status"] == "ok" and resolved["candidate_count"] == 1, resolved
                report["overload_recovery"] = "passed"
            finally:
                assert (await call("asc_close_dex_session", session_id=key))["status"] == "ok"
                assert (await call("asc_ping"))["dex_sessions"]["open_count"] == 0
        async with Client(endpoint("asc_mcp")) as client:
            opened = await client.call_tool("load_artifact", {"path": str(args.apk)})
            assert not opened.is_error, opened
            key = opened.structured_content["analysis_id"]
            try:
                reply = await client.call_tool(
                    "apk_disassemble_method",
                    {
                        "analysis_id": key,
                        "class_name": selected["class_name"],
                        "method_name": selected["method_name"],
                    },
                )
                assert not reply.is_error, reply
                actual = reply.structured_content
                assert actual["descriptor"] == selected["prototype"]
                assert [
                    (row["offset"] // 2, row["opcode"]) for row in actual["instructions"]
                ] == selected["instructions"]
                ambiguous = await client.call_tool(
                    "apk_disassemble_method",
                    {
                        "analysis_id": key,
                        "class_name": overloaded["class_name"],
                        "method_name": overloaded["method_name"],
                    },
                )
                assert ambiguous.is_error and "overloaded" in str(ambiguous)
                report["competitor_disassembly_and_ambiguity"] = "passed"
            finally:
                closed = await client.call_tool("close_artifact", {"analysis_id": key})
                assert not closed.is_error, closed
        assert digest(args.apk) == original and runtime_identity() == runtime
        assert digest(Path(__file__)) == helper
        assert competitor_runtime_identity(args.competitor) == competitor
        report.update(status="passed", input_runtime_and_verifier_unchanged=True)
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--competitor", type=Path, default=Path("artifacts/aimard-asc-mcp"))
    asyncio.run(main(parser.parse_args()))
