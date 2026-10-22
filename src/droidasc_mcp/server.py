"""MCP server entry point."""

from __future__ import annotations

import argparse
from contextlib import asynccontextmanager
from typing import Annotated, Literal

import anyio
from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from .config import Settings
from .contracts import (
    ApkInfoResult,
    ArchiveResult,
    ArtifactResult,
    DexResult,
    DiffResult,
    LegacyResult,
    ManifestResult,
    PingResult,
    SecretResult,
    SigningResult,
)
from .runner import PREPARATION_PROGRESS, DroidAscRunner
from .service import DroidAscService
from .tool_registry import ToolRegistry
from .workflows import INSTRUCTIONS, register_workflows

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
SESSION_STATE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)

ApkPath = Annotated[str, Field(description="APK file path within configured allowed roots")]
DexPaths = Annotated[
    list[str],
    Field(
        min_length=1,
        max_length=64,
        description="Ordered standard DEX file paths; combined bytes are server-bounded",
    ),
]
SessionId = Annotated[
    str, Field(description="Immutable open DEX session ID returned by an open tool")
]
ClassName = Annotated[str, Field(description="Exact class descriptor or Java dotted class name")]
OptionalClass = Annotated[
    str | None,
    Field(description="Exact owner class; for legacy fuzzy references, a literal owner substring"),
]
Prefix = Annotated[str | None, Field(description="Literal class/package prefix, case-sensitive")]
MethodId = Annotated[
    str | None,
    Field(description="Full method identity: Lpkg/C;->name(args)return; preserves overloads"),
]
FieldId = Annotated[str | None, Field(description="Full field identity: Lpkg/C;->name:type")]
TypeId = Annotated[
    str | None, Field(description="Exact DEX type including array dimensions, for find_type_refs")
]
Value = Annotated[
    str | None,
    Field(description="Literal value (classes: Dalvik or dotted); exact extends/impl parent"),
]
FuzzyClass = Annotated[
    bool, Field(description="Legacy owner substring matching; exact member tools require false")
]
Threads = Annotated[
    int, Field(description="Positive ASC worker count; requested values above 32 are capped")
]
Offset = Annotated[
    int, Field(description="Zero-based result offset; graph traversal requires zero")
]
Limit = Annotated[
    int, Field(description="Positive result page size in rows or source lines, server-capped")
]
Backend = Annotated[
    Literal["droidasc", "rust_asc"],
    Field(description="Engine; rust_asc is opt-in and reports unverified coverage"),
]
FieldAccess = Annotated[
    Literal["all", "read", "write"],
    Field(description="Instruction field-access filter, for find_field_refs"),
]
TypeRelation = Annotated[
    Literal["all", "instruction", "declaration", "annotation"],
    Field(description="Static type relation filter applied before pagination"),
]
SourceFormat = Annotated[
    Literal["auto", "java", "smali"],
    Field(description="Exact method source; auto has explicit fallback diagnostics"),
]
DebugInfo = Annotated[
    bool, Field(description="Include debug line/local metadata for explicit method Smali only")
]
ReferenceKind = Annotated[
    Literal["string", "type", "method", "field", "extends", "impl"],
    Field(description="Reference category; search_members accepts method or field only"),
]
CaseSensitive = Annotated[
    bool, Field(description="Literal discovery matching case; false ignores case")
]
MemberMatch = Annotated[
    Literal["descriptor", "name", "exact_name", "prototype"],
    Field(
        description="Literal identity or name; search_refs also accepts exact_name and prototype"
    ),
]


