"""Persist original-byte 041 checks through actual stdio and HTTP MCP servers."""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import tempfile
import zipfile
from contextlib import AsyncExitStack, nullcontext
from pathlib import Path
from unittest.mock import patch

import psutil
from mcp import Client
from mcp.client.stdio import StdioServerParameters


async def verify(root):
    sys.path[:0] = [str(Path(__file__).resolve().parents[1] / "tests"), str(Path(__file__).parent)]
    from test_integration import running_http_endpoint
    from test_native_dex041 import headers, original_oracle, shared_container
    from verify_fuzzy_references import digest, runtime_identity

    root.mkdir(parents=True)
    runtime = runtime_identity()
    report = {"status": "running", "runtime_sha256": runtime, "fixtures": [], "transports": []}
    cases = []
    for sharing in ("none", "forward", "backward_compat"):
        data = shared_container(("A", "B"), sharing, references=True)
        oracle = [original_oracle(data, header) for header in headers(data)]
        for archived in (False, True):
            path = root / (sharing + (".apk" if archived else ".dex"))
            if archived:
                with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("classes.dex", data)
            else:
                path.write_bytes(data)
            cases.append((path, data, oracle))
            report["fixtures"].append(
                {
                    "path": str(path),
                    "sha256": digest(path),
                    "physical_dex_sha256": hashlib.sha256(data).hexdigest(),
                    "oracle": oracle,
                    "logical_header_offsets": headers(data),
                }
            )
    environment = {
        **os.environ,
        "DROIDASC_MCP_JAVA": "java-must-not-run",
        "DROIDASC_MCP_ALLOWED_ROOTS": str(root),
        "ASC_TEST_ROOT": str(root),
        "DROIDASC_MCP_TOOL_PROFILE": "artifact",
    }
    for name in ("DROIDASC_MCP_JADX_HOME", "DROIDASC_MCP_DEXLIB_HOME"):
        environment.pop(name, None)
    try:
        for transport in ("stdio", "http"):
            directory = root / transport
            directory.mkdir()
            events = directory / "events.jsonl"
            before = {(p.pid, p.create_time()) for p in psutil.Process().children(recursive=True)}
            with tempfile.TemporaryDirectory(prefix="owned-", dir=directory) as temporary:
                env = {**environment, **dict.fromkeys(("TMPDIR", "TEMP", "TMP"), temporary)}
                with (
                    patch.dict(os.environ, env, clear=True),
                    running_http_endpoint(directory)
                    if transport == "http"
                    else nullcontext(None) as http,
                ):
                    endpoint = http or StdioServerParameters(
                        command=sys.executable, args=["-m", "droidasc_mcp"], env=env
                    )
                    async with AsyncExitStack() as stack:
                        client = await stack.enter_async_context(Client(endpoint))
                        stream = stack.enter_context(events.open("x"))

                        async def call(tool, *, _client=client, _stream=stream, **arguments):
                            reply = await _client.call_tool(tool, arguments)
                            result = reply.structured_content
                            _stream.write(
                                json.dumps(
                                    {
                                        "tool": tool,
                                        "arguments": arguments,
                                        "is_error": reply.is_error,
                                        "result": result,
                                        "error_text": str(reply.content)
                                        if reply.is_error
                                        else None,
                                    }
                                )
                                + "\n"
                            )
                            _stream.flush()
                            assert not reply.is_error and result.get("status", "ok") == "ok", result
                            return result

                        for path, data, oracle in cases:
                            loaded = await call(
                                "load_artifact", path=str(path), max_uncompressed_bytes=1024**2
                            )
                            key = loaded["analysis_id"]
                            info = await call("apk_get_dex_info", analysis_id=key)
                            assert info["class_count"] == len(oracle)
                            assert [
                                row["logical_header_offset"] for row in info["sources"]
                            ] == headers(data)
                            assert all(
                                row["sha256"] == hashlib.sha256(data).hexdigest()
                                for row in info["sources"]
                            )
                            assert sum(row["stored_size_bytes"] for row in info["sources"]) == len(
                                data
                            )
                            inventory, offset = [], 0
                            while True:
                                page = await call(
                                    "apk_list_classes", analysis_id=key, offset=offset, limit=1
                                )
                                inventory.extend(row["class_name"] for row in page["items"])
                                if not page["has_more"]:
                                    break
                                offset = page["next_offset"]
                            assert inventory == [row[0] for row in oracle]
                            for owner, method, _code, value in oracle:
                                constants = await call(
                                    "apk_get_string_constants", analysis_id=key, class_name=owner
                                )
                                assert [row["value"] for row in constants["items"]] == [value]
                                for tool, kwargs, opcode, address in [
                                    (
                                        "apk_find_string_references",
                                        {"value": value},
                                        "const-string",
                                        0,
                                    ),
                                    (
                                        "apk_find_method_references",
                                        {"method_descriptor": method},
                                        "invoke-static",
                                        6,
                                    ),
                                    (
                                        "apk_find_field_references",
                                        {"field_descriptor": owner + "->field:Ljava/lang/String;"},
                                        "sget-object",
                                        4,
                                    ),
                                ]:
                                    result = await call(tool, analysis_id=key, limit=1, **kwargs)
                                    assert (
                                        result["total"] == 1
                                        and result["items"][0]["caller"] == method
                                    )
                                    assert (
                                        result["items"][0]["opcode"],
                                        result["items"][0]["instruction_offset"],
                                    ) == (opcode, address)
                                    repeat = await call(tool, analysis_id=key, limit=2, **kwargs)
                                    assert repeat["items"] == result["items"]
                                graph = await call(
                                    "apk_get_call_graph", analysis_id=key, method_descriptor=method
                                )
                                assert [
                                    (edge["caller"], edge["callee"], edge["instruction_offset"])
                                    for edge in graph["edges"]
                                ] == [(method, method, 6)]
                                source = await call(
                                    "apk_get_method_source",
                                    analysis_id=key,
                                    class_name=owner,
                                    method_descriptor=method,
                                    source_format="smali",
                                    limit=100,
                                )
                                assert value in source["source"]
                            assert (await call("close_artifact", analysis_id=key))["closed"]
                        # Rejected import must not poison the next public request.
                        bad = root / "malformed.dex"
                        bad.write_bytes(b"dex\n041\0" + bytes(112))
                        reply = await client.call_tool(
                            "asc_open_dex_session", {"dex_paths": [str(bad)]}
                        )
                        stream.write(
                            json.dumps(
                                {
                                    "tool": "asc_open_dex_session",
                                    "malformed": True,
                                    "is_error": reply.is_error,
                                    "result": reply.structured_content,
                                }
                            )
                            + "\n"
                        )
                        assert not reply.is_error and reply.structured_content["status"] == "error"
                        assert (await call("asc_ping"))["dex_sessions"]["open_count"] == 0
                    assert not list(Path(temporary).iterdir())
                assert not list(Path(temporary).iterdir())
            assert not Path(temporary).exists()
            survivors = [
                p.pid
                for p in psutil.Process().children(recursive=True)
                if (p.pid, p.create_time()) not in before
            ]
            assert not survivors, survivors
            report["transports"].append(
                {
                    "transport": transport,
                    "status": "passed",
                    "events_sha256": digest(events),
                    "owned_temporary_empty_and_removed": True,
                    "surviving_children": survivors,
                }
            )
        assert all(digest(Path(case["path"])) == case["sha256"] for case in report["fixtures"])
        assert runtime_identity() == runtime
        report["status"] = "passed"
    except BaseException as exc:
        report.update(status="failed", error=repr(exc))
        raise
    finally:
        (root / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {key: value for key, value in report.items() if key != "runtime_sha256"}, indent=2
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(verify(args.output_directory.resolve()))


if __name__ == "__main__":
    main()
