"""Wheel ABI floors follow the public buffer API's actual availability."""

import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("minor", [10, 11, 12, 13])
def test_native_buffer_build_targets_supported_python_abi(monkeypatch, minor):
    captured = {}

    def setup(**kwargs):
        captured.update(kwargs)

    def extension(name, sources, **kwargs):
        return SimpleNamespace(name=name, sources=sources, **kwargs)

    monkeypatch.setitem(
        sys.modules, "setuptools", SimpleNamespace(setup=setup, Extension=extension)
    )
    monkeypatch.setattr(sys, "version_info", (3, minor, 0, "final", 0))
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "setup.py"))
    (native,) = captured["ext_modules"]
    assert native.name == "droidasc_mcp._dexscan"
    assert native.py_limited_api is (minor >= 11)
    assert native.define_macros == ([("Py_LIMITED_API", "0x030B0000")] if minor >= 11 else [])
    assert captured["options"] == (
        {"bdist_wheel": {"py_limited_api": "cp311"}} if minor >= 11 else {}
    )
