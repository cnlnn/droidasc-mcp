"""Check the selected dependency bytes in source and distribution installations."""

import hashlib
import importlib.metadata
import json
from pathlib import Path


def test_installed_upstream_matches_reviewed_source_candidate():
    manifest = json.loads(
        (
            Path(__file__).resolve().parents[1] / "third_party/droidasc_sourcefixes/manifest.json"
        ).read_text(encoding="utf-8")
    )
    distribution = importlib.metadata.distribution("droidasc")
    assert distribution.version == manifest["version"]
    expected = {
        name: item["sha256"]
        for name, item in manifest["files"].items()
        if name.endswith(".py") and name.startswith(("droidasc/", "dadguard/"))
    }
    installed = {
        str(path).replace("\\", "/"): hashlib.sha256(
            distribution.locate_file(path).read_bytes()
        ).hexdigest()
        for path in distribution.files
        if str(path).replace("\\", "/").startswith(("droidasc/", "dadguard/"))
        and str(path).endswith(".py")
    }
    assert len(expected) == manifest["runtime_python_files"] == 80
    assert installed == expected
    original_dadguard = {
        name: item["official_sdist_sha256"]
        for name, item in manifest["files"].items()
        if name.startswith("dadguard/") and name.endswith(".py")
    }
    assert len(original_dadguard) == manifest["unchanged_released_dadguard_python_files"] == 23
    assert {name: installed[name] for name in original_dadguard} == original_dadguard
