"""DEX input policy, bounded import, diagnostics and cleanup regressions."""

import hashlib
import json
import shutil
import struct
import zipfile
import zlib
from dataclasses import replace
from pathlib import Path

import anyio
import pytest
from mcp import Client

from droidasc_mcp.config import ApkPathError
from droidasc_mcp.dex_worker import BoundedText, DexInputError, PublicCliRunner, analyze, copy_dex
from droidasc_mcp.runner import DroidAscError, DroidAscRunner, Snapshot
from droidasc_mcp.server import build_server


def empty_dex():
    data = bytearray(112)
    data[:8] = b"dex\n035\0"
    struct.pack_into("<III", data, 32, len(data), 112, 0x12345678)
    data[12:32] = hashlib.sha1(data[32:]).digest()
    struct.pack_into("<I", data, 8, zlib.adler32(data[12:]))
    return data


def test_copy_preserves_exact_bytes_and_hash(tmp_path):
    path = tmp_path / "input.dex"
    data = empty_dex()
    path.write_bytes(data)
    with zipfile.ZipFile(tmp_path / "analysis.apk", "w") as out:
        result = copy_dex(path, out, "classes.dex", 1000)
    assert result["sha256"] == hashlib.sha256(data).hexdigest()
    assert result["path"] == str(path)
    with zipfile.ZipFile(tmp_path / "analysis.apk") as archive:
        assert archive.read("classes.dex") == data
        assert archive.namelist() == ["classes.dex"]
    assert path.read_bytes() == data


def test_preparation_stores_exact_dex_without_recompression(settings, tmp_path, monkeypatch):
    path = tmp_path / "input.dex"
    data = bytes(empty_dex())
    path.write_bytes(data)
    root = tmp_path / "prepared"
    root.mkdir()
    inspected = []

    def inspect(self, args):
        single = Path(args[-1])
        with zipfile.ZipFile(single) as archive:
            assert archive.getinfo("classes.dex").compress_type == zipfile.ZIP_STORED
            assert archive.read("classes.dex") == data
        inspected.append(single)
        return Snapshot(0, (), 0)

    monkeypatch.setattr(PublicCliRunner, "_get_snapshot", inspect)
    result = analyze(
        {
            "allowed_roots": [str(tmp_path)],
            "max_input_bytes": settings.max_apk_bytes,
            "max_output_bytes": settings.max_output_bytes,
            "max_page_size": settings.max_page_size,
            "query": {"offset": 0, "limit": 10},
            "paths": [str(path)],
            "prepare": True,
        },
        root,
    )
    assert result["status"] == "ok", result
    assert result["sources"][0]["sha256"] == hashlib.sha256(data).hexdigest()
    with zipfile.ZipFile(root / "analysis.apk") as archive:
        assert archive.getinfo("classes.dex").compress_type == zipfile.ZIP_STORED
        assert archive.read("classes.dex") == data
    assert inspected and all(not p.exists() for p in inspected)
    assert path.read_bytes() == data


@pytest.mark.parametrize(
    ("offset", "replacement", "code"),
    [
        (0, b"bad!", "invalid_magic"),
        (4, b"041", "unsupported_dex"),
        (32, struct.pack("<I", 200), "size_mismatch"),
        (36, struct.pack("<I", 120), "unsupported_dex"),
        (40, b"\x12\x34\x56\x78", "unsupported_dex"),
        (56, struct.pack("<II", 2, 112), "invalid_table"),
        (56, struct.pack("<II", 0, 112), "invalid_table"),
        (8, b"\x00\x00\x00\x00", "integrity_mismatch"),
        (12, b"x", "integrity_mismatch"),
    ],
)
def test_invalid_dex_is_not_repaired(tmp_path, offset, replacement, code):
    data = empty_dex()
    data[offset : offset + len(replacement)] = replacement
    path = tmp_path / "input.dex"
    path.write_bytes(data)
    with (
        zipfile.ZipFile(tmp_path / "analysis.apk", "w") as archive,
        pytest.raises(DexInputError) as caught,
    ):
        copy_dex(path, archive, "classes.dex", 1000)
    assert caught.value.code == code
    assert path.read_bytes() == data


