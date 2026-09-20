"""MCP adapter for the Droid ASC Android decompiler."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("droidasc-mcp")
except PackageNotFoundError:  # pragma: no cover - source tree without installation
    __version__ = "0.0.0"

__all__ = ["__version__"]
