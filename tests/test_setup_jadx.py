"""Pinned backend download retries transient failures without weakening verification."""

import hashlib
import importlib.util
import io
import urllib.error
from pathlib import Path

import pytest


@pytest.fixture
def installer(monkeypatch):
    source = Path(__file__).resolve().parents[1] / "scripts/setup_jadx.py"
    spec = importlib.util.spec_from_file_location("setup_jadx", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.time, "sleep", lambda seconds: None)
    return module


def test_transient_download_restarts_and_verifies(installer, monkeypatch, tmp_path):
    data = b"verified release"
    calls = []

    def open_url(*args, **kwargs):
        calls.append(True)
        if len(calls) == 1:
            raise urllib.error.HTTPError("url", 500, "transient", {}, None)
        return io.BytesIO(data)

    monkeypatch.setattr(installer.urllib.request, "urlopen", open_url)
    monkeypatch.setattr(installer, "SHA256", hashlib.sha256(data).hexdigest())
    archive = tmp_path / "archive.zip"
    archive.write_bytes(b"old partial contents")
    installer.download(archive)
    assert archive.read_bytes() == data and len(calls) == 2


@pytest.mark.parametrize("code,attempts", [(404, 1), (500, 3)])
def test_download_attempts_are_bounded(installer, monkeypatch, tmp_path, code, attempts):
    calls = []

    def fail(*args, **kwargs):
        calls.append(True)
        raise urllib.error.HTTPError("url", code, "failure", {}, None)

    monkeypatch.setattr(installer.urllib.request, "urlopen", fail)
    with pytest.raises(urllib.error.HTTPError):
        installer.download(tmp_path / "archive.zip")
    assert len(calls) == attempts


def test_digest_mismatch_is_not_retried(installer, monkeypatch, tmp_path):
    calls = []

    def wrong(*args, **kwargs):
        calls.append(True)
        return io.BytesIO(b"wrong release")

    monkeypatch.setattr(installer.urllib.request, "urlopen", wrong)
    with pytest.raises(RuntimeError, match="digest mismatch"):
        installer.download(tmp_path / "archive.zip")
    assert len(calls) == 1
