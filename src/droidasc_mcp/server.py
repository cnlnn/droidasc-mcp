"""MCP server entry point."""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import anyio
from mcp.server import MCPServer
from mcp.types import ToolAnnotations
from pydantic import Field

from .config import Settings
from .runner import DroidAscRunner
from .service import DroidAscService
from .workflows import INSTRUCTIONS, register_workflows

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
SESSION_STATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)


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

    mcp = MCPServer("droidasc-mcp", lifespan=lifespan, instructions=INSTRUCTIONS)
    register_workflows(mcp)

    @mcp.tool(annotations=READ_ONLY)
    def asc_ping() -> dict[str, object]:
        """Report server, engine, path-scope, and pagination configuration."""
        return service.ping()

    @mcp.tool(annotations=READ_ONLY)
    def asc_apk_info(apk_path: str, include_sha256: bool = True) -> dict[str, object]:
        """Inspect APK size, SHA-256, manifest presence, and top-level DEX entries."""
        return service.apk_info(apk_path, include_sha256=include_sha256)

    @mcp.tool(annotations=READ_ONLY)
    def asc_list_apk_entries(
        apk_path: Annotated[str, Field(description="APK path within the configured allowed roots")],
        kind: Annotated[
            Literal["manifest", "resource", "asset", "native", "dex", "metadata", "other"] | None,
            Field(description="Entry category; omit for all file entries"),
        ] = None,
        prefix: Annotated[
            str | None, Field(description="Case-sensitive literal ZIP path prefix")
        ] = None,
        offset: Annotated[
            int, Field(ge=0, description="Zero-based offset in sorted filtered entries")
        ] = 0,
        limit: Annotated[
            int, Field(ge=1, le=1000, description="Page size, capped by server limits")
        ] = 100,
    ) -> dict[str, object]:
        """List APK contents, sizes, CRC metadata and native ABIs without extracting files.

        SHA-256 binds this page to the APK. CRC values here are declarations, not verification.
        Native rows are an archive inventory, not ELF analysis. Follow next_offset for more.
        """
        return service.query_archive(
            apk_path, operation="list_entries", kind=kind, prefix=prefix, offset=offset, limit=limit
        )

    @mcp.tool(annotations=READ_ONLY)
    def asc_read_apk_entry(
        apk_path: Annotated[str, Field(description="APK path within the configured allowed roots")],
        entry_path: Annotated[
            str, Field(description="Exact relative ZIP entry path from inventory")
        ],
        max_bytes: Annotated[
            int,
            Field(ge=1, le=131072, description="Maximum returned content bytes before encoding"),
        ] = 16384,
        decode_xml: Annotated[
            bool,
            Field(description="Decode complete XML entries up to 4 MiB; false reads raw bytes"),
        ] = True,
    ) -> dict[str, object]:
        """Read a bounded entry prefix as UTF-8 or base64, with APK hash and entry provenance.

        Binary XML decoding and returned-content truncation are separate statuses. Partial raw
        reads do not verify CRC. Resource IDs are not resolved; no filesystem extraction occurs.
        """
        return service.query_archive(
            apk_path,
            operation="read_entry",
            entry_path=entry_path,
            max_bytes=max_bytes,
            decode_xml=decode_xml,
        )

    @mcp.tool(annotations=READ_ONLY)
    def asc_manifest_summary(
        apk_path: Annotated[str, Field(description="APK path within the configured allowed roots")],
        offset: Annotated[
            int, Field(ge=0, description="Zero-based component offset in manifest order")
        ] = 0,
        limit: Annotated[
            int, Field(ge=1, le=1000, description="Component page size, server-capped")
        ] = 100,
    ) -> dict[str, object]:
        """Read structured Manifest components, filters, metadata and permission inheritance.

        Raw declarations are preserved separately. Unspecified exported defaults and resource
        values remain unresolved. Provider path rules and URI grants need separate review;
        permission inheritance is static triage, not a runtime accessibility or vulnerability test.
        """
        return service.query_archive(
            apk_path, operation="manifest_summary", offset=offset, limit=limit
        )

    @mcp.tool(annotations=READ_ONLY)
    def asc_get_manifest(
        apk_path: str,
        offset: int = 0,
        limit: int = 500,
        backend: Literal["droidasc", "rust_asc"] = "droidasc",
    ) -> dict[str, object]:
        """Decode AndroidManifest.xml and return a bounded page of XML lines."""
        return service.get_manifest(apk_path, offset=offset, limit=limit, backend=backend)

    @mcp.tool(annotations=READ_ONLY)
    def asc_list_classes(
        apk_path: str,
        prefix: str | None = None,
        threads: int = 8,
        offset: int = 0,
        limit: int = 200,
        backend: Literal["droidasc", "rust_asc"] = "droidasc",
    ) -> dict[str, object]:
        """List class descriptors, optionally filtered by package or class prefix."""
        return service.list_classes(
            apk_path,
            prefix=prefix,
            backend=backend,
            threads=threads,
            offset=offset,
            limit=limit,
        )

    @mcp.tool(annotations=READ_ONLY)
    def asc_get_class_source(
        apk_path: str,
        class_name: str,
        threads: int = 8,
        offset: int = 0,
        limit: int = 500,
        backend: Literal["droidasc", "rust_asc"] = "droidasc",
    ) -> dict[str, object]:
        """Locate and decompile one class, returning a bounded page of source lines."""
        return service.get_class_source(
            apk_path,
            class_name=class_name,
            backend=backend,
            threads=threads,
            offset=offset,
            limit=limit,
        )

    @mcp.tool(annotations=READ_ONLY)
    def asc_find_refs(
        apk_path: str,
        kind: Literal["string", "type", "method", "field", "extends", "impl"],
        value: str | None = None,
        class_name: str | None = None,
        fuzzy_class: bool = False,
        threads: int = 8,
        offset: int = 0,
        limit: int = 200,
        backend: Literal["droidasc", "rust_asc"] = "droidasc",
    ) -> dict[str, object]:
        """Find cross-DEX references or direct subclasses/interface implementors.

        extends/impl use an exact class in value and return direct declarations only.
        Optional rust_asc supports string/type/method/field only and has unverified coverage.
        """
        return service.find_refs(
            apk_path,
            kind=kind,
            backend=backend,
            value=value,
            class_name=class_name,
            fuzzy_class=fuzzy_class,
            threads=threads,
            offset=offset,
            limit=limit,
        )

    @mcp.tool(annotations=READ_ONLY)
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
            "find_field_refs",
            "find_type_refs",
            "build_xref_index",
            "search_members",
            "search_strings",
        ] = "info",
        prefix: str | None = None,
        class_name: str | None = None,
        method_descriptor: str | None = None,
        field_descriptor: str | None = None,
        field_access: Literal["all", "read", "write"] = "all",
        type_descriptor: str | None = None,
        type_relation: Literal["all", "instruction", "declaration", "annotation"] = "all",
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
        find_field_refs requires field_descriptor (Lpkg/C;->name:I).
        field_access filters reads/writes; inheritance and reflective accesses are not resolved.
        find_type_refs reports exact type operands, declarations and annotation types/values.
        build_xref_index builds a bounded complete static index; one-shot indexes are temporary.
        search_members scans declarations without building an index; kind=method/field.
        value is a case-sensitive literal substring of the full descriptor, not regex.
        class_name restricts exact owner. search_strings scans DEX string-pool values
        using a case-sensitive literal value, not instruction use sites.
        source_format=auto returns Java or exact-method Smali with fell_back/reason;
        java never silently falls back, smali always disassembles that exact method.
        """
        return service.analyze_dex(
            dex_paths,
            operation=operation,
            prefix=prefix,
            class_name=class_name,
            method_descriptor=method_descriptor,
            field_descriptor=field_descriptor,
            field_access=field_access,
            type_descriptor=type_descriptor,
            type_relation=type_relation,
            source_format=source_format,
            debug_info=debug_info,
            kind=kind,
            value=value,
            fuzzy_class=fuzzy_class,
            threads=threads,
            offset=offset,
            limit=limit,
        )

    @mcp.tool(annotations=SESSION_STATE)
    def asc_open_dex_session(dex_paths: list[str]) -> dict[str, object]:
        """Validate and snapshot DEX inputs once; return an immutable hash-bound session.

        Reuses the validated bundle, not a resident engine. Idle sessions expire and may
        be evicted at capacity. Source file changes require opening a new session.
        """
        return service.open_dex_session(dex_paths)

    @mcp.tool(annotations=SESSION_STATE)
    def asc_close_dex_session(session_id: str) -> dict[str, object]:
        """Close a DEX session; active queries finish before its stored files are removed."""
        return service.sessions.close(session_id)

    @mcp.tool(annotations=SESSION_STATE)
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
            "find_field_refs",
            "find_type_refs",
            "build_xref_index",
            "search_members",
            "search_strings",
        ] = "info",
        prefix: str | None = None,
        class_name: str | None = None,
        method_descriptor: str | None = None,
        field_descriptor: str | None = None,
        field_access: Literal["all", "read", "write"] = "all",
        type_descriptor: str | None = None,
        type_relation: Literal["all", "instruction", "declaration", "annotation"] = "all",
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
        find_field_refs requires field_descriptor (Lpkg/C;->name:I).
        field_access filters reads/writes; inheritance and reflective accesses are not resolved.
        build_xref_index persists an atomic static index for this session's lifetime.
        An optional configured durable cache restores matching indexes across server restarts.
        find_type_refs builds/reuses that index; subsequent method/field queries also reuse it.
        type_descriptor is exact (including arrays); type_relation filters before pagination.
        search_members scans declarations or reuses an existing index; kind=method/field.
        value is a case-sensitive literal substring of the full descriptor, not regex.
        class_name restricts exact owner. search_strings scans DEX string-pool values
        using a case-sensitive literal value, not instruction use sites.
        Identical discovery and non-indexed reference pages reuse a bounded session cache.
        source_format=auto may return exact-method Smali with an explicit fallback reason.
        """
        return service.query_dex_session(
            session_id,
            operation=operation,
            prefix=prefix,
            class_name=class_name,
            method_descriptor=method_descriptor,
            field_descriptor=field_descriptor,
            field_access=field_access,
            type_descriptor=type_descriptor,
            type_relation=type_relation,
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
