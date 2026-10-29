"""Keep the separate upstream contribution reproducible without changing defaults."""

import difflib
import hashlib
import importlib
import io
import json
import tarfile
from pathlib import Path

import pytest


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


@pytest.fixture
def sourcefixes(tmp_path, monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    tool = importlib.import_module("upstream_sourcefixes.prepare")
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    official = {
        "LICENSE": (scripts / "upstream_sourcefixes/LICENSE").read_bytes(),
        "README.md": b"# Original upstream source\n",
        "pyproject.toml": b'[project]\nname = "droidasc"\nversion = "0.1.2-post3"\n',
        "droidasc/asc_core/utils/decompiler.py": b'def render():\n    return "original"\n',
        "dadguard/writer.py": b"# released parser bytes\r\n",
        "tests/dex_fixture.py": b"def make_fixture():\n    return b''\n",
    }
    (bundle / "LICENSE").write_bytes(official["LICENSE"])
    middle = {
        **official,
        "droidasc/asc_core/utils/decompiler.py": b'def render():\n    return "annotations"\n',
        "tests/test_method_annotations.py": b"# generated annotation fixture\n",
    }
    final = {
        **middle,
        "droidasc/asc_core/utils/decompiler.py": b'def render():\n    return "sourcefixes"\n',
        "tests/dex_fixture.py": b"def make_fixture(kind=b'Lexample/Type;'):\n    return kind\n",
        "tests/test_source_type_links.py": b"# generated original-type fixture\n",
    }

    def patch(before, after, name):
        text = "".join(
            "".join(
                difflib.unified_diff(
                    before.get(path, b"").decode().splitlines(keepends=True),
                    after.get(path, b"").decode().splitlines(keepends=True),
                    fromfile="a/" + path if path in before else "/dev/null",
                    tofile="b/" + path if path in after else "/dev/null",
                )
            )
            for path in sorted(before.keys() | after.keys())
            if before.get(path) != after.get(path)
        )
        (bundle / name).write_text(text, encoding="utf-8", newline="")
        return {"filename": name, "sha256": digest(text.encode())}

    manifest = json.loads((scripts / "upstream_sourcefixes/manifest.json").read_text())
    manifest["patches"] = [
        patch(official, middle, "first.patch"),
        patch(middle, final, "second.patch"),
    ]
    manifest["original_runtime_sha256"] = digest(official[manifest["runtime_path"]])
    manifest["prepared_runtime_sha256"] = digest(final[manifest["runtime_path"]])
    manifest["python_files"], manifest["dadguard_python_files"] = 2, 1
    archive_path = tmp_path / "official.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for name, data in official.items():
            entry = tarfile.TarInfo(manifest["sdist"]["root"] + "/" + name)
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
    manifest["sdist"]["sha256"] = digest(archive_path.read_bytes())
    manifest["sdist"]["size_bytes"] = archive_path.stat().st_size
    manifest_path = bundle / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return tool, bundle, archive_path, manifest, official, final


def test_offline_preparation_uses_standard_git_patches_and_retains_released_bytes(
    sourcefixes, tmp_path, monkeypatch
):
    tool, bundle, archive, manifest, official, final = sourcefixes
    original_archive = archive.read_bytes()
    output = tmp_path / "prepared"
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "unrelated-git-dir"))
    monkeypatch.setenv("GIT_WORK_TREE", str(tmp_path / "unrelated-work-tree"))
    receipt = tool.prepare_source(archive, output, bundle=bundle)
    assert archive.read_bytes() == original_archive
    assert (output / "source/dadguard/writer.py").read_bytes() == official["dadguard/writer.py"]
    assert (output / "source/droidasc/asc_core/utils/decompiler.py").read_bytes() == final[
        manifest["runtime_path"]
    ]
    assert (output / "source/tests/dex_fixture.py").read_bytes() == official["tests/dex_fixture.py"]
    assert not (output / "source/tests/test_method_annotations.py").exists()
    assert not (output / "source/tests/test_source_type_links.py").exists()
    assert (
        b'version = "0.1.2.post3+sourcefixes.2"' in (output / "source/pyproject.toml").read_bytes()
    )
    assert (output / "source/README.md").read_bytes().endswith(official["README.md"])
    assert receipt["changed_source_paths"] == manifest["expected_changed_paths"]
    assert receipt["changed_runtime_paths"] == [manifest["runtime_path"]]
    assert receipt["application_scope"] == "runtime_hunks_only"
    assert not receipt["contribution_test_hunks_applied"]
    assert receipt["unchanged_released_dadguard_python_files"] == 1
    assert receipt["original_archive_unchanged"]
    assert not receipt["built_or_installed"] and not receipt["default_dependency_changed"]
    assert json.loads((output / "receipt.json").read_text()) == receipt
    assert not list(tmp_path.glob("asc-sourcefixes-*"))


