"""Both verifier entry paths read the product's actual prepared bytes."""

import importlib.util
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_dex import empty_dex


@pytest.mark.parametrize("artifact_handle", [False, True])
def test_original_byte_verifier_checks_legacy_and_lazy_handle(
    tmp_path, monkeypatch, artifact_handle
):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "ownership_verifier", scripts / "verify_preparation_directory.py"
    )
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    apk = tmp_path / "input.apk"
    with zipfile.ZipFile(apk, "w") as archive:
        archive.writestr("classes.dex", empty_dex())
    output = tmp_path / "receipt.json"
    verifier.main(
        SimpleNamespace(apk=apk, output=output, expanded_mib=512, artifact_handle=artifact_handle)
    )
    result = json.loads(output.read_text())
    assert result["status"] == "passed" and result["artifact_handle"] is artifact_handle
    assert result["snapshot_bytes_match_original"] and result["common_metadata_exact_match"]
    assert result["exact_classes_and_owners"] == 0 and result["dex_count"] == 1
    assert result["session_disk_budget_bytes"] == (8 * 1024**3 if artifact_handle else None)
