"""Check real-MCP compact APK summaries against original ZIP entries and a pinned competitor.

Install the competitor in this interpreter as described in verify_method_selection.py.
This checks summary values and stateless cleanup, not DEX accuracy or performance.
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

from benchmark_competitor_runtime import competitor_runtime_identity
from mcp import Client
from mcp.client.stdio import StdioServerParameters
from verify_fuzzy_references import digest, runtime_identity


async def main(args):
    paths = [path.resolve(strict=True) for path in args.apks]
    assert not args.output.exists(), "Preserve previous acceptance attempts"
    runtime = runtime_identity()
    verifier = digest(Path(__file__))
    competitor = competitor_runtime_identity(args.competitor)
    report = {
        "status": "running",
        "scope": "APK compact summary parity through real MCP stdio; original ZIP/hash oracle; "
        "not DEX analysis, complete workflow acceptance or a timing comparison",
        "runtime_sha256": runtime,
        "verifier_sha256": verifier,
        "python": sys.version,
        "competitor_runtime": competitor,
        "competitor_commit": subprocess.check_output(
            ["git", "-C", str(args.competitor), "rev-parse", "HEAD"], text=True
        ).strip(),
        "artifacts": [],
    }

    def save():
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    save()
    try:
        for path in paths:
            original = digest(path)
            with zipfile.ZipFile(path) as archive:
                infos = archive.infolist()
                dex = sorted(
                    info.filename for info in infos if info.filename.lower().endswith(".dex")
                )
                libraries = [
                    info.filename.split("/")
                    for info in infos
                    if info.filename.startswith("lib/")
                    and info.filename.endswith(".so")
                    and len(info.filename.split("/")) == 3
                    and not info.is_dir()
                ]
                abis = sorted({parts[1] for parts in libraries})
            environment = {
                **os.environ,
                "DROIDASC_MCP_ALLOWED_ROOTS": str(path.parent),
                "ASC_MCP_ALLOWED_ROOTS": str(path.parent),
                "DROIDASC_MCP_JAVA": "java-must-not-run",
                "DROIDASC_MCP_TIMEOUT_SECONDS": "180",
            }

            def endpoint(module, env=environment):
                return StdioServerParameters(command=sys.executable, args=["-m", module], env=env)

            async with Client(endpoint("droidasc_mcp")) as client:
                reply = await client.call_tool(
                    "asc_inspect_artifact", {"artifact_path": str(path), "include_summary": True}
                )
                assert not reply.is_error, reply
                ours = reply.structured_content
                assert ours["status"] == "ok", ours
                summary = ours["summary"]
                assert ours["artifact_sha256"] == original
                assert ours["artifact_size_bytes"] == path.stat().st_size
                assert ours["dex_entries"] == dex
                assert summary["entry_count"] == len(infos)
                assert summary["native_scope"] == "archive"
                assert summary["native_library_count"] == len(libraries)
                assert summary["native_abi_count"] == len(abis)
                assert summary["native_abis"] == abis[:100]
                assert summary["native_abis_truncated"] == (len(abis) > 100)
                assert summary["manifest"]["status"] == "ok", summary["manifest"]
                assert summary["manifest"]["resource_values_resolved"] is False
                ping = await client.call_tool("asc_ping", {})
                assert not ping.is_error
                assert ping.structured_content["dex_sessions"]["open_count"] == 0
            async with Client(endpoint("asc_mcp")) as client:
                opened = await client.call_tool("load_artifact", {"path": str(path)})
                assert not opened.is_error, opened
                key = opened.structured_content["analysis_id"]
                try:
                    reply = await client.call_tool("apk_get_summary", {"analysis_id": key})
                    assert not reply.is_error, reply
                    other = reply.structured_content
                    assert other["sha256"] == original
                    assert other["size_bytes"] == ours["artifact_size_bytes"]
                    assert sorted(other["dex_files"]) == dex
                    assert other["entry_count"] == summary["entry_count"]
                    assert other["native_abis"] == abis
                    for field in (
                        "package_name",
                        "version_name",
                        "version_code",
                        "min_sdk",
                        "target_sdk",
                    ):
                        assert other[field] == summary["manifest"][field], field
                finally:
                    closed = await client.call_tool("close_artifact", {"analysis_id": key})
                    assert not closed.is_error, closed
            assert digest(path) == original
            report["artifacts"].append(
                {
                    "path": str(path),
                    "sha256": original,
                    "size_bytes": ours["artifact_size_bytes"],
                    "dex_count": len(dex),
                    "summary": summary,
                    "status": "passed",
                }
            )
            save()
        assert all(digest(Path(row["path"])) == row["sha256"] for row in report["artifacts"])
        assert runtime_identity() == runtime and digest(Path(__file__)) == verifier
        assert competitor_runtime_identity(args.competitor) == competitor
        report.update(status="passed", input_runtime_and_verifier_unchanged=True)
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apks", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--competitor", type=Path, default=Path("artifacts/aimard-asc-mcp"))
    asyncio.run(main(parser.parse_args()))
