"""Original-file inventory and bounded content parity for standalone DEX inputs."""

import base64
import hashlib
from dataclasses import replace

import pytest

from droidasc_mcp import archive_worker as worker
from droidasc_mcp.config import ApkPathError
from droidasc_mcp.service import DroidAscService


def analyze(path, **query):
    return worker.analyze(
        {
            "apk_path": str(path),
            "allowed_roots": [str(path.parent)],
            "max_input_bytes": 16 * 1024**2,
            "max_page_size": 100,
            "query": query,
        }
    )


@pytest.mark.parametrize("name", ["classes.dex", "arbitrary + name.DEX", "logical-041.dex"])
def test_original_dex_inventory_and_complete_byte_pages(tmp_path, name):
    path = tmp_path / name
    data = b"dex\n041\0" + bytes(range(256)) * 513
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    inventory = analyze(path, operation="list_entries", limit=1)
    assert inventory["status"] == "ok", inventory
    assert inventory["artifact_sha256"] == digest and inventory["artifact_size_bytes"] == len(data)
    assert inventory["items"] == [
        {
            "path": name,
            "kind": "dex",
            "size_bytes": len(data),
            "compressed_size_bytes": len(data),
            "encrypted": False,
            "abi": None,
        }
    ]
    assert inventory["next_offset"] is None and inventory["total"] == 1
    chunks, offset = [], 0
    while True:
        page = analyze(
            path, operation="read_entry", entry_path=name, max_bytes=65537, byte_offset=offset
        )
        assert page["status"] in {"ok", "partial"}, page
        assert page["artifact_sha256"] == digest and page["format_validation"] == "not_performed"
        assert "crc_verified" not in page and "crc32" not in page
        assert page["encoding"] == "base64"
        decoded = base64.b64decode(page["content"], validate=True)
        assert page["returned_bytes"] == len(decoded) <= 65537
        chunks.append(decoded)
        if page["content_complete"]:
            assert page["next_byte_offset"] is None
            break
        assert page["next_byte_offset"] == offset + len(decoded)
        offset = page["next_byte_offset"]
    assert b"".join(chunks) == data and path.read_bytes() == data
    eof = analyze(path, operation="read_entry", entry_path=name, byte_offset=len(data) + 1)
    assert eof["content"] == "" and eof["content_complete"] and not eof["truncated"]


@pytest.mark.parametrize(
    "selection,expected",
    [
        ({}, 1),
        ({"kind": "dex"}, 1),
        ({"kind": "native"}, 0),
        ({"kind": "asset"}, 0),
        ({"prefix": "stand"}, 1),
        ({"prefix": "other"}, 0),
        ({"offset": 1}, 1),
    ],
)
def test_raw_inventory_filters_and_pagination(tmp_path, selection, expected):
    path = tmp_path / "standalone.dex"
    path.write_bytes(b"not a validated code input")
    result = analyze(path, operation="list_entries", **selection)
    assert result["status"] == "ok", result
    assert result["total"] == expected
    assert len(result["items"]) == (0 if selection.get("offset") else expected)
    assert result["format_validation"] == "not_performed"


@pytest.mark.parametrize(
    "query",
    [
        {"operation": "list_entries", "offset": -1},
        {"operation": "list_entries", "offset": True},
        {"operation": "list_entries", "limit": 101},
        {"operation": "list_entries", "kind": "unknown"},
        {"operation": "list_entries", "prefix": 1},
        {"operation": "read_entry", "max_bytes": 131073},
        {"operation": "read_entry", "max_bytes": True},
        {"operation": "read_entry", "byte_offset": -1},
        {"operation": "read_entry", "byte_offset": True},
        {"operation": "read_entry", "decode_xml": "true"},
        {"operation": "read_entry", "entry_path": "../secret"},
        {"operation": "read_entry", "entry_path": "/etc/passwd"},
    ],
)
def test_raw_invalid_queries_fail_closed(tmp_path, query):
    path = tmp_path / "sample.dex"
    path.write_bytes(b"dex\n035\0")
    result = analyze(path, **{"entry_path": path.name, **query})
    assert result["status"] == "error" and result["code"] in {"invalid_query", "unsafe_entry"}
    assert "content" not in result


@pytest.mark.parametrize(
    "operation", ["manifest_summary", "signing_inventory", "artifact_inventory"]
)
def test_raw_entries_do_not_claim_archive_or_analysis_capabilities(tmp_path, operation):
    path = tmp_path / "sample.dex"
    path.write_bytes(b"malformed DEX is still inventoryable")
    result = analyze(path, operation=operation)
    assert result["status"] == "not_applicable" and result["code"] == "unsupported_capability"
    assert "content" not in result
    missing = analyze(path, operation="read_entry", entry_path="different.dex")
    assert missing["code"] == "entry_not_found"


def test_raw_content_mutation_discards_bytes(tmp_path, monkeypatch):
    path = tmp_path / "sample.dex"
    original = b"dex\n035\0" + bytes(range(256)) * 8
    path.write_bytes(original)
    digest, calls = worker._digest, []

    def changed(handle):
        calls.append(1)
        if len(calls) == 2:
            path.write_bytes(original[:-1] + b"changed")
        return digest(handle)

    monkeypatch.setattr(worker, "_digest", changed)
    result = analyze(path, operation="read_entry", entry_path=path.name)
    assert result["status"] == "error" and result["code"] == "input_changed"
    assert "content" not in result


def test_host_raw_entry_policy_and_supervised_worker(settings, tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    path = root / "input.DEX"
    path.write_bytes(b"dex\n035\0\xff")
    outside = tmp_path / "outside.dex"
    outside.write_bytes(b"secret")
    service = DroidAscService(replace(settings, allowed_roots=(root,)))
    try:
        result = service.query_archive(str(path), operation="read_entry", entry_path=path.name)
        assert result["status"] == "ok", result
        assert base64.b64decode(result["content"]) == path.read_bytes()
        for operation in ("list_entries", "read_entry"):
            with pytest.raises(ApkPathError, match="outside allowed roots"):
                service.query_archive(str(outside), operation=operation, entry_path=outside.name)
        with pytest.raises(ApkPathError):
            service.inspect_artifact(str(path))
    finally:
        service.close()
