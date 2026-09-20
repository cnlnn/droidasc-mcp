# Contributing

1. Create a virtual environment with `uv sync --locked --extra dev`.
2. Run `uv run ruff check .`.
3. Run `uv run pytest`.
4. Keep MCP responses bounded and structured. Do not add a generic shell or arbitrary CLI tool.
5. Do not commit APK fixtures unless their redistribution rights and provenance are documented.
6. Build with `uv build`, then run `scripts/verify_dist.py` against the matching sdist and wheel
   using Python 3.12+ before publishing a release.
