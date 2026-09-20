from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.runner import DroidAscError, DroidAscRunner


@pytest.fixture
def fake_droidasc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    package_root = tmp_path / "fake-package"
    package = package_root / "fake_droidasc"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "__main__.py").write_text(
        textwrap.dedent(
            r"""
            import pathlib
            import sys
            import time

            args = sys.argv[1:]
            if any(item.endswith("sleep.apk") for item in args):
                time.sleep(10)
            if any(item.endswith("failure.apk") for item in args):
                print("synthetic failure", file=sys.stderr)
                raise SystemExit(3)
            output = pathlib.Path(args[args.index("-o") + 1])
            command = args[0]
            if command == "getmanifest":
                text = "<manifest>\n  <application />\n</manifest>\n"
            elif command == "listclass":
                text = "Lcom/example/One;\nLcom/example/Two;\nLcom/example/Three;\n"
            elif command == "getclass":
                text = "public class One {\n    void run() {}\n}\n"
            elif command == "findrefs":
                text = (
                    "classes.dex | Lcom/example/One;->run | matched=(token)\n"
                    "classes2.dex | Lcom/example/Two;->load | matched=(token)\n"
                )
            else:
                raise SystemExit(4)
            output.write_text(text, encoding="utf-8")
            """
        ),
        encoding="utf-8",
    )
    old_path = __import__("os").environ.get("PYTHONPATH", "")
    value = str(package_root) if not old_path else f"{package_root}:{old_path}"
    monkeypatch.setenv("PYTHONPATH", value)
    return "fake_droidasc"


def runner(settings: Settings, module_name: str) -> DroidAscRunner:
    return DroidAscRunner(settings, module_name=module_name)


def test_list_classes_is_paginated(settings: Settings, apk_file: Path, fake_droidasc: str):
    page = runner(settings, fake_droidasc).list_classes(
        apk_file,
        prefix="com.example",
        threads=4,
        offset=1,
        limit=1,
    )
    assert page.items == ["Lcom/example/Two;"]
    assert page.total == 3
    assert page.as_dict()["truncated"] is True


def test_manifest_and_source_preserve_bounded_lines(
    settings: Settings, apk_file: Path, fake_droidasc: str
):
    subject = runner(settings, fake_droidasc)
    manifest = subject.get_manifest(apk_file, offset=0, limit=2)
    source = subject.get_class_source(
        apk_file,
        class_name="Lcom/example/One;",
        threads=2,
        offset=1,
        limit=1,
    )
    assert manifest.items == ["<manifest>", "  <application />"]
    assert manifest.total == 3
    assert source.items == ["    void run() {}"]
    assert source.total == 3


def test_find_refs_returns_structured_hits(settings: Settings, apk_file: Path, fake_droidasc: str):
    result = runner(settings, fake_droidasc).find_refs(
        apk_file,
        kind="string",
        value="token",
        class_name=None,
        fuzzy_class=False,
        threads=2,
        offset=0,
        limit=10,
    )
    assert result["total"] == 2
    assert result["items"][0] == {
        "dex": "classes.dex",
        "method": "Lcom/example/One;->run",
        "matched": "token",
        "raw": "classes.dex | Lcom/example/One;->run | matched=(token)",
    }


def test_find_refs_validates_query(settings: Settings, apk_file: Path, fake_droidasc: str):
    with pytest.raises(ValueError, match="value is required"):
        runner(settings, fake_droidasc).find_refs(
            apk_file,
            kind="string",
            value=None,
            class_name=None,
            fuzzy_class=False,
            threads=2,
            offset=0,
            limit=10,
        )


def test_nonzero_exit_is_reported(settings: Settings, tmp_path: Path, fake_droidasc: str):
    apk = tmp_path / "failure.apk"
    apk.write_bytes(b"apk")
    with pytest.raises(DroidAscError, match="synthetic failure"):
        runner(settings, fake_droidasc).get_manifest(apk, offset=0, limit=10)


def test_page_size_is_capped(settings: Settings, apk_file: Path, fake_droidasc: str):
    page = runner(settings, fake_droidasc).list_classes(
        apk_file,
        prefix=None,
        threads=99,
        offset=0,
        limit=1000,
    )
    assert page.limit == settings.max_page_size


def test_output_size_limit_is_enforced(settings: Settings, apk_file: Path, fake_droidasc: str):
    restricted = Settings(
        allowed_roots=settings.allowed_roots,
        timeout_seconds=settings.timeout_seconds,
        max_apk_bytes=settings.max_apk_bytes,
        max_output_bytes=10,
        max_page_size=settings.max_page_size,
        max_parallel=settings.max_parallel,
    )
    with pytest.raises(DroidAscError, match="output exceeds"):
        runner(restricted, fake_droidasc).list_classes(
            apk_file,
            prefix=None,
            threads=2,
            offset=0,
            limit=10,
        )


def test_timeout_terminates_worker(settings: Settings, tmp_path: Path, fake_droidasc: str):
    apk = tmp_path / "sleep.apk"
    apk.write_bytes(b"apk")
    restricted = Settings(
        allowed_roots=settings.allowed_roots,
        timeout_seconds=1,
        max_apk_bytes=settings.max_apk_bytes,
        max_output_bytes=settings.max_output_bytes,
        max_page_size=settings.max_page_size,
        max_parallel=settings.max_parallel,
    )
    with pytest.raises(DroidAscError, match="timed out after 1 seconds"):
        runner(restricted, fake_droidasc).get_manifest(apk, offset=0, limit=10)
