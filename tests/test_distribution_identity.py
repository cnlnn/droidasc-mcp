"""Fail release acceptance when canonical source and native-wheel identities differ."""

import hashlib
import importlib
import io
import tarfile
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


@pytest.mark.parametrize("legacy", [False, True])
def test_sdist_extraction_works_without_new_tarfile_filter_api(tmp_path, monkeypatch, legacy):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    verify = importlib.import_module("verify_dist")
    if legacy:
        monkeypatch.delattr(tarfile, "data_filter", raising=False)

        def old_extractall(self, path=".", members=None, *, numeric_owner=False):
            raise AssertionError("Extraction must not depend on extractall/filter support")

        monkeypatch.setattr(tarfile.TarFile, "extractall", old_extractall)
    archive_path = tmp_path / "source.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        directory = tarfile.TarInfo("project/source/")
        directory.type = tarfile.DIRTYPE
        archive.addfile(directory)
        member = tarfile.TarInfo("project/source/name with spaces.txt")
        member.size = 7
        archive.addfile(member, io.BytesIO(b"source\n"))
    root = tmp_path / "output"
    root.mkdir()
    with tarfile.open(archive_path) as archive:
        verify.extract_sdist(archive, root)
    assert (root / "project/source/name with spaces.txt").read_bytes() == b"source\n"


@pytest.mark.parametrize(
    "damage",
    [
        "../outside",
        "/outside",
        "C:/outside",
        "project\\outside",
        "project/../outside",
        "project//outside",
        "project/./outside",
        "project/name. ",
        "symlink",
        "hardlink",
        "device",
        "duplicate",
    ],
)
def test_sdist_extraction_rejects_unsafe_members_before_any_write(tmp_path, monkeypatch, damage):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    verify = importlib.import_module("verify_dist")
    archive_path = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        safe = tarfile.TarInfo("project/safe.txt")
        safe.size = 4
        archive.addfile(safe, io.BytesIO(b"safe"))
        member = tarfile.TarInfo(
            "project/link"
            if damage in {"symlink", "hardlink", "device"}
            else "project/safe.txt"
            if damage == "duplicate"
            else damage
        )
        if damage in {"symlink", "hardlink", "device"}:
            member.type = {
                "symlink": tarfile.SYMTYPE,
                "hardlink": tarfile.LNKTYPE,
                "device": tarfile.CHRTYPE,
            }[damage]
            member.linkname = "../outside"
            archive.addfile(member)
        else:
            archive.addfile(member, io.BytesIO(b""))
    root = tmp_path / "output"
    root.mkdir()
    with tarfile.open(archive_path) as archive, pytest.raises(ValueError, match="sdist member"):
        verify.extract_sdist(archive, root)
    assert not list(root.iterdir())
