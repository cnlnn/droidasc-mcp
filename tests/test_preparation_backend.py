"""Optional checksums never weaken integrity checks or require native packages."""

import zipfile
import zlib
from types import SimpleNamespace

import pytest

from droidasc_mcp import _preparation_backend as backend


@pytest.fixture
def select(monkeypatch):
    def run(candidate):
        monkeypatch.setattr(
            backend,
            "import_module",
            lambda name: SimpleNamespace(__version__="1.0.0") if name == "zlib_ng" else candidate,
        )
        return backend._select_backend()

    return run


def test_canonical_vectors_and_continuations():
    assert backend.crc32(b"123456789") == 0xCBF43926
    assert backend.adler32(b"123456789") == 0x091E01DE
    assert backend._compatible_checksum(zlib.crc32, "crc32")
    assert backend._compatible_checksum(zlib.adler32, "adler32")


def test_compatible_backend_selected(select):
    candidate = SimpleNamespace(crc32=zlib.crc32, adler32=zlib.adler32)
    selected = select(candidate)
    assert selected["crc32"][:2] == (candidate.crc32, "zlib-ng")
    assert selected["adler32"][:2] == (zlib.adler32, "stdlib")


def test_selection_does_not_patch_standard_library(select):
    original = (zlib.crc32, zlib.adler32, zipfile.crc32, zipfile.ZipFile.open)
    candidate = SimpleNamespace(
        crc32=lambda data, seed=0: zlib.crc32(data, seed),
        adler32=lambda data, seed=1: zlib.adler32(data, seed),
    )
    selected = select(candidate)
    assert selected["crc32"][:2] == (candidate.crc32, "zlib-ng")
    assert selected["adler32"][:2] == (zlib.adler32, "stdlib")
    assert (zlib.crc32, zlib.adler32, zipfile.crc32, zipfile.ZipFile.open) == original


@pytest.mark.parametrize("name", ["crc32", "adler32"])
@pytest.mark.parametrize("bad", [None, lambda *args: True, lambda *args: -1, lambda *args: 2**32])
def test_missing_or_wrong_checksum_falls_back(select, name, bad):
    candidate = SimpleNamespace(crc32=zlib.crc32, adler32=zlib.adler32)
    setattr(candidate, name, bad)
    selected = select(candidate)
    assert selected[name][:2] == (getattr(zlib, name), "stdlib")
    other = "adler32" if name == "crc32" else "crc32"
    expected = "zlib-ng" if other == "crc32" else "stdlib"
    assert selected[other][:2] == (getattr(zlib, other), expected)


@pytest.mark.parametrize("name", ["crc32", "adler32"])
def test_ignored_seed_is_rejected(select, name):
    candidate = SimpleNamespace(crc32=zlib.crc32, adler32=zlib.adler32)
    original = getattr(zlib, name)
    setattr(candidate, name, lambda data, seed=0: original(data))
    selected = select(candidate)
    assert selected[name][:2] == (getattr(zlib, name), "stdlib")
    other = "adler32" if name == "crc32" else "crc32"
    expected = "zlib-ng" if other == "crc32" else "stdlib"
    assert selected[other][:2] == (getattr(zlib, other), expected)


@pytest.mark.parametrize("name", ["crc32", "adler32"])
def test_backend_preflight_exception_is_rejected(select, name):
    def broken(*args):
        raise RuntimeError("backend preflight failed")

    candidate = SimpleNamespace(crc32=zlib.crc32, adler32=zlib.adler32)
    setattr(candidate, name, broken)
    selected = select(candidate)
    assert selected[name][:2] == (getattr(zlib, name), "stdlib")
    other = "adler32" if name == "crc32" else "crc32"
    expected = "zlib-ng" if other == "crc32" else "stdlib"
    assert selected[other][:2] == (getattr(zlib, other), expected)


@pytest.mark.parametrize("error", [ImportError("missing"), OSError("unavailable")])
def test_unavailable_backend_falls_back(monkeypatch, error):
    def unavailable(name):
        raise error

    monkeypatch.setattr(backend, "import_module", unavailable)
    selected = backend._select_backend()
    assert all(row[1] == "stdlib" for row in selected.values())


def test_unpinned_version_not_imported(monkeypatch):
    calls = []

    def forbidden(name):
        calls.append(name)
        if name == "zlib_ng":
            return SimpleNamespace(__version__="999")
        raise AssertionError("Unpinned native backend must not be imported")

    monkeypatch.setattr(backend, "import_module", forbidden)
    selected = backend._select_backend()
    assert all(row[1] == "stdlib" for row in selected.values())
    assert calls == ["zlib_ng"]


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(9)])
def test_preflight_does_not_swallow_process_control(monkeypatch, error):
    def stopped(name):
        raise error

    monkeypatch.setattr(backend, "import_module", stopped)
    with pytest.raises(type(error)):
        backend._select_backend()


def test_runtime_selected_crc_error_propagates_without_retry(select):
    state = {"fail": False, "calls": 0}

    def checksum(data, seed=0):
        if state["fail"]:
            state["calls"] += 1
            raise RuntimeError("selected checksum failed during input")
        return zlib.crc32(data, seed)

    candidate = SimpleNamespace(crc32=checksum, adler32=zlib.adler32)
    selected = select(candidate)
    assert selected["crc32"][0] is checksum
    state["fail"] = True
    with pytest.raises(RuntimeError, match="selected checksum failed during input"):
        selected["crc32"][0](b"actual input")
    assert state["calls"] == 1


def test_empty_noncanonical_adler_seed_is_not_excluded_from_preflight(select):
    def incompatible(data, seed=1):
        return seed if data == b"" else zlib.adler32(data, seed)

    candidate = SimpleNamespace(crc32=zlib.crc32, adler32=incompatible)
    selected = select(candidate)
    assert selected["crc32"][:2] == (zlib.crc32, "zlib-ng")
    assert selected["adler32"] == (zlib.adler32, "stdlib", "optional checksum incompatible")
    assert selected["adler32"][0](b"", 0xFFFFFFFF) == 917518
