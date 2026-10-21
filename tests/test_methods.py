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


@pytest.mark.parametrize(
    "descriptor",
    [
        None,
        "value",
        "LClass;->value",
        "Class->value:I",
        "LClass;->value:V",
        "LClass;->value:[V",
        "LClass;->value:I:Z",
        "LClass;->value()I",
        "LClass;->value:LBad",
        "LClass;->a b:I",
        "LClass;-><init>:I",
    ],
)
def test_field_requires_full_identity(descriptor):
    with pytest.raises(ValueError, match="field_descriptor"):
        _normalize_dex_query({"operation": "find_field_refs", "field_descriptor": descriptor})


@pytest.mark.parametrize(
    "descriptor",
    [
        "LClass;->value:J",
        "LClass;->names:[Ljava/lang/String;",
        "LClass;->matrix:[[I",
        "LClass;->\u503c:I",
    ],
)
def test_field_identity_is_preserved(descriptor):
    query = _normalize_dex_query(
        {
            "operation": "find_field_refs",
            "field_descriptor": descriptor,
            "class_name": "Class",
            "field_access": "read",
        }
    )
    assert query["field_descriptor"] == descriptor
    assert query["class_name"] == "LClass;"
    assert query["field_access"] == "read"


@pytest.mark.parametrize(
    "extra",
    [
        {"class_name": "Other"},
        {"field_access": "guess"},
        {"fuzzy_class": True},
        {"method_descriptor": "LClass;->run()V"},
    ],
)
def test_field_query_rejects_ambiguous_options(extra):
    with pytest.raises(ValueError):
        _normalize_dex_query(
            {"operation": "find_field_refs", "field_descriptor": "LClass;->value:I", **extra}
        )


@pytest.mark.parametrize(
    "extra", [{"field_descriptor": "LClass;->value:I"}, {"field_access": "read"}]
)
def test_field_options_are_not_silently_ignored(extra):
    with pytest.raises(ValueError, match="require find_field_refs"):
        _normalize_dex_query({"operation": "info", **extra})


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
