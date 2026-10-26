"""Synthetic verifier outcomes are not corpus evidence or release authorization."""

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def verifier(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location(
        "method_selection_outcomes", scripts / "verify_method_selection.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def attempt(verifier, monkeypatch, tmp_path):
    apk = tmp_path / "synthetic-input.bin"
    apk.write_bytes(b"synthetic fixture, no APK")
    args = SimpleNamespace(apk=apk, output=tmp_path / "receipt.json", competitor=tmp_path)
    selected = {
        "class_name": "Lsynthetic/A;",
        "method_name": "one",
        "prototype": "()V",
        "container_entry": "classes.dex",
        "instructions": [(0, "return-void")],
    }
    overloaded = {
        "class_name": "Lsynthetic/A;",
        "method_name": "many",
        "target_descriptor": "()V",
        "candidate_count": 2,
    }
    monkeypatch.setattr(verifier, "original_methods", lambda _: (selected, overloaded))
    monkeypatch.setattr(verifier, "runtime_identity", lambda: {"synthetic": "runtime"})
    monkeypatch.setattr(
        verifier, "competitor_runtime_identity", lambda _: {"synthetic": "comparator"}
    )
    monkeypatch.setattr(verifier, "digest", lambda _: "a" * 64)
    monkeypatch.setattr(verifier.subprocess, "check_output", lambda *a, **kw: "b" * 40)
    state = {"failure": None, "cleanup_failure": None, "opened": []}

    def reply(content=None, error=False):
        return SimpleNamespace(is_error=error, structured_content=content)

    class Client:
        def __init__(self, endpoint):
            self.component = "product" if endpoint.args[-1] == "droidasc_mcp" else "comparator"

        async def __aenter__(self):
            state["opened"].append(self.component)
            return self

        async def __aexit__(self, *args):
            if state.get("exit_failure") == self.component:
                raise RuntimeError("client context cleanup failed")
            return False

        async def call_tool(self, tool, params=None):
            params = params or {}
            cleanup = tool in {"asc_close_dex_session", "close_artifact"}
            failure = state["cleanup_failure"] if cleanup else state["failure"]
            if failure and failure[0] == self.component:
                if isinstance(failure[1], BaseException):
                    raise failure[1]
                if failure[1] == "tool_error":
                    return reply(error=True)
                if failure[1] == "mismatch" and tool == "apk_disassemble_method":
                    return reply({"descriptor": "wrong", "instructions": []})
            if tool == "asc_open_artifact_session":
                return reply({"status": "ok", "session_id": "synthetic"})
            if tool == "asc_close_dex_session":
                return reply({"status": "ok"})
            if tool == "asc_ping":
                return reply({"dex_sessions": {"open_count": 0}})
            if tool == "asc_query_dex_session":
                if params.get("method_name") == "many":
                    if "target_descriptor" not in params:
                        return reply({"code": "ambiguous_method", "candidate_count": 2})
                    return reply({"status": "ok", "candidate_count": 1})
                return reply(
                    {
                        "status": "ok",
                        "candidate_count": 1,
                        "method_descriptor": "Lsynthetic/A;->one()V",
                        "has_more": False,
                        "items": [{"instruction_offset": 0, "opcode": "return-void"}],
                    }
                )
            if tool == "load_artifact":
                return reply({"analysis_id": "synthetic"})
            if tool == "close_artifact":
                return reply({})
            if tool == "apk_disassemble_method":
                if params["method_name"] == "many":
                    return reply({"message": "overloaded"}, error=True)
                return reply(
                    {"descriptor": "()V", "instructions": [{"offset": 0, "opcode": "return-void"}]}
                )
            raise AssertionError(tool)

    monkeypatch.setattr(verifier, "Client", Client)
    return args, state


def receipt(args):
    return json.loads(args.output.read_text())


def test_all_pass_retains_old_contract(verifier, attempt):
    args, _ = attempt
    asyncio.run(verifier.main(args))
    report = receipt(args)
    assert report["status"] == report["competitor_disassembly_and_ambiguity"] == "passed"
    assert set(report["component_outcomes"].values()) == {"passed"}
    assert report["input_runtime_and_verifier_unchanged"] is True
    assert len(report["operations"]) == 5


@pytest.mark.parametrize(
    "error,kind",
    [
        (TimeoutError("typed deadline"), "timeout"),
        (RuntimeError("OOM timeout SIGKILL resource limit"), "unexpected_error"),
        (MemoryError("allocation failure"), "unexpected_error"),
        (asyncio.CancelledError(), "interrupted"),
        ("tool_error", "tool_error"),
        ("mismatch", "correctness_mismatch"),
    ],
)
def test_comparator_failure_is_still_strict(verifier, attempt, error, kind):
    args, state = attempt
    state["failure"] = ("comparator", error)
    expected = (
        type(error)
        if isinstance(error, BaseException)
        else (verifier.ToolFailure if error == "tool_error" else verifier.VerificationMismatch)
    )
    with pytest.raises(expected):
        asyncio.run(verifier.main(args))
    report = receipt(args)
    assert report["status"] == "failed"
    assert report["phase"] == "comparator"
    assert report["failure"]["kind"] == kind
    assert report["component_outcomes"] == {
        "product": "passed",
        "comparator": "failed",
        "integrity": "not_verified",
    }
    assert "input_runtime_and_verifier_unchanged" not in report


def test_product_failure_never_becomes_comparator_only(verifier, attempt):
    args, state = attempt
    state["failure"] = ("product", TimeoutError("product deadline"))
    with pytest.raises(TimeoutError):
        asyncio.run(verifier.main(args))
    report = receipt(args)
    assert report["phase"] == "product" and report["status"] == "failed"
    assert report["component_outcomes"]["comparator"] == "not_started"
    assert state["opened"] == ["product"]


@pytest.mark.parametrize("component", ["product", "comparator"])
def test_cleanup_failure_alone_fails_component(verifier, attempt, component):
    args, state = attempt
    state["cleanup_failure"] = (component, RuntimeError("close failure"))
    with pytest.raises(RuntimeError, match="close failure"):
        asyncio.run(verifier.main(args))
    report = receipt(args)
    assert report["phase"] == component and report["status"] == "failed"
    assert report["cleanup_errors"][0]["error"] == "RuntimeError('close failure')"


def test_cleanup_error_does_not_mask_primary_mismatch(verifier, attempt):
    args, state = attempt
    state["failure"] = ("comparator", "mismatch")
    state["cleanup_failure"] = ("comparator", RuntimeError("close failure"))
    with pytest.raises(verifier.VerificationMismatch):
        asyncio.run(verifier.main(args))
    report = receipt(args)
    assert report["failure"]["kind"] == "correctness_mismatch"
    assert report["cleanup_errors"][0]["kind"] == "unexpected_error"


def test_integrity_failure_is_not_comparator_failure(verifier, attempt, monkeypatch):
    args, _ = attempt
    identities = iter([{"first": "identity"}, {"first": "identity"}, {"changed": "identity"}])
    monkeypatch.setattr(verifier, "runtime_identity", lambda: next(identities))
    with pytest.raises(verifier.VerificationMismatch):
        asyncio.run(verifier.main(args))
    report = receipt(args)
    assert report["phase"] == "integrity" and report["status"] == "failed"
    assert report["component_outcomes"] == {
        "product": "passed",
        "comparator": "passed",
        "integrity": "failed",
    }
    assert "input_runtime_and_verifier_unchanged" not in report


def test_preserve_prior_receipt(verifier, attempt):
    args, _ = attempt
    args.output.write_text("prior attempt")
    with pytest.raises(verifier.VerificationMismatch, match="Preserve"):
        asyncio.run(verifier.main(args))
    assert args.output.read_text() == "prior attempt"


def test_client_context_cleanup_retains_original_failure_chain(verifier, attempt):
    args, state = attempt
    state["failure"] = ("comparator", "mismatch")
    state["exit_failure"] = "comparator"
    with pytest.raises(RuntimeError, match="client context cleanup"):
        asyncio.run(verifier.main(args))
    report = receipt(args)
    assert report["status"] == "failed"
    assert [error["kind"] for error in report["failure_chain"]] == [
        "unexpected_error",
        "correctness_mismatch",
    ]


@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(1)])
def test_explicit_interruption_classification(verifier, error):
    assert verifier.failure_detail(error)["kind"] == "interrupted"