@pytest.mark.parametrize(
    ("data", "budget", "code"),
    [(b"dex\n035\0", 1000, "truncated_dex"), (empty_dex(), 100, "input_limit")],
)
def test_short_or_oversize_input(tmp_path, data, budget, code):
    path = tmp_path / "input.dex"
    path.write_bytes(data)
    with (
        zipfile.ZipFile(tmp_path / "analysis.apk", "w") as archive,
        pytest.raises(DexInputError) as caught,
    ):
        copy_dex(path, archive, "classes.dex", budget)
    assert caught.value.code == code


def test_dex_path_limits(settings, tmp_path):
    path = tmp_path / "input.dex"
    path.write_bytes(empty_dex())
    assert settings.validate_dex_paths([str(path)]) == [path]
    for paths, message in (
        ([], "between"),
        ([str(path)] * 65, "between"),
        ([str(path)] * 2, "Repeated"),
        ([str(path.with_suffix(".apk"))], "Only .dex"),
        ([str(tmp_path / "missing.dex")], "does not exist"),
    ):
        with pytest.raises(ApkPathError, match=message):
            settings.validate_dex_paths(paths)
    with pytest.raises(ApkPathError, match="Combined DEX"):
        replace(settings, max_apk_bytes=100).validate_dex_paths([str(path)])
    with pytest.raises(ApkPathError, match="outside allowed roots"):
        replace(settings, allowed_roots=(tmp_path / "nested",)).validate_dex_paths([str(path)])


def test_dex_symlink_escape(settings, tmp_path):
    outside = tmp_path / "outside.dex"
    outside.write_bytes(empty_dex())
    root = tmp_path / "allowed"
    root.mkdir()
    link = root / "linked.dex"
    try:
        link.symlink_to(outside)
    except OSError:
        # Windows without symlink privilege still exercises resolved-path policy above.
        with pytest.raises(ApkPathError, match="outside allowed roots"):
            replace(settings, allowed_roots=(root,)).validate_dex_paths([str(outside)])
    else:
        with pytest.raises(ApkPathError, match="outside allowed roots"):
            replace(settings, allowed_roots=(root,)).validate_dex_paths([str(link)])


def test_cli_capture_is_byte_bounded():
    with BoundedText(4) as output:
        output.write("ab")
        with pytest.raises(DroidAscError, match="stream limit"):
            output.write("cde")


@pytest.mark.parametrize("outcome", ["success", "failure", "cancelled"])
def test_temporary_inputs_cleaned_on_every_exit(settings, tmp_path, monkeypatch, outcome):
    runner = DroidAscRunner(settings)
    roots = []

    def execute(args, **kwargs):
        root = Path(args[0]).parent
        roots.append(root)
        assert json.loads(Path(args[0]).read_text())["paths"] == [str(tmp_path / "input.dex")]
        (root / "analysis.apk").write_bytes(b"temporary")
        if outcome == "failure":
            raise DroidAscError("timed out")
        if outcome == "cancelled":
            raise KeyboardInterrupt
        return b'{"status":"ok"}'

    monkeypatch.setattr(runner, "_execute", execute)
    if outcome == "success":
        assert runner.analyze_dex([tmp_path / "input.dex"], {})["status"] == "ok"
    else:
        with pytest.raises(KeyboardInterrupt if outcome == "cancelled" else DroidAscError):
            runner.analyze_dex([tmp_path / "input.dex"], {})
    assert roots and all(not root.exists() for root in roots)


