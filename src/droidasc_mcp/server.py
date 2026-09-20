"""MCP server entry point."""

from __future__ import annotations

import argparse
from typing import Literal

from mcp.server import MCPServer

from .config import Settings
from .service import DroidAscService


def build_server(settings: Settings | None = None) -> MCPServer:
    service = DroidAscService(settings or Settings.from_env())
    mcp = MCPServer("droidasc-mcp")

    @mcp.tool()
    def asc_ping() -> dict[str, object]:
        """Report server, engine, path-scope, and pagination configuration."""
        return service.ping()

    @mcp.tool()
    def asc_apk_info(apk_path: str, include_sha256: bool = True) -> dict[str, object]:
        """Inspect APK size, SHA-256, manifest presence, and top-level DEX entries."""
        return service.apk_info(apk_path, include_sha256=include_sha256)

    @mcp.tool()
    def asc_get_manifest(apk_path: str, offset: int = 0, limit: int = 500) -> dict[str, object]:
        """Decode AndroidManifest.xml and return a bounded page of XML lines."""
        return service.get_manifest(apk_path, offset=offset, limit=limit)

    @mcp.tool()
    def asc_list_classes(
        apk_path: str,
        prefix: str | None = None,
        threads: int = 8,
        offset: int = 0,
        limit: int = 200,
    ) -> dict[str, object]:
        """List class descriptors, optionally filtered by package or class prefix."""
        return service.list_classes(
            apk_path,
            prefix=prefix,
            threads=threads,
            offset=offset,
            limit=limit,
        )

    @mcp.tool()
    def asc_get_class_source(
        apk_path: str,
        class_name: str,
        threads: int = 8,
        offset: int = 0,
        limit: int = 500,
    ) -> dict[str, object]:
        """Locate and decompile one class, returning a bounded page of source lines."""
        return service.get_class_source(
            apk_path,
            class_name=class_name,
            threads=threads,
            offset=offset,
            limit=limit,
        )

    @mcp.tool()
    def asc_find_refs(
        apk_path: str,
        kind: Literal["string", "type", "method", "field"],
        value: str | None = None,
        class_name: str | None = None,
        fuzzy_class: bool = False,
        threads: int = 8,
        offset: int = 0,
        limit: int = 200,
    ) -> dict[str, object]:
        """Find cross-DEX references to a string, type, method, or field."""
        return service.find_refs(
            apk_path,
            kind=kind,
            value=value,
            class_name=class_name,
            fuzzy_class=fuzzy_class,
            threads=threads,
            offset=offset,
            limit=limit,
        )

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP server for the Droid ASC APK decompiler")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="HTTP bind address")
    parser.add_argument("--port", type=int, default=8000, help="HTTP bind port")
    args = parser.parse_args()

    server = build_server()
    if args.transport == "stdio":
        server.run()
    else:
        server.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