def test_official_archive_without_git_fixture_needs_only_runtime_hunks(sourcefixes, tmp_path):
    tool, bundle, archive, manifest, official, final = sourcefixes
    with tarfile.open(archive) as source:
        members = [
            (entry, source.extractfile(entry).read())
            for entry in source.getmembers()
            if not entry.name.endswith("/tests/dex_fixture.py")
        ]
    with tarfile.open(archive, "w:gz") as target:
        for entry, data in members:
            target.addfile(entry, io.BytesIO(data))
    manifest["sdist"]["sha256"] = digest(archive.read_bytes())
    manifest["sdist"]["size_bytes"] = archive.stat().st_size
    manifest["expected_changed_paths"] = ["README.md", manifest["runtime_path"], "pyproject.toml"]
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "prepared"
    receipt = tool.prepare_source(archive, output, bundle=bundle)
    assert (output / "source" / manifest["runtime_path"]).read_bytes() == final[
        manifest["runtime_path"]
    ]
    assert not (output / "source/tests").exists()
    assert (output / "source/dadguard/writer.py").read_bytes() == official["dadguard/writer.py"]
    assert receipt["changed_source_paths"] == manifest["expected_changed_paths"]


def test_patch_rejection_surfaces_git_stderr_and_cleans_stage(sourcefixes, tmp_path):
    tool, bundle, archive, manifest, _, _ = sourcefixes
    patch = bundle / manifest["patches"][0]["filename"]
    patch.write_bytes(patch.read_bytes().replace(b'return "original"', b'return "missing!"'))
    manifest["patches"][0]["sha256"] = digest(patch.read_bytes())
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    output = tmp_path / "prepared"
    with pytest.raises(ValueError, match=r"first.patch.*patch failed"):
        tool.prepare_source(archive, output, bundle=bundle)
    assert not output.exists()
    assert not list(tmp_path.glob("asc-sourcefixes-*"))


@pytest.mark.parametrize(
    "damage", ["archive", "patch", "license", "runtime", "inventory", "output", "scope"]
)
def test_offline_preparation_rejects_changed_inputs_or_scope(sourcefixes, tmp_path, damage):
    tool, bundle, archive, manifest, _, _ = sourcefixes
    output = tmp_path / "prepared"
    if damage == "archive":
        archive.write_bytes(archive.read_bytes() + b"changed")
    elif damage == "patch":
        path = bundle / manifest["patches"][0]["filename"]
        path.write_bytes(path.read_bytes() + b"changed")
    elif damage == "license":
        (bundle / "LICENSE").write_bytes(b"changed")
    elif damage == "runtime":
        manifest["prepared_runtime_sha256"] = "0" * 64
    elif damage == "inventory":
        manifest["dadguard_python_files"] += 1
    elif damage == "scope":
        manifest["expected_changed_paths"] = []
    elif damage == "output":
        output.mkdir()
        (output / "user.txt").write_bytes(b"user content")
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        tool.prepare_source(archive, output, bundle=bundle)
    if damage == "output":
        assert (output / "user.txt").read_bytes() == b"user content"
    else:
        assert not output.exists()
    assert not list(tmp_path.glob("asc-sourcefixes-*"))


def test_reviewed_bundle_hashes_and_runtime_boundaries_are_locked(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    tool = importlib.import_module("upstream_sourcefixes.prepare")
    manifest = json.loads((tool.BUNDLE / "manifest.json").read_text())
    assert (
        manifest["sdist"]["sha256"]
        == "0e292a2756db85c5fd3fda0a397f2ad544c8de016135a79ed5ed739ecbb89230"
    )
    assert manifest["python_files"] == 80 and manifest["dadguard_python_files"] == 23
    assert manifest["original_source_version"] == "0.1.2-post3"
    assert tool.sha256(tool.BUNDLE / "LICENSE") == manifest["license_sha256"]
    assert all(tool.sha256(tool.BUNDLE / p["filename"]) == p["sha256"] for p in manifest["patches"])
    assert (
        manifest["prepared_runtime_sha256"]
        == "81fc8edff8881949441bcdeb3ed6b54bb371203aaf6bd99c028af5236d9d8836"
    )
