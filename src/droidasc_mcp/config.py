"""Runtime configuration and APK path validation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class ConfigurationError(ValueError):
    """Raised when server configuration is invalid."""


class ApkPathError(ValueError):
    """Raised when an APK path is outside the configured policy."""


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
class Settings:
    """Security and resource limits for the MCP server."""

    allowed_roots: tuple[Path, ...]
    timeout_seconds: int = 180
    max_apk_bytes: int = 2 * 1024 * 1024 * 1024
    max_output_bytes: int = 64 * 1024 * 1024
    max_page_size: int = 1000
    max_parallel: int = 2

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
            max_page_size=_positive_int("DROIDASC_MCP_MAX_PAGE_SIZE", 1000),
            max_parallel=_positive_int("DROIDASC_MCP_MAX_PARALLEL", 2),
        )

    def validate_apk(self, value: str) -> Path:
        path = Path(value).expanduser().resolve()
        if path.suffix.lower() != ".apk":
            raise ApkPathError("Only .apk files are accepted")
        if not path.is_file():
            raise ApkPathError(f"APK file does not exist: {path}")
        if not any(_is_relative_to(path, root) for root in self.allowed_roots):
            roots = ", ".join(str(root) for root in self.allowed_roots)
            raise ApkPathError(f"APK path is outside allowed roots: {roots}")
        size = path.stat().st_size
        if size > self.max_apk_bytes:
            raise ApkPathError(f"APK exceeds configured size limit: {size} bytes")
        return path


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True
