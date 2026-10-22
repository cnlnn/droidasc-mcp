"""Decode the host's request and defer CLI infrastructure until a CLI operation."""

from pathlib import Path

from .path_policy import PathPolicy
from .worker_errors import page_bounds


class WorkerSettings(PathPolicy):
    def __init__(self, request):
        self.allowed_roots = tuple(Path(p) for p in request["allowed_roots"])
        self.max_apk_bytes = request["max_input_bytes"]
        self.max_output_bytes = request["max_output_bytes"]
        self.max_page_size = request["max_page_size"]
        self.jadx_home = Path(request["jadx_home"]) if request.get("jadx_home") else None
        self.dexlib_home = Path(request["dexlib_home"]) if request.get("dexlib_home") else None
        self.java_executable = request.get("java_executable")
        self.max_xref_index_bytes = request.get("max_xref_index_bytes", 256 * 1024**2)
        self.xref_cache_dir = (
            Path(request["xref_cache_dir"]) if request.get("xref_cache_dir") else None
        )
        self.max_xref_cache_bytes = request.get("max_xref_cache_bytes", 1024**3)
        self.xref_cache_ttl_seconds = request.get("xref_cache_ttl_seconds", 7 * 86400)


class WorkerRuntime:
    def __init__(self, settings):
        self.settings = settings
        self.cli = None

    def _page_bounds(self, offset, limit):
        return page_bounds(offset, limit, self.settings.max_page_size)

    def __getattr__(self, name):
        if self.cli is None:
            from .cli_worker import PublicCliRunner
            from .config import Settings

            self.cli = PublicCliRunner(Settings(**vars(self.settings)))
        return getattr(self.cli, name)
