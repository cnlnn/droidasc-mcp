"""Runtime configuration and APK path validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .path_policy import ApkPathError as ApkPathError
from .path_policy import PathPolicy


class ConfigurationError(ValueError):
    """Raised when server configuration is invalid."""


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class Settings(PathPolicy):
    """Security and resource limits for the MCP server."""

    allowed_roots: tuple[Path, ...]
    timeout_seconds: int = 180
    max_apk_bytes: int = 2 * 1024 * 1024 * 1024
    max_output_bytes: int = 64 * 1024 * 1024
    max_worker_memory_bytes: int = 2 * 1024 * 1024 * 1024
    max_page_size: int = 1000
    max_parallel: int = 2
    max_dex_sessions: int = 4
    dex_session_ttl_seconds: int = 1800
    max_dex_session_bytes: int = 4 * 1024**3
    jadx_home: Path | None = None
    dexlib_home: Path | None = None
    java_executable: str | None = None
    rust_asc_executable: Path | None = None
    max_xref_index_bytes: int = 512 * 1024**2
    xref_cache_dir: Path | None = None
    max_xref_cache_bytes: int = 1024**3
    xref_cache_ttl_seconds: int = 7 * 86400

    @classmethod
    def from_env(cls) -> Settings:
        raw_roots = os.getenv("DROIDASC_MCP_ALLOWED_ROOTS")
        roots = (
            tuple(Path(item).expanduser().resolve() for item in raw_roots.split(os.pathsep) if item)
            if raw_roots
            else (Path.cwd().resolve(),)
        )
        if not roots:
            raise ConfigurationError("DROIDASC_MCP_ALLOWED_ROOTS contains no usable paths")
        missing = [str(root) for root in roots if not root.is_dir()]
        if missing:
            raise ConfigurationError(f"Allowed root is not a directory: {', '.join(missing)}")
        return cls(
            allowed_roots=roots,
            timeout_seconds=_positive_int("DROIDASC_MCP_TIMEOUT_SECONDS", 180),
            max_apk_bytes=_positive_int("DROIDASC_MCP_MAX_APK_BYTES", 2 * 1024**3),
            max_output_bytes=_positive_int("DROIDASC_MCP_MAX_OUTPUT_BYTES", 64 * 1024**2),
            max_worker_memory_bytes=_positive_int(
                "DROIDASC_MCP_MAX_WORKER_MEMORY_BYTES", 2 * 1024**3
            ),
            max_page_size=_positive_int("DROIDASC_MCP_MAX_PAGE_SIZE", 1000),
            max_parallel=_positive_int("DROIDASC_MCP_MAX_PARALLEL", 2),
            max_dex_sessions=_positive_int("DROIDASC_MCP_MAX_DEX_SESSIONS", 4),
            dex_session_ttl_seconds=_positive_int("DROIDASC_MCP_DEX_SESSION_TTL_SECONDS", 1800),
            max_dex_session_bytes=_positive_int("DROIDASC_MCP_MAX_DEX_SESSION_BYTES", 4 * 1024**3),
            jadx_home=Path(os.environ["DROIDASC_MCP_JADX_HOME"]).expanduser().resolve()
            if os.getenv("DROIDASC_MCP_JADX_HOME")
            else None,
            dexlib_home=Path(os.environ["DROIDASC_MCP_DEXLIB_HOME"]).expanduser().resolve()
            if os.getenv("DROIDASC_MCP_DEXLIB_HOME")
            else None,
            java_executable=os.getenv("DROIDASC_MCP_JAVA"),
            rust_asc_executable=Path(os.environ["DROIDASC_MCP_RUST_ASC"]).expanduser().resolve()
            if os.getenv("DROIDASC_MCP_RUST_ASC")
            else None,
            max_xref_index_bytes=_positive_int("DROIDASC_MCP_MAX_XREF_INDEX_BYTES", 512 * 1024**2),
            xref_cache_dir=Path(os.environ["DROIDASC_MCP_XREF_CACHE_DIR"]).expanduser().absolute()
            if os.getenv("DROIDASC_MCP_XREF_CACHE_DIR")
            else None,
            max_xref_cache_bytes=_positive_int("DROIDASC_MCP_MAX_XREF_CACHE_BYTES", 1024**3),
            xref_cache_ttl_seconds=_positive_int("DROIDASC_MCP_XREF_CACHE_TTL_SECONDS", 7 * 86400),
        )
