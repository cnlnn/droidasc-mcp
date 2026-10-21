from dataclasses import replace
from pathlib import Path

import pytest

from droidasc_mcp.runner import DroidAscError
from droidasc_mcp.rust_backend import RustAscRunner
from droidasc_mcp.service import DroidAscService


def test_rust_cli_translation_is_positional(settings, tmp_path):
    binary = tmp_path / "rust_ASC binary"
    binary.touch()
    runner = RustAscRunner(replace(settings, rust_asc_executable=binary))
    args = ["findrefs", "--threads", "2", "input.apk", "string", "--", "--threads"]
    assert runner._command(args, None)[3:] == [str(binary), *args[:1], "--thread", *args[2:]]
    assert runner._command(["file"], "droidasc_mcp.info_worker")[-2:] == [
        "droidasc_mcp.info_worker",
        "file",
    ]
    with pytest.raises(ValueError, match="not supported"):
        runner._command(["export", "input.apk"], None)


def test_rust_is_explicit_and_shares_limits(settings, apk_file):
    service = DroidAscService(settings)
    assert service.rust_runner._slots is service.runner._slots
    assert service.ping()["rust_backend"]["default"] is False
    with pytest.raises(ValueError, match="not configured"):
        service.get_manifest(str(apk_file), offset=0, limit=1, backend="rust_asc")
    with pytest.raises(ValueError, match="backend must"):
        service.get_manifest(str(apk_file), offset=0, limit=1, backend="auto")
    with pytest.raises(DroidAscError, match="Configure"):
        service.rust_runner._command(["listclass", str(apk_file)], None)


def test_rust_never_silently_falls_back(settings, apk_file):
    service = DroidAscService(replace(settings, rust_asc_executable=Path("missing")))
    with pytest.raises(ValueError, match="hierarchy"):
        service.find_refs(
            str(apk_file),
            kind="extends",
            value="java.lang.Object",
            class_name=None,
            fuzzy_class=False,
            threads=1,
            offset=0,
            limit=1,
            backend="rust_asc",
        )
    with pytest.raises(DroidAscError, match="Configure"):
        service.get_manifest(str(apk_file), offset=0, limit=1, backend="rust_asc")
