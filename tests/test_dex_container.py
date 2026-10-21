"""Real DEX 041 logical import, provenance, xrefs, and malformed-container rejection."""

import hashlib
import struct
from dataclasses import replace
from pathlib import Path

import pytest
from dex041_fixture import dex041_container

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService


@pytest.mark.parametrize("names,shared", [(("A",), False), (("A", "B"), False), (("A", "B"), True)])
def test_dex041_import_and_exact_instruction_views(tmp_path, names, shared):
    path = tmp_path / "container.dex"
    data = dex041_container(names, shared_strings=shared)
    path.write_bytes(data)
    service = DroidAscService(
        replace(Settings.from_env(), allowed_roots=(tmp_path,), timeout_seconds=90)
    )
    try:
        opened = service.open_dex_session([str(path)])
        assert opened["status"] == "ok", opened
        assert opened["class_count"] == len(names)
        retained = service.sessions.entries[opened["session_id"]]
        assert not list(Path(retained.storage.name).glob("dex-container-*"))
        assert len(opened["sources"]) == len(names)
        assert all(
            row["container_sha256"] == hashlib.sha256(data).hexdigest() for row in opened["sources"]
        )
        assert opened["sources"][0]["logical_header_offset"] == 0
        if len(names) == 2:
            assert opened["sources"][1]["logical_header_offset"] > 120
        path.unlink()
        for name in names:
            result = service.query_dex_session(
                opened["session_id"],
                operation="get_string_constants",
                class_name=f"oracle.{name}",
                offset=0,
                limit=10,
            )
            assert result["status"] == "ok", result
            assert [row["value"] for row in result["items"]] == [f"value-{name}"]
            source = service.query_dex_session(
                opened["session_id"],
                operation="get_class_source",
                class_name=f"oracle.{name}",
                offset=0,
                limit=100,
                threads=1,
            )
            assert source["status"] == "ok", source
    finally:
        service.close()


@pytest.mark.parametrize(
    "field,value", [(112, 1), (116, 120), (32, 119), (36, 112), (60, 0xFFFFFFFF), (8, 0)]
)
def test_dex041_malformed_containers_are_not_repaired(tmp_path, field, value):
    path = tmp_path / "invalid.dex"
    data = bytearray(dex041_container())
    struct.pack_into("<I", data, field, value)
    path.write_bytes(data)
    service = DroidAscService(
        replace(Settings.from_env(), allowed_roots=(tmp_path,), timeout_seconds=90)
    )
    try:
        result = service.open_dex_session([str(path)])
        assert result["status"] == "error", result
        assert result["code"] in {"invalid_dex_container", "invalid_table", "integrity_mismatch"}
        assert not service.sessions.entries
        assert path.read_bytes() == data
    finally:
        service.close()
