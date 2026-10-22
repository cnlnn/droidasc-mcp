"""MCP adapter for the Droid ASC Android decompiler."""

__all__ = ["__version__"]


def __getattr__(name):
    if name != "__version__":
        raise AttributeError(name)
    from importlib.metadata import PackageNotFoundError, version

    try:
        value = version("droidasc-mcp")
    except PackageNotFoundError:  # pragma: no cover - source tree without installation
        value = "0.0.0"
    globals()[name] = value
    return value
