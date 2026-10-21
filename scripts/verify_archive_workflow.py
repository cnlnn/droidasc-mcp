"""Verify public MCP APK queries against ZIP metadata and optional Android aapt2."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters


def aapt_tree(executable, apk, entry):
    result = subprocess.run(
        [str(executable), "dump", "xmltree", str(apk), "--file", entry],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        timeout=60,
        check=True,
    )
    parents, components, tags = [], [], []
    for line in result.stdout.splitlines():
        match = re.match(r"^( *)E: (\S+) \(line=", line)
        if match:
            depth, tag = len(match[1]), match[2]
            while parents and parents[-1][0] >= depth:
                parents.pop()
            if (
                parents
                and parents[-1][1] == "application"
                and tag in {"activity", "activity-alias", "service", "receiver", "provider"}
            ):
                components.append({"kind": tag, "name": None, "depth": depth})
            parents.append((depth, tag))
            tags.append(tag)
        match = re.match(
            r'^([ ]*)A: http://schemas.android.com/apk/res/android:name\([^)]*\)="([^"]*)"',
            line,
        )
        if (
            match
            and components
            and parents[-1] == (components[-1]["depth"], components[-1]["kind"])
            and len(match[1]) == components[-1]["depth"] + 2
        ):
            components[-1]["name"] = match[2]
    assert tags, "aapt2 returned no XML elements"
    return tags, [(c["kind"], c["name"]) for c in components]


async def verify(args):
    apk = args.apk.resolve()
    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    with zipfile.ZipFile(apk) as archive:
        expected = {
            i.filename: (i.file_size, i.compress_size, f"{i.CRC:08x}")
            for i in archive.infolist()
            if not i.is_dir()
        }
        resources = sorted(n for n in expected if n.startswith("res/") and n.endswith(".xml"))
    calls = []
    endpoint = StdioServerParameters(
        command=sys.executable,
        args=["-m", "droidasc_mcp"],
        env={**os.environ, "DROIDASC_MCP_ALLOWED_ROOTS": str(apk.parent)},
    )
    async with Client(endpoint) as client:

        async def query(tool, **kwargs):
            started = time.monotonic()
            reply = await client.call_tool(tool, {"apk_path": str(apk), **kwargs})
            assert not reply.is_error, reply
            data = reply.structured_content
            assert data["status"] == "ok", data
            assert data["apk_sha256"] == digest
            calls.append({"tool": tool, "seconds": round(time.monotonic() - started, 4)})
            return data

        async def pages(tool, limit):
            offset, rows, first = 0, [], None
            while True:
                result = await query(tool, offset=offset, limit=limit)
                if first is None:
                    first = result
                assert result["total"] == first["total"]
                rows.extend(result["items"])
                offset = result["next_offset"]
                if offset is None:
                    break
                assert offset == len(rows)
            assert len(rows) == first["total"]
            return first, rows

        _, entries = await pages("asc_list_apk_entries", 500)
        actual = {
            r["path"]: (r["size_bytes"], r["compressed_size_bytes"], r["crc32"]) for r in entries
        }
        assert actual == expected and len(entries) == len(expected)
        summary, components = await pages("asc_manifest_summary", 10)
        report = {
            "apk_name": apk.name,
            "apk_sha256": digest,
            "entries": len(entries),
            "entry_kinds": dict(Counter(r["kind"] for r in entries)),
            "package_name": summary["package_name"],
            "components": len(components),
            "component_kinds": dict(Counter(r["kind"] for r in components)),
            "manifest_decoding_warnings": summary["decoding_warnings"],
            "zip_metadata_matches": True,
            "aapt2_component_matches": None,
        }
        if args.aapt2:
            _, oracle = aapt_tree(args.aapt2, apk, "AndroidManifest.xml")
            actual = [
                (
                    r["kind"],
                    r["declarations"].get("{http://schemas.android.com/apk/res/android}name"),
                )
                for r in components
            ]
            assert actual == oracle, (
                "Component declarations differ from aapt2",
                len(actual),
                len(oracle),
                [(i, a, b) for i, (a, b) in enumerate(zip(actual, oracle, strict=False)) if a != b][
                    :3
                ],
            )
            report["aapt2_component_matches"] = True
        if resources:
            name = resources[0]
            content = await query("asc_read_apk_entry", entry_path=name, max_bytes=131072)
            assert content["decoded"] and content["content_complete"] and content["crc_verified"]
            root = ET.fromstring(content["content"])
            tags = [e.tag.rsplit("}", 1)[-1] for e in root.iter()]
            if args.aapt2:
                oracle, _ = aapt_tree(args.aapt2, apk, name)
                assert tags == oracle, "Resource element structure differs from aapt2"
            report["resource"] = {
                "entry_path": name,
                "root": root.tag,
                "elements": len(tags),
                "xml_format": content["xml_format"],
                "decoding_warnings": content["decoding_warnings"],
                "aapt2_element_matches": True if args.aapt2 else None,
            }
    assert hashlib.sha256(apk.read_bytes()).hexdigest() == digest
    report.update(calls=calls, input_unchanged=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "calls"}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk", type=Path)
    parser.add_argument("--aapt2", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))


if __name__ == "__main__":
    main()
