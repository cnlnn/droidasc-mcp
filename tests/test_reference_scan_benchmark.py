"""Keep the full-result oracle driver compatible with the native path contract."""

import contextlib
import importlib
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


@pytest.mark.parametrize("rounds", [1, 2])
def test_native_oracle_driver_passes_path_to_query(monkeypatch, tmp_path, rounds):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    driver = importlib.import_module("benchmark_reference_scan")
    native = importlib.import_module("droidasc_mcp.native_dex")
    apk = tmp_path / "source.apk"
    with zipfile.ZipFile(apk, "w") as archive:
        archive.writestr("classes.dex", b"original DEX bytes")
    baseline = tmp_path / "Baseline.java"
    baseline.write_text("class Baseline {}", encoding="ascii")
    output = tmp_path / "receipt.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_reference_scan.py",
            str(apk),
            "--native",
            "--baseline-source",
            str(baseline),
            "--java",
            str(tmp_path / "java"),
            "--jadx-home",
            str(tmp_path),
            "--rounds",
            str(rounds),
            "--output",
            str(output),
        ],
    )
    calls = []
    result = {"status": "ok", "instruction_scan_complete": True, "items": [], "total": 0}
    result["scanned_instructions"] = 7

    def query(settings, bundle, request):
        assert isinstance(bundle, Path)
        with zipfile.ZipFile(bundle) as archive:
            assert archive.read("classes.dex") == b"original DEX bytes"
        assert settings.max_page_size == request["limit"] == 2**31 - 1
        calls.append(request["operation"])
        return dict(result)

    def run(command, **kwargs):
        assert kwargs == {"capture_output": True, "check": True, "timeout": 120}
        if command[:2] == [sys.executable, "-c"]:
            stdout = io.StringIO()
            with monkeypatch.context() as child, contextlib.redirect_stdout(stdout):
                child.setattr(sys, "argv", ["-c", *command[3:]])
                exec(command[2], {"__name__": "__main__"})
            payload = stdout.getvalue().encode()
        else:
            payload = json.dumps(result).encode()
        return subprocess.CompletedProcess(command, 0, stdout=payload, stderr=b"")

    monkeypatch.setattr(native, "query_references", query)
    monkeypatch.setattr(driver.subprocess, "run", run)
    driver.main()
    receipt = json.loads(output.read_text())
    assert calls.count("find_method_refs") == calls.count("find_field_refs") == rounds
    assert len(receipt["operations"]) == rounds * 4
    assert receipt["status"] == "all_full_results_equal"
    assert receipt["runtime_unchanged"] and receipt["input_and_sources_unchanged"]
