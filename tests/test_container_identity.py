"""Complete input hashes and consistent post-hash handle identities."""

import hashlib
import io
import threading
import zipfile
from pathlib import Path

import pytest

from droidasc_mcp import containers
from droidasc_mcp.archive_errors import ArchiveError


def artifact(tmp_path, name="input.apk"):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("classes.dex", b"original DEX bytes")
    path = tmp_path / name
    path.write_bytes(data.getvalue())
    return path


@pytest.mark.parametrize("preparation", [False, True])
def test_identity_is_checked_after_the_final_hash(tmp_path, monkeypatch, preparation):
    path = artifact(tmp_path)
    original, calls = containers._digest, []

    def digest(stream):
        value = original(stream)
        calls.append(value)
        if len(calls) == 2:
            path.write_bytes(path.read_bytes() + b"changed during final hash")
        return value

    monkeypatch.setattr(containers, "_digest", digest)
    with (
        pytest.raises(ArchiveError, match="changed during analysis"),
        containers.stable_archive(path, 1024**2, preparation=preparation),
    ):
        pass
    assert len(calls) == 2


@pytest.mark.parametrize("preparation", [False, True])
def test_final_hash_rechecks_the_path_not_just_open_handles(tmp_path, monkeypatch, preparation):
    path, other = artifact(tmp_path), artifact(tmp_path, "other.apk")
    original_hash, original_open, calls = containers._digest, Path.open, []

    def digest(stream):
        value = original_hash(stream)
        calls.append(value)
        return value

    def path_open(self, *args, **kwargs):
        if self == path and len(calls) == 2:
            return original_open(other, *args, **kwargs)
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(containers, "_digest", digest)
    monkeypatch.setattr(Path, "open", path_open)
    with (
        pytest.raises(ArchiveError, match="changed during analysis"),
        containers.stable_archive(path, 1024**2, preparation=preparation),
    ):
        pass
    assert len(calls) == 2


@pytest.mark.parametrize("preparation", [False, True])
def test_handle_identity_does_not_depend_on_path_stat(tmp_path, monkeypatch, preparation):
    path = artifact(tmp_path)
    original = Path.stat

    def path_stat(self, *args, **kwargs):
        if self == path:
            pytest.fail("File identity must use consistent handle-based timestamps")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", path_stat)
    with containers.stable_archive(path, 1024**2, preparation=preparation) as (archive, _, _):
        assert archive.read("classes.dex") == b"original DEX bytes"


@pytest.mark.parametrize("failure", ["hash", "inventory"])
def test_failed_preparation_closes_its_handle(tmp_path, monkeypatch, failure):
    path = artifact(tmp_path)
    original, handles = containers._digest, []

    def digest(stream):
        handles.append(stream)
        if failure == "hash":
            raise OSError("injected hash failure")
        return original(stream)

    monkeypatch.setattr(containers, "_digest", digest)
    if failure == "inventory":
        path.write_bytes(b"not a ZIP")
    error = OSError if failure == "hash" else zipfile.BadZipFile
    with pytest.raises(error), containers.stable_archive(path, 1024**2, preparation=True):
        pass
    assert handles and all(handle.closed for handle in handles)


@pytest.mark.parametrize("preparation", [False, True])
def test_both_complete_hashes_remain_serial(tmp_path, monkeypatch, preparation):
    path = artifact(tmp_path)
    original, threads = containers._digest, []

    def digest(stream):
        threads.append(threading.get_ident())
        return original(stream)

    monkeypatch.setattr(containers, "_digest", digest)
    with containers.stable_archive(path, 1024**2, preparation=preparation) as (archive, _, digest):
        assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
        assert archive.read("classes.dex") == b"original DEX bytes"
    assert threads == [threading.get_ident()] * 2
