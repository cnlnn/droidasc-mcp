"""Real profile gates reject silent fallback; command tests preserve base coverage."""

import importlib.util
import subprocess
import sys
import zipfile
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest


def load(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def profile(monkeypatch, tmp_path):
    gate = load("verify_preparation_profile")
    package = tmp_path / "__init__.py"
    native = tmp_path / "zlib_ng.so"
    package.write_text("")
    native.write_bytes(b"synthetic fixture, not a native execution claim")

    def crc(data):
        return 0

    backend = SimpleNamespace(
        __file__=str(tmp_path / "backend.py"),
        CRC_BACKEND_NAME="stdlib",
        ADLER_BACKEND_NAME="stdlib",
        crc32=zlib.crc32,
        adler32=zlib.adler32,
    )
    inflater = SimpleNamespace(INFLATE_BACKEND_NAME="stdlib", open_member=zipfile.ZipFile.open)
    modules = {
        "droidasc_mcp._preparation_backend": backend,
        "droidasc_mcp._preparation_inflate": inflater,
        "zlib_ng": SimpleNamespace(__version__="1.0.0", __file__=str(package)),
        "zlib_ng.zlib_ng": SimpleNamespace(crc32=crc, __file__=str(native)),
    }
    monkeypatch.setattr(gate, "import_module", modules.__getitem__)
    monkeypatch.setattr(gate, "version", lambda name: "1.0.0")
    monkeypatch.setattr(gate, "find_spec", lambda name: None)
    monkeypatch.setattr(gate, "check_inflate", lambda *args: "synthetic.decoder")
    return gate, backend, inflater, modules


def preparation(profile):
    gate, backend, inflater, modules = profile
    backend.CRC_BACKEND_NAME = "zlib-ng"
    backend.crc32 = modules["zlib_ng.zlib_ng"].crc32
    inflater.INFLATE_BACKEND_NAME = "zlib-ng"
    return gate


def test_base_actual_selection(profile):
    assert profile[0].check_profile("base")["crc"] == "stdlib"


def test_optional_actual_selection(profile):
    assert preparation(profile).check_profile("preparation")["inflate"] == "zlib-ng"


def test_base_contamination_rejected(profile, monkeypatch):
    monkeypatch.setattr(profile[0], "find_spec", lambda name: object())
    with pytest.raises(AssertionError, match="contaminated"):
        profile[0].check_profile("base")


@pytest.mark.parametrize("algorithm", ["crc", "inflate", "adler"])
def test_requested_profile_fallback_or_misclassification_rejected(profile, algorithm):
    gate = preparation(profile)
    if algorithm == "crc":
        profile[1].CRC_BACKEND_NAME = "stdlib"
    elif algorithm == "inflate":
        profile[2].INFLATE_BACKEND_NAME = "stdlib"
    else:
        profile[1].ADLER_BACKEND_NAME = "zlib-ng"
    with pytest.raises(AssertionError):
        gate.check_profile("preparation")


def test_unpinned_dependency_rejected(profile, monkeypatch):
    gate = preparation(profile)
    monkeypatch.setattr(gate, "version", lambda name: "99")
    with pytest.raises(AssertionError):
        gate.check_profile("preparation")


def test_label_cannot_substitute_for_crc_identity(profile):
    gate = preparation(profile)
    profile[1].crc32 = zlib.crc32
    with pytest.raises(AssertionError):
        gate.check_profile("preparation")


def test_missing_native_rejected(profile):
    gate = preparation(profile)
    Path(profile[3]["zlib_ng.zlib_ng"].__file__).unlink()
    with pytest.raises(FileNotFoundError):
        gate.check_profile("preparation")


def test_unknown_profile_rejected(profile):
    with pytest.raises(ValueError):
        profile[0].check_profile("anything")


def test_assertions_disabled_cli_rejected():
    gate = load("verify_preparation_profile")
    result = subprocess.run(
        [sys.executable, "-O", gate.__file__, "base"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "assertions enabled" in result.stderr


def test_locked_sync_preserves_base_and_adds_extra_only():
    gate = load("verify_dist")
    base = ["uv", "sync", "--locked", "--extra", "dev", "--python", sys.executable]
    assert gate.sync_command(sys.executable, False) == base
    assert gate.sync_command(sys.executable, True) == base + ["--extra", "preparation"]


def test_profile_and_stage_receipts_distinct(tmp_path):
    gate = load("verify_dist")
    paths = set()
    for profile in ("base", "preparation"):
        for stage in ("sdist", "wheel"):
            command = gate.pytest_command(sys.executable, profile, stage, tmp_path)
            assert command[:4] == [sys.executable, "-m", "pytest", "-q"]
            paths.add(command[-1])
    assert len(paths) == 4
    assert gate.pytest_command(sys.executable, "base", "sdist", None) == [
        sys.executable,
        "-m",
        "pytest",
        "-q",
    ]


@pytest.mark.parametrize("field", ["Requires-Dist", "Provides-Extra"])
def test_package_extra_metadata_mismatch_rejected(tmp_path, field):
    gate = load("verify_dist")
    package = tmp_path / "src" / "droidasc_mcp"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    metadata = "Name: droidasc-mcp\nVersion: 0.2.4\n"
    (tmp_path / "PKG-INFO").write_text(metadata + field + ": original\n")
    wheel = tmp_path / "example.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("droidasc_mcp/__init__.py", "")
        archive.writestr("droidasc_mcp/_dexscan.abi3.so", b"synthetic")
        archive.writestr("droidasc_mcp-0.2.4.dist-info/METADATA", metadata + field + ": changed\n")
    with pytest.raises(AssertionError, match=field):
        gate.distribution_identity(tmp_path, wheel)


def test_existing_receipt_cli_rejected_before_artifact_read(tmp_path):
    gate = load("verify_dist")
    receipt = tmp_path / "base-sdist.xml"
    receipt.write_text("preserved")
    result = subprocess.run(
        [
            sys.executable,
            gate.__file__,
            "missing.tar.gz",
            "missing.whl",
            "--junit-dir",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "Preserve previous" in result.stderr
    assert receipt.read_text() == "preserved"


def test_actual_base_inflater_uses_stdlib_decoder():
    gate = load("verify_preparation_profile")
    observed = gate.check_inflate(SimpleNamespace(open_member=zipfile.ZipFile.open), "base")
    assert observed == type(zlib.decompressobj(-15)).__module__ + ".Decompress"


def test_inflater_label_cannot_substitute_for_native_decoder():
    gate = load("verify_preparation_profile")
    inflater = SimpleNamespace(open_member=zipfile.ZipFile.open, INFLATE_BACKEND_NAME="zlib-ng")
    native = SimpleNamespace(decompressobj=zlib.decompressobj)
    with pytest.raises(AssertionError, match="label is not proof"):
        gate.check_inflate(inflater, "preparation", native)
