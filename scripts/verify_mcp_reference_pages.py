"""Verify every MCP reference page against a frozen independent JVM instruction scanner.

This is accuracy acceptance for standard, top-level multidex APKs, not a latency benchmark.
The scanner and its jars are acceptance inputs, separate from the measured server process.
"""

import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from verify_fuzzy_references import digest, runtime_identity

QUERIES = (
    ("find_method_refs", "method_descriptor", "Ljava/lang/String;->equals(Ljava/lang/Object;)Z"),
    ("find_field_refs", "field_descriptor", "Landroid/os/Build;->MODEL:Ljava/lang/String;"),
)


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def original_bundle(apk, bundle, sources, byte_limit):
    """Use only original bytes, mapped to the session's verified canonical entry names."""
    assert sources and len(sources) <= 64
    assert len({row["dex_entry"] for row in sources}) == len(sources)
    assert len({row["container_entry"] for row in sources}) == len(sources)
    assert sum(row["size_bytes"] for row in sources) <= byte_limit
    with zipfile.ZipFile(apk) as original, zipfile.ZipFile(bundle, "w") as output:
        inventory = original.infolist()
        names = sorted(
            info.filename for info in inventory if info.filename.lower().endswith(".dex")
        )
        assert len(names) == len(set(names)) == len(sources), "Original DEX inventory differs"
        wanted = [
            ("classes.dex" if i == 0 else f"classes{i + 1}.dex", name)
            for i, name in enumerate(names)
        ]
        actual = [(row["dex_entry"], row["container_entry"]) for row in sources]
        assert actual == wanted, "Canonical source mapping differs from original inventory"
        for row in sources:
            assert re.fullmatch(r"classes(?:\d+)?\.dex", row["dex_entry"])
            assert re.fullmatch(r"classes(?:\d+)?\.dex", row["container_entry"])
            infos = [info for info in inventory if info.filename == row["container_entry"]]
            assert len(infos) == 1 and infos[0].file_size == row["size_bytes"]
            checksum, size = hashlib.sha256(), 0
            with original.open(infos[0]) as source, output.open(row["dex_entry"], "w") as target:
                while block := source.read(256 * 1024):
                    size += len(block)
                    assert size <= row["size_bytes"]
                    checksum.update(block)
                    target.write(block)
            assert size == row["size_bytes"] and checksum.hexdigest() == row["sha256"]


def oracle(args, bundle, operation, descriptor):
    jars = sorted((args.oracle_home / "lib").glob("*.jar"))
    assert jars, "Independent scanner jars are missing"
    command = [
        str(args.java),
        f"-Xmx{args.oracle_heap_mib}m",
        "-Xss512k",
        "-XX:+UseSerialGC",
        "-XX:CompressedClassSpaceSize=64m",
        "-XX:ReservedCodeCacheSize=64m",
        "-cp",
        os.pathsep.join(map(str, jars)),
        str(args.baseline_source),
        str(bundle),
        "",
        "",
        operation,
        descriptor,
        "auto",
        "0",
        str(2**31 - 1),
        "all",
    ]
    reply = subprocess.run(command, capture_output=True, check=False, timeout=180)
    assert reply.returncode == 0, (
        "Independent scanner failed: " + reply.stderr.decode("utf-8", errors="replace")[-8192:]
    )
    result = json.loads(reply.stdout)
    assert result["status"] == "ok" and result["instruction_scan_complete"]
    assert len(result["items"]) == result["total"]
    result.pop("backend", None)
    result.pop("backend_version", None)
    return result