def build_server(
    settings: Settings | None = None,
    runner: DroidAscRunner | None = None,
    *,
    registry: ToolRegistry | None = None,
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

    registry = registry or ToolRegistry()

    @registry.tool(annotations=READ_ONLY)
    def asc_ping() -> PingResult:
        """Report server, engine, path-scope, and pagination configuration."""
        return service.ping()

    @registry.tool(annotations=READ_ONLY)
    def asc_signing_inventory(
        apk_path: Annotated[str, Field(description="APK path within configured allowed roots")],
    ) -> SigningResult:
        """Inventory v1/v2/v3 containers and certificate fingerprints; detect v3.1 block presence.

        Container presence is independent of cryptographic validity. APK digests, signatures,
        trust, rotation lineage and v4 sidecars remain unverified. Malformed containers produce
        explicit diagnostics. v1 certificates are a PKCS7 bag, not resolved signer identities.
        """
        return service.query_archive(apk_path, operation="signing_inventory")

    @registry.tool(annotations=READ_ONLY)
    def asc_inspect_artifact(
        artifact_path: Annotated[
            str, Field(description="APK/JAR/AAR/AAB/APKS/XAPK/ZIP path within allowed roots")
        ],
        module: Annotated[
            str | None,
            Field(description="Exact AAB module; omitted selects base, other formats omit"),
        ] = None,
        max_uncompressed_bytes: Annotated[
            int,
            Field(
                ge=1,
                le=2147483648,
                description="Nested classes.jar byte budget; server input limit also applies",
            ),
        ] = 134217728,
        offset: Annotated[
            int, Field(ge=0, description="Zero-based offset in sorted capability entries")
        ] = 0,
        limit: Annotated[
            int, Field(ge=1, le=1000, description="Entry page size, server-capped")
        ] = 100,
        compare_to: Annotated[
            str | None,
            Field(description="Optional newer artifact for JVM class inventory comparison"),
        ] = None,
        class_query: Annotated[
            str | None, Field(description="Case-insensitive literal substring of JVM class names")
        ] = None,
        class_prefix: Annotated[
            str | None, Field(description="JVM class prefix in dotted or Dalvik form")
        ] = None,
    ) -> ArtifactResult:
        """Inspect container capabilities before selecting a DEX analysis workflow.

        JVM classes and nested APK splits are inventory-only. First-level JAR class names
        are included. compare_to compares JVM identities; DEX declarations use session diff.
        AAB selects one module's direct DEX; nested APKs are not reconstructed.
        """
        return service.inspect_artifact(
            artifact_path,
            module=module,
            max_uncompressed_bytes=max_uncompressed_bytes,
            offset=offset,
            limit=limit,
            compare_to=compare_to,
            class_query=class_query,
            class_prefix=class_prefix,
        )

    @registry.tool(annotations=SESSION_STATE)
    def asc_open_artifact_session(
        artifact_path: Annotated[
            str, Field(description="APK/JAR/AAR/AAB/APKS/XAPK/ZIP input within allowed roots")
        ],
        ctx: Context = None,
        module: Annotated[
            str | None, Field(description="Exact AAB module; omitted selects base")
        ] = None,
        max_uncompressed_bytes: Annotated[
            int,
            Field(
                ge=1,
                le=2147483648,
                description="Expanded JAR/DEX bytes; disk reservation scales with this budget",
            ),
        ] = 134217728,
    ) -> DexResult:
        """Snapshot selected direct DEX into an immutable reusable session with container hashes.

        Direct DEX at arbitrary archive paths, AAR classes.jar DEX and one AAB module
        are supported. Pure JVM
        classes and nested split APKs stay inventory-only. Duplicate classes are rejected.
        Query and close the resulting ID with the existing DEX session tools.
        """
        token = PREPARATION_PROGRESS.set(
            (
                lambda completed, total, message: anyio.from_thread.run(
                    ctx.report_progress, completed, total, message
                )
            )
            if ctx is not None
            else None
        )
        try:
            return service.open_artifact_session(
                artifact_path, module=module, max_uncompressed_bytes=max_uncompressed_bytes
            )
        finally:
            PREPARATION_PROGRESS.reset(token)

    @registry.tool(annotations=SESSION_STATE)
    def asc_diff_dex_sessions(
        old_session_id: Annotated[str, Field(description="Open immutable baseline session ID")],
        new_session_id: Annotated[
            str, Field(description="Open immutable candidate revision session ID")
        ],
        kind: Annotated[
            Literal["all", "class", "method", "field"],
            Field(description="Declaration identity kind to compare"),
        ] = "all",
        change: Annotated[
            Literal["all", "added", "removed"],
            Field(description="Change filter applied before paging"),
        ] = "all",
        offset: Annotated[
            int, Field(ge=0, description="Zero-based offset in sorted changed descriptors")
        ] = 0,
        limit: Annotated[
            int, Field(ge=1, le=1000, description="Changed declaration page size, server-capped")
        ] = 100,
    ) -> DiffResult:
        """Compare class/member identities with full descriptors and old/new source hashes.

        Uses native DEX declarations without Java or an instruction index. Unchanged
        identities say nothing about changed behavior, access flags, annotations or bodies.
        Inventory is bounded to 1M identities and 64 MiB of cumulative declaration records.
        """
        return service.diff_dex_sessions(
            old_session_id, new_session_id, kind=kind, change=change, offset=offset, limit=limit
        )

    @registry.tool(annotations=SESSION_STATE)
    def asc_secret_candidates(
        session_id: Annotated[str, Field(description="Open immutable DEX or artifact session ID")],
        pattern: Annotated[
            Literal[
                "all",
                "aws_access_key_id",
                "github_classic_token",
                "google_api_key",
                "private_key_marker",
                "credential_assignment",
                "jwt_like",
            ],
            Field(description="Fixed candidate pattern family, not arbitrary regex"),
        ] = "all",
        include_values: Annotated[
            bool, Field(description="Explicit opt-in to return sensitive matched candidate values")
        ] = False,
        max_scan_bytes: Annotated[
            int,
            Field(
                ge=1, le=268435456, description="Cumulative decoded UTF-8 string-pool byte budget"
            ),
        ] = 67108864,
        offset: Annotated[
            int, Field(ge=0, description="Zero-based candidate offset in DEX/string/pattern order")
        ] = 0,
        limit: Annotated[
            int, Field(ge=1, le=1000, description="Redacted candidate page size, server-capped")
        ] = 100,
    ) -> SecretResult:
        """Find redacted candidate secrets in DEX strings with exact pool indices and fingerprints.

        Uses native DEX string pools without Java/JADX.
        Values are redacted unless include_values=true.
        Candidate validity and instruction use sites remain untested. Strings over 64K UTF-16
        units are skipped explicitly; per-pattern/string matches cap at 20, total strings at 2M.
        Assets, native code, runtime values and arbitrary encodings are outside this scan.
        """
        return service.secret_candidates(
            session_id,
            pattern=pattern,
            max_scan_bytes=max_scan_bytes,
            offset=offset,
            limit=limit,
            include_values=include_values,
        )

    @registry.tool(annotations=READ_ONLY)
    def asc_apk_info(
        apk_path: ApkPath,
        include_sha256: Annotated[
            bool, Field(description="Compute a full input SHA-256 when true")
        ] = True,
    ) -> ApkInfoResult:
        """Inspect APK size, SHA-256, manifest presence, and top-level DEX entries."""
        return service.apk_info(apk_path, include_sha256=include_sha256)

    @registry.tool(annotations=READ_ONLY)
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
    ) -> ArchiveResult:
        """List APK contents, sizes, CRC metadata and native ABIs without extracting files.

        SHA-256 binds this page to the APK. CRC values here are declarations, not verification.
        Native rows are an archive inventory, not ELF analysis. Follow next_offset for more.
        """
        return service.query_archive(
            apk_path, operation="list_entries", kind=kind, prefix=prefix, offset=offset, limit=limit
        )

    @registry.tool(annotations=READ_ONLY)
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
        byte_offset: Annotated[
            int,
            Field(
                ge=0,
                description="Byte offset in raw or fully decoded content; follow next_byte_offset",
            ),
        ] = 0,
    ) -> ArchiveResult:
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
            byte_offset=byte_offset,
        )

    @registry.tool(annotations=READ_ONLY)
    def asc_manifest_summary(
        apk_path: Annotated[str, Field(description="APK path within the configured allowed roots")],
        offset: Annotated[
            int, Field(ge=0, description="Zero-based component offset in manifest order")
        ] = 0,
        limit: Annotated[
            int, Field(ge=1, le=1000, description="Component page size, server-capped")
        ] = 100,
    ) -> ManifestResult:
        """Read structured Manifest components, filters, metadata and permission inheritance.

        Raw declarations are preserved separately. Unspecified exported defaults and resource
        values remain unresolved. Provider path rules and URI grants need separate review;
        permission inheritance is static triage, not a runtime accessibility or vulnerability test.
        """
        return service.query_archive(
            apk_path, operation="manifest_summary", offset=offset, limit=limit
        )

    @registry.tool(annotations=READ_ONLY)
    def asc_get_manifest(
        apk_path: ApkPath,
        offset: Offset = 0,
        limit: Limit = 500,
        backend: Backend = "droidasc",
    ) -> LegacyResult:
        """Decode AndroidManifest.xml and return a bounded page of XML lines."""
        return service.get_manifest(apk_path, offset=offset, limit=limit, backend=backend)

    @registry.tool(annotations=READ_ONLY)
    def asc_list_classes(
        apk_path: ApkPath,
        prefix: Prefix = None,
        threads: Threads = 8,
        offset: Offset = 0,
        limit: Limit = 200,
        backend: Backend = "droidasc",
    ) -> LegacyResult:
        """List class descriptors, optionally filtered by package or class prefix."""
        return service.list_classes(
            apk_path,
            prefix=prefix,
            backend=backend,
            threads=threads,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def asc_get_class_source(
        apk_path: ApkPath,
        class_name: ClassName,
        threads: Threads = 8,
        offset: Offset = 0,
        limit: Limit = 500,
        backend: Backend = "droidasc",
    ) -> LegacyResult:
        """Locate and decompile one class, returning a bounded page of source lines."""
        return service.get_class_source(
            apk_path,
            class_name=class_name,
            backend=backend,
            threads=threads,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def asc_find_refs(
        apk_path: ApkPath,
        kind: ReferenceKind,
        value: Value = None,
        class_name: OptionalClass = None,
        fuzzy_class: FuzzyClass = False,
        threads: Threads = 8,
        offset: Offset = 0,
        limit: Limit = 200,
        backend: Backend = "droidasc",
    ) -> LegacyResult:
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

    @registry.tool(annotations=READ_ONLY)
    def asc_analyze_dex(
        dex_paths: DexPaths,
        operation: Annotated[
            Literal[
                "info",
                "list_classes",
                "get_class_source",
                "find_refs",
                "get_manifest",
                "list_methods",
                "get_method_source",
                "find_method_refs",
                "get_method_calls",
                "get_call_graph",
                "find_field_refs",
                "search_refs",
                "find_type_refs",
                "build_xref_index",
                "search_members",
                "search_strings",
                "search_classes",
                "get_class_outline",
                "get_class_hierarchy",
                "get_string_constants",
                "search_method_bodies",
                "disassemble_method",
                "get_class_source_metadata",
            ],
            Field(
                description="Static DEX operation; exact member/graph tools need full descriptors"
            ),
        ] = "info",
        prefix: Prefix = None,
        class_name: OptionalClass = None,
        method_descriptor: MethodId = None,
        field_descriptor: FieldId = None,
        field_access: FieldAccess = "all",
        type_descriptor: TypeId = None,
        type_relation: TypeRelation = "all",
        source_format: SourceFormat = "auto",
        debug_info: DebugInfo = False,
        kind: ReferenceKind = "string",
        value: Value = None,
        case_sensitive: CaseSensitive = True,
        member_match: MemberMatch = "descriptor",
        target_descriptor: Annotated[
            str | None, Field(description="search_refs exact prototype or field-type filter")
        ] = None,
        fuzzy_class: FuzzyClass = False,
        threads: Threads = 8,
        offset: Offset = 0,
        limit: Limit = 200,
        direction: Annotated[
            Literal["incoming", "outgoing", "both"],
            Field(description="Graph direction; edges retain caller-to-callee orientation."),
        ] = "both",
        depth: Annotated[
            int,
            Field(
                ge=1,
                le=5,
                description="Graph hop bound; first use builds a calls-only index.",
            ),
        ] = 2,
        max_nodes: Annotated[
            int, Field(ge=1, le=500, description="Call-graph node budget including the root.")
        ] = 200,
        max_edges: Annotated[
            int,
            Field(
                ge=1,
                le=1000,
                description="Graph call-site budget; repeated calls remain separate edges.",
            ),
        ] = 500,
    ) -> DexResult:
        """Analyze 1-64 standard DEX files with source hashes and per-DEX provenance.

        Returns status=ok, error, or not_applicable. Errors carry a diagnostic code;
        duplicate class definitions are rejected. Manifest is not applicable to DEX.
        Coverage is limited to supplied files; this tool does not unpack applications.
        Native instruction/declaration queries need no JVM or JADX; Smali uses ASC.
        Explicit source_format=java alone selects the optional compatibility backend.
        find_method_refs/get_method_calls return declared instruction targets, not runtime dispatch.
        Use a full method_descriptor, e.g. Lpkg/C;->name(I)Ljava/lang/String;.
        find_field_refs requires field_descriptor (Lpkg/C;->name:I).
        field_access filters reads/writes; inheritance and reflective accesses are not resolved.
        find_type_refs reports exact type operands, declarations and annotation types/values.
        build_xref_index builds a bounded complete static index; one-shot indexes are temporary.
        get_call_graph builds/reuses the index for bounded multi-hop static exploration.
        Graph depth/node/edge/byte boundaries and unresolved dynamic sites are explicit.
        search_members scans declarations without building an index; kind=method/field.
        value is a case-sensitive literal substring of the full descriptor, not regex.
        class_name restricts exact owner. search_strings scans DEX string-pool values
        using a case-sensitive literal value, not instruction use sites.
        source_format=auto uses ASC exact-method Smali without Java/JADX;
        source_format=java explicitly opts into the optional JADX compatibility backend.
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
            case_sensitive=case_sensitive,
            member_match=member_match,
            target_descriptor=target_descriptor,
            fuzzy_class=fuzzy_class,
            threads=threads,
            offset=offset,
            limit=limit,
            direction=direction,
            depth=depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )

    @registry.tool(annotations=SESSION_STATE)
    def asc_open_dex_session(dex_paths: DexPaths, ctx: Context = None) -> DexResult:
        """Validate and snapshot DEX inputs once; return an immutable hash-bound session.

        Reuses the validated bundle, not a resident engine. Idle sessions expire and may
        be evicted at capacity. Source file changes require opening a new session.
        """
        token = PREPARATION_PROGRESS.set(
            (
                lambda completed, total, message: anyio.from_thread.run(
                    ctx.report_progress, completed, total, message
                )
            )
            if ctx is not None
            else None
        )
        try:
            return service.open_dex_session(dex_paths)
        finally:
            PREPARATION_PROGRESS.reset(token)

    @registry.tool(annotations=SESSION_STATE)
    def asc_close_dex_session(session_id: SessionId) -> DexResult:
        """Close a DEX session; active queries finish before its stored files are removed."""
        return service.sessions.close(session_id)

    @registry.tool(annotations=SESSION_STATE)
    def asc_query_dex_session(
        session_id: SessionId,
        operation: Annotated[
            Literal[
                "info",
                "list_classes",
                "get_class_source",
                "find_refs",
                "get_manifest",
                "list_methods",
                "get_method_source",
                "find_method_refs",
                "get_method_calls",
                "get_call_graph",
                "find_field_refs",
                "search_refs",
                "find_type_refs",
                "build_xref_index",
                "search_members",
                "search_strings",
                "search_classes",
                "get_class_outline",
                "get_class_hierarchy",
                "get_string_constants",
                "search_method_bodies",
                "disassemble_method",
                "get_class_source_metadata",
            ],
            Field(description="Session operation; first indexed graph/type query builds the index"),
        ] = "info",
        prefix: Prefix = None,
        class_name: OptionalClass = None,
        method_descriptor: MethodId = None,
        field_descriptor: FieldId = None,
        field_access: FieldAccess = "all",
        type_descriptor: TypeId = None,
        type_relation: TypeRelation = "all",
        source_format: SourceFormat = "auto",
        debug_info: DebugInfo = False,
        kind: ReferenceKind = "string",
        value: Value = None,
        case_sensitive: CaseSensitive = True,
        member_match: MemberMatch = "descriptor",
        target_descriptor: Annotated[
            str | None, Field(description="search_refs exact prototype or field-type filter")
        ] = None,
        fuzzy_class: FuzzyClass = False,
        threads: Threads = 8,
        offset: Offset = 0,
        limit: Limit = 200,
        direction: Annotated[
            Literal["incoming", "outgoing", "both"],
            Field(description="Graph direction; edges retain caller-to-callee orientation."),
        ] = "both",
        depth: Annotated[
            int,
            Field(
                ge=1,
                le=5,
                description="Hop bound; first use builds a calls-only index, then reuses it.",
            ),
        ] = 2,
        max_nodes: Annotated[
            int, Field(ge=1, le=500, description="Call-graph node budget including the root.")
        ] = 200,
        max_edges: Annotated[
            int,
            Field(
                ge=1,
                le=1000,
                description="Graph call-site budget; repeated calls remain separate edges.",
            ),
        ] = 500,
    ) -> DexResult:
        """Query an immutable DEX session in a supervised worker, with original provenance.

        Native instruction/declaration queries need no JVM or JADX; Smali uses ASC.
        search_refs combines literal owner/name/prototype filters without global preprocessing.
        target_descriptor optionally filters exact prototypes/field types.
        find_method_refs/get_method_calls return declared instruction targets, not runtime dispatch.
        method_descriptor is the full DEX class->name(args)return identity.
        find_field_refs requires field_descriptor (Lpkg/C;->name:I).
        field_access filters reads/writes; inheritance and reflective accesses are not resolved.
        build_xref_index persists an atomic static index for this session's lifetime.
        get_call_graph builds/reuses it for bounded multi-hop static exploration.
        Inspect truncation_reasons and unresolved_sites; graph edges are declared operands.
        An optional configured durable cache restores matching indexes across server restarts.
        find_type_refs builds/reuses that index; subsequent method/field queries also reuse it.
        type_descriptor is exact (including arrays); type_relation filters before pagination.
        search_members scans declarations or reuses an existing index; kind=method/field.
        value is a case-sensitive literal substring of the full descriptor, not regex.
        class_name restricts exact owner. search_strings scans DEX string-pool values
        using a case-sensitive literal value, not instruction use sites.
        Identical discovery and non-indexed reference pages reuse a bounded session cache.
        source_format=auto uses ASC exact-method Smali, never JADX.
        source_format=java explicitly selects the optional compatibility backend.
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
            case_sensitive=case_sensitive,
            member_match=member_match,
            target_descriptor=target_descriptor,
            fuzzy_class=fuzzy_class,
            threads=threads,
            offset=offset,
            limit=limit,
            direction=direction,
            depth=depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )

    mcp = MCPServer(
        "droidasc-mcp", lifespan=lifespan, instructions=INSTRUCTIONS, tools=registry.tools
    )
    register_workflows(mcp, service)
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
