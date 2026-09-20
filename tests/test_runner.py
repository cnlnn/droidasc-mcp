from __future__ import annotations

import os
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
            if "longline" in args:
                print("x" * 100000)
                raise SystemExit(0)
            if "stderr-flood" in args:
                sys.stderr.write("x" * 100000)
                raise SystemExit(0)
            if any(item.endswith("sleep.apk") for item in args):
                time.sleep(10)
            if any(item.endswith("failure.apk") for item in args):
                print("synthetic failure", file=sys.stderr)
                raise SystemExit(3)
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
            print(text, end="")
            """
        ),
        encoding="utf-8",
    )
    old_path = os.environ.get("PYTHONPATH", "")
    value = str(package_root) if not old_path else f"{package_root}{os.pathsep}{old_path}"
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


def test_cache_reuses_snapshot(settings, apk_file, fake_droidasc, monkeypatch):
    subject = runner(settings, fake_droidasc)
    first = subject.get_manifest(apk_file, offset=0, limit=1)

    def fail(*args, **kwargs):
        raise AssertionError("should reuse snapshot")

    monkeypatch.setattr(subject, "_execute", fail)
    second = subject.get_manifest(apk_file, offset=1, limit=1)
    assert first.total == second.total == 3
    assert first.items != second.items


def test_long_line_is_rejected(settings, apk_file, fake_droidasc):
    with pytest.raises(DroidAscError, match="response budget"):
        runner(settings, fake_droidasc).list_classes(
            apk_file, prefix="longline", threads=1, offset=0, limit=1
        )


def test_stderr_budget(settings, apk_file, fake_droidasc):
    with pytest.raises(DroidAscError, match="output exceeds"):
        runner(settings, fake_droidasc).list_classes(
            apk_file, prefix="stderr-flood", threads=1, offset=0, limit=1
        )


def test_reference_sorting(settings, apk_file, monkeypatch):
    subject = runner(settings, "unused")
    monkeypatch.setattr(subject, "_execute", lambda args: b"z\na\nm\n")
    assert subject._run_paged(["findrefs", str(apk_file)], offset=0, limit=2).items == ["a", "m"]


def test_cleanup_signals_group_after_leader_exit(monkeypatch):
    import os
    import signal
    from types import SimpleNamespace

    from droidasc_mcp.runner import _terminate_process_tree

    if os.name == "nt":
        pytest.skip("POSIX process groups")
    signals = []
    monkeypatch.setattr(os, "killpg", lambda pid, sig: signals.append((pid, sig)))
    _terminate_process_tree(SimpleNamespace(pid=12345, poll=lambda: 0))
    assert signals == [(12345, signal.SIGKILL)]


def test_cache_invalidated_on_file_change(settings, apk_file, monkeypatch):
    subject = runner(settings, "unused")
    calls = []

    def execute(args):
        calls.append(args)
        return b"a\n"

    monkeypatch.setattr(subject, "_execute", execute)
    subject.get_manifest(apk_file, offset=0, limit=1)
    with apk_file.open("ab") as handle:
        handle.write(b"changed")
    subject.get_manifest(apk_file, offset=0, limit=1)
    assert len(calls) == 2
