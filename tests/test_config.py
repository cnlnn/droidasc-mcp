from __future__ import annotations

import os
from pathlib import Path

import pytest

from droidasc_mcp.config import ApkPathError, ConfigurationError, Settings


def test_settings_from_env_accepts_multiple_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    monkeypatch.setenv("DROIDASC_MCP_ALLOWED_ROOTS", f"{first}{os.pathsep}{second}")
    monkeypatch.setenv("DROIDASC_MCP_MAX_PAGE_SIZE", "77")
    monkeypatch.setenv("DROIDASC_MCP_MAX_WORKER_MEMORY_BYTES", "268435456")

    settings = Settings.from_env()

    assert settings.allowed_roots == (first.resolve(), second.resolve())
    assert settings.max_page_size == 77
    assert settings.max_worker_memory_bytes == 268435456


def test_settings_rejects_invalid_integer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DROIDASC_MCP_ALLOWED_ROOTS", str(tmp_path))
    monkeypatch.setenv("DROIDASC_MCP_TIMEOUT_SECONDS", "never")

    with pytest.raises(ConfigurationError, match="must be an integer"):
        Settings.from_env()


def test_validate_apk_accepts_file_inside_root(settings: Settings, apk_file: Path):
    assert settings.validate_apk(str(apk_file)) == apk_file.resolve()


def test_validate_apk_rejects_outside_root(settings: Settings, tmp_path: Path):
    outside = tmp_path.parent / "outside.apk"
    outside.write_bytes(b"apk")
    try:
        with pytest.raises(ApkPathError, match="outside allowed roots"):
            settings.validate_apk(str(outside))
    finally:
        outside.unlink(missing_ok=True)


def test_validate_apk_rejects_symlink_escape(settings: Settings, tmp_path: Path):
    outside = tmp_path.parent / "outside-symlink-target.apk"
    outside.write_bytes(b"apk")
    link = tmp_path / "linked.apk"
    link.symlink_to(outside)
    try:
        with pytest.raises(ApkPathError, match="outside allowed roots"):
            settings.validate_apk(str(link))
    finally:
        outside.unlink(missing_ok=True)


def test_validate_apk_rejects_non_apk(settings: Settings, tmp_path: Path):
    sample = tmp_path / "sample.zip"
    sample.write_bytes(b"zip")
    with pytest.raises(ApkPathError, match="Only .apk"):
        settings.validate_apk(str(sample))
