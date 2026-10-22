"""Benchmark-only inherited CPU budgets never alter the caller's affinity."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def wrapper():
    path = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_cpu_wrapper.py"
    spec = importlib.util.spec_from_file_location("cpu_wrapper", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Affinity:
    def __init__(self, allowed=(2, 4, 6, 8), refuse=False):
        self.allowed, self.refuse, self.writes = list(allowed), refuse, []

    def cpu_affinity(self, value=None):
        if value is not None:
            self.writes.append(value)
            if not self.refuse:
                self.allowed = value
        return list(self.allowed)


def test_select_budget_is_read_only_and_configure_applies_exact_mask(wrapper):
    process = Affinity()
    assert wrapper.select_cpus(2, process) == [2, 4]
    assert process.writes == []
    wrapper.configure_affinity([2, 6], process)
    assert process.writes == [[2, 6]] and process.allowed == [2, 6]


@pytest.mark.parametrize("workers", [0, -1, 5])
def test_unavailable_cpu_budget_fails_instead_of_silent_reduction(wrapper, workers):
    with pytest.raises(ValueError, match="exceeds"):
        wrapper.select_cpus(workers, Affinity())


@pytest.mark.parametrize("cpus", [[], [2, 2], [-1], [True], [1.0], [0]])
def test_invalid_or_unavailable_affinity_cannot_launch_server(wrapper, cpus):
    process = Affinity()
    with pytest.raises(ValueError):
        wrapper.configure_affinity(cpus, process)
    assert process.writes == []


def test_unsupported_or_unapplied_affinity_fails_closed(wrapper):
    with pytest.raises(RuntimeError, match="support"):
        wrapper.select_cpus(1, object())
    with pytest.raises(RuntimeError, match="support"):
        wrapper.configure_affinity([2], object())
    with pytest.raises(RuntimeError, match="complete"):
        wrapper.configure_affinity([2], Affinity(refuse=True))


@pytest.mark.parametrize("server", ["droidasc_mcp", "asc_mcp"])
def test_budget_precedes_server_import_and_preserves_module_spawn_semantics(
    wrapper, monkeypatch, server
):
    process, calls = Affinity(), []
    monkeypatch.setattr(wrapper.psutil, "Process", lambda: process)
    monkeypatch.setattr(wrapper.sys, "argv", ["wrapper.py", "--cpus", "2,6", server])

    def run(module, **kwargs):
        assert process.allowed == [2, 6]
        assert wrapper.sys.argv == [server]
        calls.append((module, kwargs))

    monkeypatch.setattr(wrapper.runpy, "run_module", run)
    wrapper.main()
    assert calls == [(server, {"run_name": "__main__", "alter_sys": True})]
