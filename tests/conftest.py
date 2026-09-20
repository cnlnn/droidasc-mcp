from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from droidasc_mcp.config import Settings


@pytest.fixture
def apk_file(tmp_path: Path) -> Path:
    apk = tmp_path / "fixture.apk"
    with zipfile.ZipFile(apk, "w") as archive:
        archive.writestr("AndroidManifest.xml", b"binary-placeholder")
        archive.writestr("classes.dex", b"dex\n035\0")
        archive.writestr("classes2.dex", b"dex\n035\0")
        archive.writestr("assets/classes3.dex", b"not-top-level")
    return apk


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        allowed_roots=(tmp_path.resolve(),),
        timeout_seconds=5,
        max_apk_bytes=16 * 1024 * 1024,
        max_output_bytes=1024 * 1024,
        max_page_size=100,
        max_parallel=2,
    )


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
