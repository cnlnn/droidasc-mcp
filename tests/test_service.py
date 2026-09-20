from __future__ import annotations

import hashlib
from pathlib import Path

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService, _normalize_class_name


def test_apk_info_reports_provenance(settings: Settings, apk_file: Path):
    result = DroidAscService(settings).apk_info(str(apk_file))
    assert result["apk_path"] == str(apk_file.resolve())
    assert result["has_manifest"] is True
    assert result["dex_entries"] == ["classes.dex", "classes2.dex"]
    assert result["sha256"] == hashlib.sha256(apk_file.read_bytes()).hexdigest()


def test_normalize_class_name():
    assert _normalize_class_name("com.example.Main") == "Lcom/example/Main;"
    assert _normalize_class_name("Lcom/example/Main;") == "Lcom/example/Main;"