def test_disabled_assertions_rejected_before_input_or_clients(verifier):
    script = Path(verifier.__file__).resolve()
    code = (
        "import asyncio, importlib.util; "
        f"s=importlib.util.spec_from_file_location('v', {str(script)!r}); "
        "v=importlib.util.module_from_spec(s); s.loader.exec_module(v); "
        "asyncio.run(v.main(object()))"
    )
    result = subprocess.run(
        [sys.executable, "-O", "-c", code],
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "requires assertions enabled" in result.stderr
    assert "AttributeError" not in result.stderr


def test_product_identity_change_blocks_comparator_despite_five_operations(
    verifier, attempt, monkeypatch
):
    args, state = attempt
    identities = iter([{"first": "identity"}, {"changed": "identity"}])
    monkeypatch.setattr(verifier, "runtime_identity", lambda: next(identities))
    with pytest.raises(verifier.VerificationMismatch):
        asyncio.run(verifier.main(args))
    report = receipt(args)
    assert len(report["operations"]) == 5
    assert report["overload_recovery"] == "passed"
    assert report["status"] == "failed"
    assert report["component_outcomes"]["product"] == "failed"
    assert report["component_outcomes"]["comparator"] == "not_started"
    assert "product_input_runtime_and_verifier_unchanged" not in report
    assert state["opened"] == ["product"]
