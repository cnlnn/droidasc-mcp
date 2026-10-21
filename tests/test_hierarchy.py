"""Exact hierarchy queries and honest parsing of public CLI declarations."""

from unittest.mock import Mock

import pytest

from droidasc_mcp.runner import DroidAscRunner, _parse_hierarchy
from droidasc_mcp.service import DroidAscService


@pytest.mark.parametrize("kind", ["extends", "impl"])
@pytest.mark.parametrize(
    "name, expected", [("Login", "LLogin;"), ("LLogin;", "LLogin;"), ("Local.Base", "LLocal/Base;")]
)
def test_exact_hierarchy_normalization(settings, apk_file, kind, name, expected):
    runner = Mock()
    runner.find_refs.return_value = {}
    runner.analyze_dex.return_value = {}
    service = DroidAscService(settings, runner)
    query = dict(
        kind=kind, value=name, class_name=None, fuzzy_class=False, threads=1, offset=0, limit=10
    )
    service.find_refs(str(apk_file), **query)
    assert runner.find_refs.call_args.kwargs["value"] == expected
    dex = apk_file.with_suffix(".dex")
    dex.write_bytes(b"fixture")
    service.analyze_dex([str(dex)], operation="find_refs", **query)
    assert runner.analyze_dex.call_args.args[1]["value"] == expected


@pytest.mark.parametrize("kind", ["extends", "impl"])
@pytest.mark.parametrize(
    "extra", [{"value": None}, {"class_name": "Login"}, {"fuzzy_class": True}, {"value": "--gui"}]
)
def test_invalid_hierarchy_queries_do_not_launch(settings, apk_file, monkeypatch, kind, extra):
    runner = DroidAscRunner(settings)

    def fail(*args, **kwargs):
        pytest.fail("Invalid hierarchy query reached CLI")

    monkeypatch.setattr(runner, "_execute", fail)
    query = dict(
        kind=kind, value="Login", class_name=None, fuzzy_class=False, threads=1, offset=0, limit=10
    )
    with pytest.raises(ValueError):
        runner.find_refs(apk_file, **{**query, **extra})


@pytest.mark.parametrize("kind, relation", [("extends", "extends"), ("impl", "implements")])
def test_hierarchy_records_are_not_method_references(kind, relation):
    raw = f"classes2.dex | LChild; {relation} LBase;"
    assert _parse_hierarchy(raw, kind) == {
        "dex": "classes2.dex",
        "class_name": "LChild;",
        "relation": relation,
        "target": "LBase;",
        "raw": raw,
    }
    for malformed in (raw + " extra", "unrecognized", raw.replace("LChild;", "LChild; | x")):
        assert _parse_hierarchy(malformed, kind) == {"raw": malformed}
