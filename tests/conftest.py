from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

from droidasc_mcp.config import Settings


def pytest_sessionstart(session):
    if os.getenv("ASC_TEST_EXPECT_FIXTURE") == "1":
        apk = os.getenv("ASC_TEST_APK")
        if not apk or not Path(apk).is_file():
            raise pytest.UsageError("Fixture acceptance requires an existing ASC_TEST_APK")


def pytest_sessionfinish(session, exitstatus):
    if os.getenv("ASC_TEST_EXPECT_FIXTURE") == "1":
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        if reporter and reporter.stats.get("skipped"):
            session.exitstatus = pytest.ExitCode.TESTS_FAILED


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
