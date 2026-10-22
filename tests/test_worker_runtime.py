"""Worker requests share path/paging rules without constructing the host runtime."""

from dataclasses import replace

import pytest

from droidasc_mcp.config import Settings
from droidasc_mcp.path_policy import PathPolicy
from droidasc_mcp.runner import DroidAscError, DroidAscRunner
from droidasc_mcp.worker_errors import DroidAscError as WorkerError
from droidasc_mcp.worker_runtime import WorkerRuntime, WorkerSettings


def test_worker_configuration_and_cli_are_equivalent_to_host_settings(settings, tmp_path):
    expected = replace(
        settings,
        max_apk_bytes=123456,
        max_output_bytes=34567,
        max_page_size=17,
        jadx_home=tmp_path / "optional-jadx",
        dexlib_home=tmp_path / "optional-dexlib",
        java_executable="optional-java",
        max_xref_index_bytes=45678,
        xref_cache_dir=tmp_path / "cache",
        max_xref_cache_bytes=56789,
        xref_cache_ttl_seconds=99,
    )
    request = DroidAscRunner(expected)._dex_request([], {"offset": 0, "limit": 1})
    worker = WorkerSettings(request)
    assert isinstance(worker, PathPolicy)
    assert Settings.validate_artifact is WorkerSettings.validate_artifact
    assert Settings.validate_dex_paths is WorkerSettings.validate_dex_paths
    assert all(getattr(expected, key) == value for key, value in vars(worker).items())
    runtime = WorkerRuntime(worker)
    assert runtime.cli is None
    assert runtime._page_bounds(2, 100) == (2, 17)
    assert runtime.cli is None
    # Only a requested legacy CLI operation constructs its original runner.
    assert runtime.list_classes.__self__ is runtime.cli
    assert all(getattr(runtime.cli.settings, key) == value for key, value in vars(worker).items())
    assert runtime.cli.settings == Settings(**vars(worker))
    assert DroidAscError is WorkerError


@pytest.mark.parametrize("offset,limit", [(-1, 1), (0, 0), (1, -1), (0, 1), (5, 1000000)])
def test_worker_pagination_preserves_host_behavior(settings, offset, limit):
    host = DroidAscRunner(settings)
    runtime = WorkerRuntime(WorkerSettings(host._dex_request([], {})))
    if offset < 0 or limit <= 0:
        with pytest.raises(ValueError) as expected:
            host._page_bounds(offset, limit)
        with pytest.raises(ValueError, match=str(expected.value)):
            runtime._page_bounds(offset, limit)
    else:
        assert runtime._page_bounds(offset, limit) == host._page_bounds(offset, limit)
    assert runtime.cli is None
