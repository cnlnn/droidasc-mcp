"""Exact descriptor validation and optional backend failures without a JVM dependency."""

from dataclasses import replace

import pytest

from droidasc_mcp.method_backend import query_methods
from droidasc_mcp.service import _normalize_dex_query


@pytest.mark.parametrize(
    "descriptor",
    [
        None,
        "marker",
        "marker()V",
        "Class->marker()V",
        "LClass;->marker()",
        "LClass;->marker(V)V",
        "LClass;->marker()[V",
        "LClass;->marker(LNoSemicolon)V",
    ],
)
@pytest.mark.parametrize("operation", ["get_method_source", "find_method_refs", "get_method_calls"])
def test_method_requires_full_identity(descriptor, operation):
    with pytest.raises(ValueError, match="descriptor"):
        _normalize_dex_query({"operation": operation, "method_descriptor": descriptor})


def test_method_owner_is_not_silently_replaced():
    with pytest.raises(ValueError, match="different classes"):
        _normalize_dex_query(
            {
                "operation": "get_method_source",
                "class_name": "other.Class",
                "method_descriptor": "LClass;->marker()V",
            }
        )
    query = _normalize_dex_query(
        {"operation": "get_method_source", "method_descriptor": "LClass;->marker()V"}
    )
    assert query["class_name"] == "LClass;"


def test_backend_is_explicitly_optional(settings, tmp_path):
    assert (
        query_methods(settings, tmp_path / "input.apk", "classes.dex", {})["code"]
        == "backend_unavailable"
    )
    configured = replace(settings, jadx_home=tmp_path, java_executable="missing-java")
    assert (
        query_methods(configured, tmp_path / "input.apk", "classes.dex", {})["code"]
        == "backend_unavailable"
    )


def test_invalid_source_format():
    with pytest.raises(ValueError, match="source_format"):
        _normalize_dex_query({"operation": "list_methods", "source_format": "guess"})


@pytest.mark.parametrize("operation,mode", [("info", "smali"), ("get_method_source", "auto")])
def test_debug_info_requires_native_smali(operation, mode):
    with pytest.raises(ValueError, match="debug_info"):
        _normalize_dex_query(
            {
                "operation": operation,
                "source_format": mode,
                "method_descriptor": "LClass;->marker()V",
                "debug_info": True,
            }
        )
