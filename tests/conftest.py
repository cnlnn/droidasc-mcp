from __future__ import annotations

import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from droidasc_mcp.config import Settings


def pytest_sessionstart(session):
    if os.getenv("ASC_TEST_EXPECT_FIXTURE") == "1":
        apk = os.getenv("ASC_TEST_APK")
        if not apk or not Path(apk).is_file():
            raise pytest.UsageError("Fixture acceptance requires an existing ASC_TEST_APK")
        for name in ("ASC_TEST_COMPLEX_APK", "ASC_TEST_COMPLEX_MAPPING"):
            if not os.getenv(name) or not Path(os.environ[name]).is_file():
                raise pytest.UsageError(f"Fixture acceptance requires an existing {name}")


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


@pytest.fixture
def real_dex_files(tmp_path):
    apk = os.getenv("ASC_TEST_APK")
    if not apk or os.getenv("ASC_TEST_EXPECT_FIXTURE") != "1":
        pytest.skip("Set ASC_TEST_APK and ASC_TEST_EXPECT_FIXTURE=1 for public DEX acceptance")
    root = tmp_path / "DEX input with spaces"
    root.mkdir()
    paths = []
    with zipfile.ZipFile(apk) as archive:
        for name in ("classes.dex", "classes2.dex"):
            path = root / name
            path.write_bytes(archive.read(name))
            paths.append(path)
    return paths


def assemble_smali(tmp_path_factory, names):
    home = os.getenv("DROIDASC_MCP_JADX_HOME")
    java = os.getenv("DROIDASC_MCP_JAVA") or shutil.which("java")
    if not home or not java:
        pytest.skip("Configure JADX 1.5.5 and JDK 17 for instruction acceptance")
    root = tmp_path_factory.mktemp("instruction-oracle")
    jars = os.pathsep.join(str(p) for p in sorted((Path(home) / "lib").glob("*.jar")))
    paths = []
    for number, name in enumerate(names, 1):
        output = root / f"input{number}.dex"
        subprocess.run(
            [
                java,
                "-cp",
                jars,
                "com.android.tools.smali.smali.Main",
                "assemble",
                "--api",
                "28",
                str(Path(__file__).parent / "fixtures" / "xrefs" / name),
                "-o",
                str(output),
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
        assert output.is_file()
        paths.append(output)
    return paths


@pytest.fixture(scope="session")
def smali_dex_files(tmp_path_factory):
    return assemble_smali(tmp_path_factory, ("first", "second"))


@pytest.fixture(scope="session")
def string_reference_dex_files(tmp_path_factory):
    return assemble_smali(tmp_path_factory, ("string_refs", "structure"))


@pytest.fixture(scope="session")
def graph_dex_files(tmp_path_factory):
    return assemble_smali(tmp_path_factory, ("graph_first", "graph_second"))


@pytest.fixture(scope="session")
def review_dex_files(tmp_path_factory):
    return assemble_smali(tmp_path_factory, ("review_old", "review_new"))


@pytest.fixture(scope="session")
def memo_dex_files(tmp_path_factory):
    return assemble_smali(tmp_path_factory, ("memo_first", "memo_second"))


@pytest.fixture(scope="session")
def boundary_dex_file(tmp_path_factory):
    return assemble_smali(tmp_path_factory, ("boundary",))[0]


@pytest.fixture(scope="session")
def large_reference_dex_file(tmp_path_factory):
    root = tmp_path_factory.mktemp("reference-pages")
    owner = "Lfixture/" + "LongReferenceCaller" * 8 + ";"
    (root / "References.smali").write_text(
        f".class public {owner}\n.super Ljava/lang/Object;\n"
        ".method public static run()V\n.registers 0\n"
        + "invoke-static {}, Lfixture/Target;->touch()V\n" * 2000
        + "return-void\n.end method\n",
        encoding="utf-8",
    )
    return assemble_smali(tmp_path_factory, (root,))[0]


@pytest.fixture(scope="session")
def wide_operand_dex_file(tmp_path_factory):
    root = tmp_path_factory.mktemp("wide-operand-pages")
    value = "literal[a.*]" * 300
    target = "Lwide/" + "Target" * 500 + ";"
    (root / "Operands.smali").write_text(
        ".class public Lwide/Caller;\n.super Ljava/lang/Object;\n"
        ".method public static strings()V\n.registers 1\n"
        + f'const-string v0, "{value}"\n' * 100
        + "return-void\n.end method\n"
        + ".method public static types()V\n.registers 1\n"
        + f"const-class v0, {target}\n" * 100
        + "return-void\n.end method\n",
        encoding="utf-8",
    )
    return assemble_smali(tmp_path_factory, (root,))[0]
