from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService, _normalize_class_name


def test_apk_info_reports_provenance(settings: Settings, apk_file: Path):
    result = DroidAscService(settings).apk_info(str(apk_file))
    assert result["apk_path"] == str(apk_file.resolve())
    assert result["has_manifest"] is True
    assert result["dex_entries"] == ["classes.dex", "classes2.dex"]
    assert result["sha256"] == hashlib.sha256(apk_file.read_bytes()).hexdigest()


def test_normalize_class_name():
    assert _normalize_class_name("Login") == "LLogin;"
    assert _normalize_class_name("Local.Main") == "LLocal/Main;"
    assert _normalize_class_name("LLogin;") == "LLogin;"
    assert _normalize_class_name("com.example.Main") == "Lcom/example/Main;"
    assert _normalize_class_name("Lcom/example/Main;") == "Lcom/example/Main;"


@pytest.mark.parametrize("kind", ["method", "field"])
@pytest.mark.parametrize(
    "name, expected",
    [
        ("Login", "LLogin;"),
        ("Local.Main", "LLocal/Main;"),
        ("LLogin;", "LLogin;"),
    ],
)
def test_member_reference_exact_class_normalization(settings, apk_file, kind, name, expected):
    runner = Mock()
    runner.find_refs.return_value = {}
    DroidAscService(settings, runner).find_refs(
        str(apk_file),
        kind=kind,
        value="marker",
        class_name=name,
        fuzzy_class=False,
        threads=1,
        offset=0,
        limit=10,
    )
    assert runner.find_refs.call_args.kwargs["class_name"] == expected


@pytest.mark.parametrize("kind", ["method", "field"])
def test_member_reference_fuzzy_class_is_preserved(settings, apk_file, kind):
    runner = Mock()
    runner.find_refs.return_value = {}
    DroidAscService(settings, runner).find_refs(
        str(apk_file),
        kind=kind,
        value="marker",
        class_name="Login",
        fuzzy_class=True,
        threads=1,
        offset=0,
        limit=10,
    )
    assert runner.find_refs.call_args.kwargs["class_name"] == "Login"
