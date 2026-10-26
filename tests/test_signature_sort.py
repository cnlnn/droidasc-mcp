"""Ordering equivalence must not cache inventories or weaken freshness checks."""

import os
from dataclasses import replace
from pathlib import Path, PosixPath, PurePosixPath, PureWindowsPath

import pytest

from droidasc_mcp import memory_cache


@pytest.mark.parametrize("names", [[], ["a"], ["z", "A", "a", "a.b", "é", "中", ".x"]])
def test_sibling_order_matches_path_order(tmp_path, names):
    paths = [tmp_path / name for name in names]
    assert memory_cache._sorted_siblings(iter(paths)) == sorted(paths)


def test_different_parents_keep_full_path_order(tmp_path):
    paths = [tmp_path / "a" / "z", tmp_path / "z" / "a"]
    assert memory_cache._sorted_siblings(paths) == sorted(paths)


def test_windows_casefold_order_preserved():
    paths = [PureWindowsPath("C:/lib/a"), PureWindowsPath("C:/lib/B")]
    assert memory_cache._sorted_siblings(paths) == sorted(paths)


def test_root_and_current_directory_keep_full_path_order():
    path_type = PosixPath if os.name == "posix" else PurePosixPath
    paths = [path_type("."), path_type("/")]
    assert memory_cache._sorted_siblings(paths) == sorted(paths)


def test_subclass_comparison_is_not_replaced():
    class ReversePath(type(Path())):
        def __lt__(self, other):
            return str(self) > str(other)

    paths = [ReversePath("/lib/a"), ReversePath("/lib/z")]
    assert memory_cache._sorted_siblings(paths) == sorted(paths)


@pytest.mark.parametrize("kind", ["source", "jar", "java", "index"])
def test_signature_rechecks_every_identity(settings, tmp_path, monkeypatch, kind):
    source = tmp_path / "source"
    source.mkdir()
    home = tmp_path / "engine"
    (home / "lib").mkdir(parents=True)
    targets = {
        "source": source / "module.py",
        "jar": home / "lib" / "engine.jar",
        "java": tmp_path / "java",
        "index": tmp_path / "calls.sqlite",
    }
    for target in targets.values():
        target.write_bytes(b"old")
    monkeypatch.setattr(memory_cache, "__file__", str(source / "memory_cache.py"))
    monkeypatch.setattr(memory_cache.shutil, "which", lambda _: str(targets["java"]))
    configured = replace(settings, jadx_home=home)
    before = memory_cache.signature(configured, tmp_path)
    assert before is not None
    replacement = targets[kind].with_suffix(".replacement")
    replacement.write_bytes(b"new implementation")
    replacement.replace(targets[kind])
    assert memory_cache.signature(configured, tmp_path) != before


@pytest.mark.parametrize("kind", ["source", "jar"])
def test_signature_reenumerates_additions_and_removals(settings, tmp_path, monkeypatch, kind):
    source = tmp_path / "source"
    source.mkdir()
    home = tmp_path / "engine"
    (home / "lib").mkdir(parents=True)
    monkeypatch.setattr(memory_cache, "__file__", str(source / "memory_cache.py"))
    monkeypatch.setattr(memory_cache.shutil, "which", lambda _: None)
    configured = replace(settings, jadx_home=home)
    before = memory_cache.signature(configured, tmp_path)
    target = source / "new.py" if kind == "source" else home / "lib" / "new.jar"
    target.write_bytes(b"new")
    assert memory_cache.signature(configured, tmp_path) != before
    target.unlink()
    assert memory_cache.signature(configured, tmp_path) == before


def test_stat_failure_still_disables_cache(settings, tmp_path, monkeypatch):
    monkeypatch.setattr(memory_cache.shutil, "which", lambda _: str(tmp_path / "missing-java"))
    assert memory_cache.signature(settings, tmp_path) is None
