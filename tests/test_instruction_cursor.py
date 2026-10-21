"""Low-allocation cursor must agree with the pinned decoder, including payloads."""

import os
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService


def test_reference_order_is_descriptor_order_not_method_name_order(boundary_dex_file):
    settings = replace(Settings.from_env(), allowed_roots=(boundary_dex_file.parent,))
    service = DroidAscService(settings)
    try:
        key = service.open_dex_session([str(boundary_dex_file)])["session_id"]
        args = {
            "operation": "find_field_refs",
            "field_descriptor": "Lfixture/Ordering;->value:I",
            "offset": 0,
            "limit": 100,
        }
        result = service.query_dex_session(key, **args)
        assert result["status"] == "ok", result
        expected = [
            f"Lfixture/Ordering;->{name}" for name in ("a$()I", "a()I", "a(I)I", "a([I)I", "a0()I")
        ]
        assert [row["caller"] for row in result["items"]] == expected
        page = service.query_dex_session(key, **{**args, "offset": 1, "limit": 2})
        assert page["items"] == result["items"][1:3]
        assert page["total"] == 5
    finally:
        service.close()


def test_instruction_cursor_matches_library(
    tmp_path, smali_dex_files, boundary_dex_file, graph_dex_files
):
    home = Path(os.environ["DROIDASC_MCP_JADX_HOME"])
    java = Path(os.environ.get("DROIDASC_MCP_JAVA") or shutil.which("java"))
    javac = java.with_name("javac.exe" if os.name == "nt" else "javac")
    if not javac.is_file():
        pytest.fail("Cursor acceptance requires the configured JDK compiler")
    import droidasc_mcp

    source = Path(droidasc_mcp.__file__).with_name("MethodBridge.java")
    oracle = Path(__file__).parent / "fixtures/java/InstructionCursorOracle.java"
    jars = os.pathsep.join(map(str, sorted((home / "lib").glob("*.jar"))))
    subprocess.run(
        [str(javac), "-cp", jars, "-d", str(tmp_path), str(source), str(oracle)],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    result = subprocess.run(
        [
            str(java),
            "-cp",
            os.pathsep.join([str(tmp_path), jars]),
            "InstructionCursorOracle",
            *map(str, [*smali_dex_files, boundary_dex_file, *graph_dex_files]),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "checked=" in result.stdout