async def verify_pages(call, query, expected, page_size):
    offset, combined, pages, recoveries = 0, [], [], []
    while True:
        result = await call(**query, offset=offset, limit=page_size)
        if result.get("status") == "error":
            assert result.get("code") == "response_limit" and page_size > 1, result
            recoveries.append({"offset": offset, "limit": page_size, "code": "response_limit"})
            page_size = max(1, page_size // 2)
            continue
        assert result["offset"] == offset and result["limit"] == page_size
        for key, value in expected.items():
            if key != "items":
                assert result[key] == value, f"Page diagnostic differs: {key}"
        rows = result["items"]
        assert len(rows) <= page_size
        if "page_limited_by" in result:
            assert result["page_limited_by"] == "response_bytes"
            assert 0 < len(rows) < page_size
            maximum = result["response_byte_limit"]
            assert type(maximum) is int and 0 < maximum < 256 * 1024
            body = {k: v for k, v in result.items() if k != "session_id"}
            assert len(json.dumps(body).encode()) <= maximum
        assert rows == expected["items"][offset : offset + len(rows)], (
            "Ordered instruction rows differ"
        )
        combined.extend(rows)
        more = len(combined) < expected["total"]
        assert result["has_more"] == result["truncated"] == more
        next_offset = offset + len(rows) if more else None
        assert result["next_offset"] == next_offset, "Continuation skips or repeats rows"
        pages.append({"offset": offset, "count": len(rows), "items_sha256": fingerprint(rows)})
        if not more:
            break
        assert rows, "A nonterminal page must advance"
        offset = next_offset
    assert combined == expected["items"], "Complete ordered reference result differs"
    return {
        "status": "passed",
        "total": len(combined),
        "pages": pages,
        "response_limit_recoveries": recoveries,
        "full_result_sha256": fingerprint(expected),
        "scanned_instructions": expected["scanned_instructions"],
    }


async def main(args):
    args.apk = args.apk.resolve(strict=True)
    args.baseline_source = args.baseline_source.resolve(strict=True)
    args.java = args.java.resolve(strict=True)
    args.oracle_home = args.oracle_home.resolve(strict=True)
    assert not args.output.exists(), "Preserve previous acceptance attempts"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    dependencies = [
        Path(__file__),
        Path(__file__).with_name("verify_fuzzy_references.py"),
        args.baseline_source,
        args.java,
        *sorted((args.oracle_home / "lib").glob("*.jar")),
    ]
    report = {
        "status": "running",
        "apk_sha256": digest(args.apk),
        "runtime_sha256": runtime_identity(),
        "oracle_heap_mib": args.oracle_heap_mib,
        "acceptance_inputs_sha256": {str(path): digest(path) for path in dependencies},
        "scope": (
            "all ordered rows and scan diagnostics for two selected references over real stdio, "
            "against original APK bytes and a frozen independent JVM scanner; "
            "not all possible queries or a timing comparison"
        ),
        "operations": [],
    }

    def save():
        args.output.write_text(json.dumps(report, indent=2) + "\n")

    try:
        save()
        with tempfile.TemporaryDirectory(prefix="mcp-reference-pages-") as directory:
            root = Path(directory)
            owned = root / "server"
            owned.mkdir()
            env = {
                **os.environ,
                "DROIDASC_MCP_ALLOWED_ROOTS": str(args.apk.parent),
                "DROIDASC_MCP_TIMEOUT_SECONDS": "180",
                "DROIDASC_MCP_MAX_DEX_SESSION_BYTES": str(8192 * 1024**2),
                "DROIDASC_MCP_MAX_PAGE_SIZE": str(args.page_size),
                "DROIDASC_MCP_JAVA": "java-must-not-run",
                "TMPDIR": str(owned),
                "TEMP": str(owned),
                "TMP": str(owned),
            }
            for key in (
                "DROIDASC_MCP_JADX_HOME",
                "DROIDASC_MCP_DEXLIB_HOME",
                "DROIDASC_MCP_XREF_CACHE_DIR",
            ):
                env.pop(key, None)
            endpoint = StdioServerParameters(
                command=sys.executable, args=["-m", "droidasc_mcp"], env=env
            )
            async with Client(endpoint) as client:

                async def call_tool(tool, *, allow_response_limit=False, **params):
                    reply = await client.call_tool(tool, params, read_timeout_seconds=180)
                    result = reply.structured_content
                    assert not reply.is_error and result, reply
                    assert result["status"] == "ok" or (
                        allow_response_limit and result.get("code") == "response_limit"
                    ), reply
                    return result

                opened = await call_tool(
                    "asc_open_artifact_session",
                    artifact_path=str(args.apk),
                    max_uncompressed_bytes=args.expanded_mib * 1024**2,
                )
                assert opened["artifact_sha256"] == report["apk_sha256"]
                report["sources"] = opened["sources"]
                bundle = root / "original-canonical.apk"
                original_bundle(args.apk, bundle, opened["sources"], args.expanded_mib * 1024**2)
                report["oracle_bundle_sha256"] = digest(bundle)

                async def call(**query):
                    result = await call_tool(
                        "asc_query_dex_session",
                        session_id=opened["session_id"],
                        allow_response_limit=True,
                        **query,
                    )
                    if result["status"] == "error":
                        assert result["session_id"] == opened["session_id"]
                        return result
                    for key in ("session_id", "input_id", "artifact_sha256", "sources"):
                        assert result[key] == opened[key], f"Page provenance differs: {key}"
                    return result

                for operation, field, descriptor in QUERIES:
                    expected = await asyncio.to_thread(oracle, args, bundle, operation, descriptor)
                    result = await verify_pages(
                        call, {"operation": operation, field: descriptor}, expected, args.page_size
                    )
                    report["operations"].append(
                        {"operation": operation, "descriptor": descriptor, **result}
                    )
                    save()
                    print(
                        json.dumps(
                            {
                                "operation": operation,
                                "total": result["total"],
                                "pages": len(result["pages"]),
                                "status": result["status"],
                            }
                        ),
                        flush=True,
                    )
                closed = await call_tool("asc_close_dex_session", session_id=opened["session_id"])
                assert (
                    closed["session_id"] == opened["session_id"] and not closed["cleanup_pending"]
                )
            assert not list(owned.iterdir()), "Server left owned temporary files"
        assert not root.exists()
        assert report["apk_sha256"] == digest(args.apk)
        assert report["runtime_sha256"] == runtime_identity()
        assert report["acceptance_inputs_sha256"] == {
            str(path): digest(path) for path in dependencies
        }
        assert sorted((args.oracle_home / "lib").glob("*.jar")) == [
            path for path in dependencies if path.suffix == ".jar"
        ], "Independent scanner jar inventory changed"
        report.update(status="passed", input_runtime_oracle_unchanged=True, cleanup_verified=True)
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        save()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--baseline-source", type=Path, required=True)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--oracle-home", type=Path, required=True)
    parser.add_argument("--oracle-heap-mib", type=int, choices=range(128, 4097), default=1024)
    parser.add_argument("--page-size", type=int, choices=range(1, 1001), default=1000)
    parser.add_argument("--expanded-mib", type=int, choices=range(1, 2049), default=512)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
