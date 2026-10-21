"""MCP server entry point."""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from typing import Literal

import anyio
from mcp.server import MCPServer

from .config import Settings
from .runner import DroidAscRunner
from .service import DroidAscService


def build_server(
    settings: Settings | None = None, runner: DroidAscRunner | None = None
) -> MCPServer:
    settings = settings or Settings.from_env()
    service = DroidAscService(settings, runner)

    @asynccontextmanager
    async def lifespan(server):
        try:
            yield
        finally:
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(service.close)

    mcp = MCPServer("droidasc-mcp", lifespan=lifespan)

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
        kind: Literal["string", "type", "method", "field", "extends", "impl"],
        value: str | None = None,
        class_name: str | None = None,
        fuzzy_class: bool = False,
        threads: int = 8,
        offset: int = 0,
        limit: int = 200,
    ) -> dict[str, object]:
        """Find cross-DEX references or direct subclasses/interface implementors.

        extends/impl use an exact class in value and return direct declarations only.
        """
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

    @mcp.tool()
    def asc_analyze_dex(
        dex_paths: list[str],
        operation: Literal[
            "info",
            "list_classes",
            "get_class_source",
            "find_refs",
            "get_manifest",
            "list_methods",
            "get_method_source",
            "find_method_refs",
            "get_method_calls",
        ] = "info",
        prefix: str | None = None,
        class_name: str | None = None,
        method_descriptor: str | None = None,
        source_format: Literal["auto", "java", "smali"] = "auto",
        debug_info: bool = False,
        kind: Literal["string", "type", "method", "field", "extends", "impl"] = "string",
        value: str | None = None,
        fuzzy_class: bool = False,
        threads: int = 8,
        offset: int = 0,
        limit: int = 200,
    ) -> dict[str, object]:
        """Analyze 1-64 standard DEX files with source hashes and per-DEX provenance.

        Returns status=ok, error, or not_applicable. Errors carry a diagnostic code;
        duplicate class definitions are rejected. Manifest is not applicable to DEX.
        Coverage is limited to supplied files; this tool does not unpack applications.
        Java, method lists and exact instruction references use optional JADX 1.5.5/JDK 17+.
        Explicit smali uses ASC; debug_info includes DEX line/local metadata.
        find_method_refs/get_method_calls return declared instruction targets, not runtime dispatch.
        Use a full method_descriptor, e.g. Lpkg/C;->name(I)Ljava/lang/String;.
        source_format=auto returns Java or exact-method Smali with fell_back/reason;
        java never silently falls back, smali always disassembles that exact method.
        """
        return service.analyze_dex(
            dex_paths,
            operation=operation,
            prefix=prefix,
            class_name=class_name,
            method_descriptor=method_descriptor,
            source_format=source_format,
            debug_info=debug_info,
            kind=kind,
            value=value,
            fuzzy_class=fuzzy_class,
            threads=threads,
            offset=offset,
            limit=limit,
        )

    @mcp.tool()
    def asc_open_dex_session(dex_paths: list[str]) -> dict[str, object]:
        """Validate and snapshot DEX inputs once; return an immutable hash-bound session.

        Reuses the validated bundle, not a resident engine. Idle sessions expire and may
        be evicted at capacity. Source file changes require opening a new session.
        """
        return service.open_dex_session(dex_paths)

    @mcp.tool()
    def asc_close_dex_session(session_id: str) -> dict[str, object]:
        """Close a DEX session; active queries finish before its stored files are removed."""
        return service.sessions.close(session_id)

    @mcp.tool()
    def asc_query_dex_session(
        session_id: str,
        operation: Literal[
            "info",
            "list_classes",
            "get_class_source",
            "find_refs",
            "get_manifest",
            "list_methods",
            "get_method_source",
            "find_method_refs",
            "get_method_calls",
        ] = "info",
        prefix: str | None = None,
        class_name: str | None = None,
        method_descriptor: str | None = None,
        source_format: Literal["auto", "java", "smali"] = "auto",
        debug_info: bool = False,
        kind: Literal["string", "type", "method", "field", "extends", "impl"] = "string",
        value: str | None = None,
        fuzzy_class: bool = False,
        threads: int = 8,
        offset: int = 0,
        limit: int = 200,
    ) -> dict[str, object]:
        """Query an immutable DEX session in a supervised worker, with original provenance.

        Java, method lists and exact instruction references use optional JADX 1.5.5/JDK 17+.
        Explicit smali uses ASC; debug_info includes DEX line/local metadata.
        find_method_refs/get_method_calls return declared instruction targets, not runtime dispatch.
        method_descriptor is the full DEX class->name(args)return identity.
        source_format=auto may return exact-method Smali with an explicit fallback reason.
        """
        return service.query_dex_session(
            session_id,
            operation=operation,
            prefix=prefix,
            class_name=class_name,
            method_descriptor=method_descriptor,
            source_format=source_format,
            debug_info=debug_info,
            kind=kind,
            value=value,
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
