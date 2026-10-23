"""Measured graph receipts cannot borrow independent acceptance for another input."""

import copy
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def verifier(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("verify_graph_benchmark")


@pytest.fixture
def accepted(verifier):
    sources = [{"dex_entry": "classes.dex", "sha256": "original", "size_bytes": 128}]
    return {
        "schema": 2,
        "status": verifier.STATUS,
        "input_id": "input",
        "engine_version": "engine",
        "sources": sources,
        "sources_sha256": verifier.fingerprint(sources),
        "index_sha256": "independently-accepted-index",
    }


def test_measured_graph_retains_exact_acceptance_binding(verifier, accepted):
    opened = {**accepted, "session_id": "new-session"}
    assert verifier.bind_graph_acceptance(accepted, opened) == {
        "accepted_index_sha256": accepted["index_sha256"],
        "independent_acceptance_sha256": verifier.fingerprint(accepted),
    }


@pytest.mark.parametrize("field", ["input_id", "engine_version", "sources"])
def test_measured_graph_rejects_other_input_identity(verifier, accepted, field):
    opened = copy.deepcopy(accepted)
    opened[field] = [] if field == "sources" else "other"
    with pytest.raises(AssertionError, match=f"Measured {field}"):
        verifier.bind_graph_acceptance(accepted, opened)


@pytest.mark.parametrize("field", ["input_id", "engine_version", "sources"])
def test_measured_graph_rejects_missing_input_identity(verifier, accepted, field):
    opened = copy.deepcopy(accepted)
    del opened[field]
    with pytest.raises(KeyError):
        verifier.bind_graph_acceptance(accepted, opened)


@pytest.mark.parametrize(
    ("field", "value"),
    [("schema", 1), ("status", "running"), ("status", "failed"), ("sources_sha256", "stale")],
)
def test_measured_graph_rejects_unaccepted_or_stale_receipt(verifier, accepted, field, value):
    opened = copy.deepcopy(accepted)
    accepted[field] = value
    with pytest.raises(AssertionError):
        verifier.bind_graph_acceptance(accepted, opened)


def test_bound_digest_changes_with_independent_evidence(verifier, accepted):
    opened = copy.deepcopy(accepted)
    original = verifier.bind_graph_acceptance(accepted, opened)
    accepted["independent_call_sites"] = 12
    changed = verifier.bind_graph_acceptance(accepted, opened)
    assert changed["accepted_index_sha256"] == original["accepted_index_sha256"]
    assert changed["independent_acceptance_sha256"] != original["independent_acceptance_sha256"]
