"""Fail release acceptance when canonical source and native-wheel identities differ."""

import hashlib
import importlib
import zipfile
from pathlib import Path

import pytest


@pytest.fixture
def distribution_pair(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    verify = importlib.import_module("verify_dist")
    project = tmp_path / "source"
    package = project / "src" / "droidasc_mcp"
    package.mkdir(parents=True)
    metadata = b"Name: droidasc-mcp\nVersion: 0.2.3\n\n"
    (project / "PKG-INFO").write_bytes(metadata)
    (package / "__init__.py").write_bytes(b"version = '0.2.3'\n")
    (package / "input_schemas.json").write_bytes(b"{}\n")
    wheel = tmp_path / "candidate.whl"
    files = {
        "droidasc_mcp/__init__.py": (package / "__init__.py").read_bytes(),
        "droidasc_mcp/input_schemas.json": b"{}\n",
        "droidasc_mcp/_dexscan.abi3.so": b"synthetic-native-bytes",
        "droidasc_mcp-0.2.3.dist-info/METADATA": metadata,
    }

    def check(changes=None):
        contents = {**files, **(changes or {})}
        with zipfile.ZipFile(wheel, "w") as archive:
            for name, data in contents.items():
                if data is not None:
                    archive.writestr(name, data)
        return verify.distribution_identity(project, wheel)

    return check, files


def test_canonical_source_and_native_wheel_identity(distribution_pair):
    check, files = distribution_pair
    version, hashes = check()
    assert version == "0.2.3"
    assert hashes == {
        name.removeprefix("droidasc_mcp/"): hashlib.sha256(data).hexdigest()
        for name, data in files.items()
        if name.startswith("droidasc_mcp/")
    }


@pytest.mark.parametrize(
    "changes",
    [
        {"droidasc_mcp/__init__.py": b"stale source\n"},
        {"droidasc_mcp/input_schemas.json": b'{"stale":true}\n'},
        {"droidasc_mcp/input_schemas.json": None},
        {"droidasc_mcp/unexpected.py": b"pass\n"},
        {"droidasc_mcp/__init__.py": b"version = '0.2.3'\r\n"},
    ],
)
def test_canonical_source_rejects_changed_missing_extra_and_crlf_files(distribution_pair, changes):
    check, _ = distribution_pair
    with pytest.raises(AssertionError, match="canonical sdist"):
        check(changes)


@pytest.mark.parametrize("field", ["Name", "Version"])
def test_canonical_metadata_rejects_wrong_project_or_version(distribution_pair, field):
    check, files = distribution_pair
    name = "droidasc_mcp-0.2.3.dist-info/METADATA"
    original = b"droidasc-mcp" if field == "Name" else b"0.2.3"
    with pytest.raises(AssertionError, match=field):
        check({name: files[name].replace(original, b"wrong")})


@pytest.mark.parametrize(
    "changes",
    [
        {"droidasc_mcp/_dexscan.abi3.so": None},
        {"droidasc_mcp/_dexscan.pyd": b"unexpected-second-native"},
    ],
)
def test_release_wheel_requires_exactly_one_native_accelerator(distribution_pair, changes):
    check, _ = distribution_pair
    with pytest.raises(AssertionError, match="exactly one native"):
        check(changes)
