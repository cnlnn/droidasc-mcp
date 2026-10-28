"""Explicit Java source and legacy ASC compatibility retain original provenance."""

import hashlib
from contextlib import closing
from dataclasses import replace
from pathlib import Path

import pytest
from test_native_dex041 import shared_container

from droidasc_mcp.config import Settings
from droidasc_mcp.service import DroidAscService


@pytest.fixture
def configured_settings(tmp_path):
    settings = Settings.from_env()
    if not settings.jadx_home or not settings.dexlib_home:
        pytest.skip(
            "Configure JADX 1.5.5 and standalone Smali 3.0.9 for explicit source compatibility"
        )
    return replace(settings, allowed_roots=(tmp_path,), timeout_seconds=90)


@pytest.mark.parametrize("sharing", ["none", "forward", "backward_compat"])
def test_explicit_java_source_receives_selected_logical_file(
    configured_settings, tmp_path, sharing
):
    path = tmp_path / "source.dex"
    data = shared_container(("A", "B"), sharing)
    path.write_bytes(data)
    # The installed JADX jars supply the optional bridge's dexlib2 dependency.
    with closing(DroidAscService(replace(configured_settings, dexlib_home=None))) as svc:
        opened = svc.open_dex_session([str(path)])
        key = opened["session_id"]
        root = Path(svc.sessions.entries[key].storage.name)
        original = (root / "analysis.apk").read_bytes()
        path.unlink()
        result = svc.query_dex_session(
            key,
            operation="get_method_source",
            class_name="oracle.B",
            method_descriptor="Loracle/B;->hello()Ljava/lang/String;",
            source_format="java",
            offset=0,
            limit=100,
        )
        assert result["status"] == "ok" and "value-B" in result["source"], result
        assert "value-A" not in result["source"] and result["format"] == "java"
        assert result["source_view"]["kind"] == "dexlib2_reencoded_standalone_040"
        assert result["sources"][1]["sha256"] == hashlib.sha256(data).hexdigest()
        assert (root / "analysis.apk").read_bytes() == original and svc.sessions.reserved == 0


@pytest.mark.parametrize("sharing", ["none", "forward", "backward_compat"])
def test_legacy_reference_adapter_retains_standalone_names(configured_settings, tmp_path, sharing):
    path = tmp_path / "legacy.dex"
    data = shared_container(("A", "B"), sharing, references=True)
    path.write_bytes(data)
    # Legacy 041 normalization uses standalone Smali, not the optional JADX distribution.
    with closing(DroidAscService(replace(configured_settings, jadx_home=None))) as svc:
        opened = svc.open_dex_session([str(path)])
        key = opened["session_id"]
        for kind, value in (("string", "value-B"), ("field", "field")):
            result = svc.query_dex_session(
                key,
                operation="find_refs",
                kind=kind,
                value=value,
                class_name=None,
                fuzzy_class=False,
                threads=1,
                offset=0,
                limit=100,
            )
            assert result["status"] == "ok" and result["total"] >= 1, result
            assert any(
                "oracle/B" in row["raw"] and "classes2.dex" in row["raw"] for row in result["items"]
            ), result
            assert result["compatibility_view"]["requires_java"] is True
            assert result["sources"][1]["sha256"] == hashlib.sha256(data).hexdigest()
            assert svc.sessions.reserved == 0


def test_java_source_unavailable_does_not_change_native_or_smali(settings, tmp_path):
    path = tmp_path / "source.dex"
    path.write_bytes(shared_container(("A", "B"), "forward"))
    with closing(
        DroidAscService(
            replace(settings, java_executable="java-must-not-run", jadx_home=None, dexlib_home=None)
        )
    ) as svc:
        opened = svc.open_dex_session([str(path)])
        result = svc.query_dex_session(
            opened["session_id"],
            operation="get_method_source",
            class_name="oracle.B",
            method_descriptor="Loracle/B;->hello()Ljava/lang/String;",
            source_format="java",
            offset=0,
            limit=100,
        )
        assert result["status"] == "error" and result["code"] == "backend_unavailable", result
        smali = svc.query_dex_session(
            opened["session_id"],
            operation="get_method_source",
            class_name="oracle.B",
            method_descriptor="Loracle/B;->hello()Ljava/lang/String;",
            source_format="smali",
            offset=0,
            limit=100,
        )
        assert smali["status"] == "ok" and "value-B" in smali["source"], smali
        assert svc.sessions.reserved == 0