@pytest.mark.anyio
@pytest.mark.parametrize("cancel", [False, True])
async def test_dex_storage_cleaned_after_live_worker_termination(settings, monkeypatch, cancel):
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).parent))
    runner = DroidAscRunner(replace(settings, timeout_seconds=1))
    execute = runner._execute
    roots = []

    def slow_worker(args, **kwargs):
        root = Path(args[0]).parent
        roots.append(root)
        return execute(["tree", str(root)], module_name="process_fixture")

    monkeypatch.setattr(runner, "_execute", slow_worker)
    if cancel:
        with anyio.move_on_after(0.4) as scope:
            await anyio.to_thread.run_sync(runner.analyze_dex, [], {})
        assert scope.cancel_called
    else:
        with pytest.raises(DroidAscError, match="timed out"):
            await anyio.to_thread.run_sync(runner.analyze_dex, [], {})
    assert roots and all(not root.exists() for root in roots)


@pytest.mark.anyio
async def test_real_dex_duplicate_and_error_recovery(settings, real_dex_files, tmp_path):
    duplicate = tmp_path / "copy.dex"
    duplicate.write_bytes(real_dex_files[0].read_bytes())
    bad = tmp_path / "bad.dex"
    bad.write_bytes(b"dex\n035\0")
    async with Client(build_server(replace(settings, timeout_seconds=60))) as client:
        for paths, code in (
            ([str(real_dex_files[0]), str(duplicate)], "duplicate_class"),
            ([str(bad)], "truncated_dex"),
        ):
            result = await client.call_tool("asc_analyze_dex", {"dex_paths": paths})
            assert not result.is_error
            assert result.structured_content["status"] == "error"
            assert result.structured_content["code"] == code
        result = await client.call_tool("asc_analyze_dex", {"dex_paths": [str(real_dex_files[0])]})
        assert result.structured_content["status"] == "ok"
        assert result.structured_content["sources"][0]["class_count"] > 0


@pytest.mark.anyio
@pytest.mark.parametrize("opcode", [0x3E, 0x73])
@pytest.mark.parametrize(
    "operation,identity",
    [
        ("get_method_calls", {"method_descriptor": "Lfixture/Caller;->run()V"}),
        ("find_field_refs", {"field_descriptor": "Lfixture/Target;->value:I"}),
        ("build_xref_index", {}),
        ("find_type_refs", {"type_descriptor": "Lfixture/Target;"}),
    ],
)
async def test_unknown_instruction_never_reports_complete_scan(
    settings, tmp_path, smali_dex_files, opcode, operation, identity
):
    import os

    path = Path(shutil.copy(smali_dex_files[0], tmp_path))
    data = bytearray(path.read_bytes())
    # The independent Smali oracle starts run() with const/4 v0,1 then invoke-static.
    marker = b"\x12\x10\x71\x10"
    assert data.count(marker) == 1
    # Unknown 0x3e and optimized-only 0x73 must not become a complete standard-DEX scan.
    data[data.index(marker) + 2] = opcode
    data[12:32] = hashlib.sha1(data[32:]).digest()
    struct.pack_into("<I", data, 8, zlib.adler32(data[12:]))
    path.write_bytes(data)
    configured = replace(
        settings,
        timeout_seconds=60,
        jadx_home=Path(os.environ["DROIDASC_MCP_JADX_HOME"]),
        java_executable=os.getenv("DROIDASC_MCP_JAVA"),
    )
    async with Client(build_server(configured)) as client:
        reply = await client.call_tool(
            "asc_analyze_dex",
            {
                "dex_paths": [str(path)],
                "operation": operation,
                **identity,
                "limit": 1,
            },
        )
        assert not reply.is_error, reply
        result = reply.structured_content
        assert result["status"] == "error" and result["code"] == "engine_error", result
        assert "items" not in result and "instruction_scan_complete" not in result
        assert path.read_bytes() == data
        shutil.copy(smali_dex_files[0], path)
        recovered = await client.call_tool(
            "asc_analyze_dex",
            {
                "dex_paths": [str(path)],
                "operation": operation,
                **identity,
            },
        )
        assert recovered.structured_content["instruction_scan_complete"] is True
