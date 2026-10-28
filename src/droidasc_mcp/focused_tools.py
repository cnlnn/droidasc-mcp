"""Handle-oriented DEX tools adapted from aimardcr/asc-mcp's server wrappers.

See NOTICE for the pinned source and interface adaptations. Execution remains owned
by the existing session service, including its bounds, caches and exact identities.
"""

from typing import Annotated, Literal

from mcp.types import ToolAnnotations
from pydantic import Field

from .contracts import (
    DexClassPage,
    DexGraphResult,
    DexIndexResult,
    DexInfoResult,
    DexInstructionPage,
    DexMemberPage,
    DexReferencePage,
    DexSourceResult,
)

AnalysisId = Annotated[str, Field(min_length=1, description="Handle returned by load_artifact")]
ClassName = Annotated[str, Field(description="Exact Dalvik descriptor or dotted class name")]
OptionalClass = Annotated[
    str | None, Field(description="Exact owner class, or omit for all owners")
]
MethodId = Annotated[
    str | None, Field(description="Full Lpkg/C;->name(args)return identity; preserves overloads")
]
MethodName = Annotated[
    str | None,
    Field(description="Exact declared name with class_name, instead of method_descriptor"),
]
Prototype = Annotated[
    str | None, Field(description="Exact (args)return prototype for an overloaded method_name")
]
Query = Annotated[str, Field(min_length=1, description="Nonempty literal substring")]
Offset = Annotated[int, Field(ge=0, description="Zero-based result row or source-line offset")]
Limit = Annotated[int, Field(ge=1, description="Maximum rows or source lines; server-capped")]
CaseSensitive = Annotated[bool, Field(description="Literal matching case; false ignores case")]
ReferenceFormat = Annotated[
    Literal["flat", "grouped"], Field(description="Flat use sites or bounded caller groups")
]
Cursor = Annotated[
    str | None,
    Field(
        min_length=1,
        max_length=1024,
        description="Grouped next_cursor for identical selectors; offset stays zero",
    ),
]
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


def register_focused_tools(registry, service):
    def run(analysis_id, operation, **query):
        return service.query_dex_session(
            analysis_id, **{"threads": 8, "offset": 0, "limit": 200, **query}, operation=operation
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_get_dex_info(analysis_id: AnalysisId) -> DexInfoResult:
        """Read prepared DEX identity, source hashes and coverage for this handle."""
        return run(analysis_id, "info")

    @registry.tool(annotations=READ_ONLY)
    def apk_list_classes(
        analysis_id: AnalysisId,
        prefix: Annotated[
            str | None, Field(description="Literal dotted or Dalvik class prefix")
        ] = None,
        query: Annotated[
            str | None, Field(min_length=1, description="Literal class-name substring")
        ] = None,
        case_sensitive: CaseSensitive = False,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexClassPage:
        """List exact class identities; query searches names without building an index."""
        if query is None:
            if prefix and not prefix.startswith("L"):
                prefix = "L" + prefix.replace(".", "/")
            return run(analysis_id, "list_classes", prefix=prefix, offset=offset, limit=limit)
        return run(
            analysis_id,
            "search_classes",
            prefix=prefix,
            value=query,
            case_sensitive=case_sensitive,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_get_class_source(
        analysis_id: AnalysisId, class_name: ClassName, offset: Offset = 0, limit: Limit = 200
    ) -> DexSourceResult:
        """Read paged ASC decompiled class text with original DEX provenance."""
        return run(
            analysis_id, "get_class_source", class_name=class_name, offset=offset, limit=limit
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_find_references(
        analysis_id: AnalysisId,
        value: Annotated[str, Field(min_length=1, description="Legacy CLI name/regex selector")],
        kind: Annotated[
            Literal["string", "type", "method", "field", "extends", "impl"],
            Field(description="Legacy CLI reference category"),
        ] = "string",
        class_name: OptionalClass = None,
        fuzzy_class: Annotated[bool, Field(description="Match literal owner substrings")] = False,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexReferencePage:
        """Search legacy CLI name/regex evidence; exact instruction tools are separate."""
        return run(
            analysis_id,
            "find_refs",
            value=value,
            kind=kind,
            class_name=class_name,
            fuzzy_class=fuzzy_class,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_get_dex_manifest(
        analysis_id: AnalysisId, offset: Offset = 0, limit: Limit = 200
    ) -> DexInfoResult:
        """Read the prepared DEX bundle manifest view; bare DEX reports not_applicable."""
        return run(analysis_id, "get_manifest", offset=offset, limit=limit)

    @registry.tool(annotations=READ_ONLY)
    def apk_list_methods(
        analysis_id: AnalysisId, class_name: ClassName, offset: Offset = 0, limit: Limit = 200
    ) -> DexMemberPage:
        """List declared full method identities for exact selection, preserving overloads."""
        return run(analysis_id, "list_methods", class_name=class_name, offset=offset, limit=limit)

    @registry.tool(annotations=READ_ONLY)
    def apk_get_method_source(
        analysis_id: AnalysisId,
        class_name: OptionalClass = None,
        method_name: MethodName = None,
        descriptor: Prototype = None,
        method_descriptor: MethodId = None,
        source_format: Annotated[
            Literal["auto", "smali", "java"],
            Field(description="auto/smali uses ASC without Java; java selects optional JADX"),
        ] = "auto",
        debug_info: Annotated[
            bool, Field(description="Include debug locals/lines for explicit smali")
        ] = False,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexSourceResult:
        """Read exact-method source; ambiguous names need a prototype. Java is opt-in."""
        return run(
            analysis_id,
            "get_method_source",
            class_name=class_name,
            method_name=method_name,
            target_descriptor=descriptor,
            method_descriptor=method_descriptor,
            source_format=source_format,
            debug_info=debug_info,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_find_method_references(
        analysis_id: AnalysisId,
        class_name: OptionalClass = None,
        method_name: MethodName = None,
        descriptor: Prototype = None,
        method_descriptor: MethodId = None,
        reference_format: ReferenceFormat = "flat",
        cursor: Cursor = None,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexReferencePage:
        """Find exact invoke sites; full identities also address external targets."""
        return run(
            analysis_id,
            "find_method_refs",
            class_name=class_name,
            method_name=method_name,
            target_descriptor=descriptor,
            method_descriptor=method_descriptor,
            reference_format=reference_format,
            cursor=cursor,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_get_method_calls(
        analysis_id: AnalysisId,
        class_name: OptionalClass = None,
        method_name: MethodName = None,
        descriptor: Prototype = None,
        method_descriptor: MethodId = None,
        reference_format: ReferenceFormat = "flat",
        cursor: Cursor = None,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexReferencePage:
        """Read one exact caller's declared invoke operands, not runtime dispatch."""
        return run(
            analysis_id,
            "get_method_calls",
            class_name=class_name,
            method_name=method_name,
            target_descriptor=descriptor,
            method_descriptor=method_descriptor,
            reference_format=reference_format,
            cursor=cursor,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_get_call_graph(
        analysis_id: AnalysisId,
        class_name: OptionalClass = None,
        method_name: MethodName = None,
        descriptor: Prototype = None,
        method_descriptor: MethodId = None,
        direction: Annotated[
            Literal["incoming", "outgoing", "both"], Field(description="Traversal direction")
        ] = "both",
        depth: Annotated[int, Field(ge=1, le=5, description="Maximum call-graph hops")] = 2,
        max_nodes: Annotated[
            int, Field(ge=1, le=500, description="Node budget including root")
        ] = 200,
        max_edges: Annotated[
            int, Field(ge=1, le=1000, description="Individual call-site budget")
        ] = 500,
    ) -> DexGraphResult:
        """Trace bounded static calls; inspect truncation_reasons and unresolved_sites."""
        return run(
            analysis_id,
            "get_call_graph",
            class_name=class_name,
            method_name=method_name,
            target_descriptor=descriptor,
            method_descriptor=method_descriptor,
            direction=direction,
            depth=depth,
            max_nodes=max_nodes,
            max_edges=max_edges,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_find_field_references(
        analysis_id: AnalysisId,
        field_descriptor: Annotated[str, Field(description="Full Lpkg/C;->name:type identity")],
        field_access: Annotated[
            Literal["all", "read", "write"], Field(description="Field access filter")
        ] = "all",
        reference_format: ReferenceFormat = "flat",
        cursor: Cursor = None,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexReferencePage:
        """Find exact instruction field accesses; inheritance/reflection remains unresolved."""
        return run(
            analysis_id,
            "find_field_refs",
            field_descriptor=field_descriptor,
            field_access=field_access,
            reference_format=reference_format,
            cursor=cursor,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_find_string_references(
        analysis_id: AnalysisId,
        value: Query,
        case_sensitive: CaseSensitive = True,
        reference_format: ReferenceFormat = "flat",
        cursor: Cursor = None,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexReferencePage:
        """Find literal const-string/jumbo use sites; pass discovered values unchanged."""
        return run(
            analysis_id,
            "find_string_refs",
            value=value,
            case_sensitive=case_sensitive,
            reference_format=reference_format,
            cursor=cursor,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_search_references(
        analysis_id: AnalysisId,
        kind: Annotated[
            Literal["method", "field"], Field(description="Instruction member category")
        ],
        value: Annotated[
            str | None, Field(min_length=1, description="Literal member identity/name substring")
        ] = None,
        class_name: Annotated[
            str | None, Field(description="Exact owner or fuzzy literal owner substring")
        ] = None,
        fuzzy_class: Annotated[
            bool, Field(description="Use literal owner substring matching")
        ] = False,
        member_match: Annotated[
            Literal["descriptor", "name", "exact_name", "prototype"],
            Field(description="Match identity, name, exact name or method prototype"),
        ] = "descriptor",
        target_descriptor: Annotated[
            str | None, Field(description="Exact method prototype or field type")
        ] = None,
        case_sensitive: CaseSensitive = True,
        field_access: Annotated[
            Literal["all", "read", "write"], Field(description="Field access filter")
        ] = "all",
        reference_format: ReferenceFormat = "flat",
        cursor: Cursor = None,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexReferencePage:
        """Find partial/fuzzy member targets in one pass; supply value or class_name."""
        return run(
            analysis_id,
            "search_refs",
            kind=kind,
            value=value,
            class_name=class_name,
            fuzzy_class=fuzzy_class,
            member_match=member_match,
            target_descriptor=target_descriptor,
            case_sensitive=case_sensitive,
            field_access=field_access,
            reference_format=reference_format,
            cursor=cursor,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_find_type_references(
        analysis_id: AnalysisId,
        type_descriptor: Annotated[
            str, Field(min_length=1, description="Exact DEX type; arrays retain dimensions")
        ],
        type_relation: Annotated[
            Literal["all", "instruction", "declaration", "annotation", "operand"],
            Field(
                description="instruction includes member/catch types; operand selects type operands"
            ),
        ] = "all",
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexReferencePage:
        """Find exact static type relations; non-operand scopes build/reuse a bounded index."""
        return run(
            analysis_id,
            "find_type_refs",
            type_descriptor=type_descriptor,
            type_relation=type_relation,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_find_type_instructions(
        analysis_id: AnalysisId,
        type_name: Annotated[
            str, Field(min_length=1, description="Dotted/Dalvik literal type operand selector")
        ],
        type_match: Annotated[
            Literal["substring", "exact"], Field(description="Case-sensitive literal matching")
        ] = "substring",
        reference_format: ReferenceFormat = "flat",
        cursor: Cursor = None,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexReferencePage:
        """Find explicit instruction type operands without building a full index."""
        return run(
            analysis_id,
            "find_type_refs",
            type_descriptor=type_name,
            type_relation="operand",
            type_match=type_match,
            reference_format=reference_format,
            cursor=cursor,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_build_xref_index(analysis_id: AnalysisId) -> DexIndexResult:
        """Build an optional bounded full static index for this handle's lifetime."""
        return run(analysis_id, "build_xref_index")

    @registry.tool(annotations=READ_ONLY)
    def apk_search_members(
        analysis_id: AnalysisId,
        kind: Annotated[Literal["method", "field"], Field(description="Declared member category")],
        query: Query,
        class_name: OptionalClass = None,
        member_match: Annotated[
            Literal["name", "descriptor"], Field(description="Match names or full identities")
        ] = "name",
        case_sensitive: CaseSensitive = False,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexMemberPage:
        """Discover literal declaration names or identities without preprocessing instructions."""
        return run(
            analysis_id,
            "search_members",
            kind=kind,
            value=query,
            class_name=class_name,
            member_match=member_match,
            case_sensitive=case_sensitive,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_search_strings(
        analysis_id: AnalysisId,
        query: Query,
        case_sensitive: CaseSensitive = False,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexReferencePage:
        """Discover DEX string-pool values, not instruction use sites."""
        return run(
            analysis_id,
            "search_strings",
            value=query,
            case_sensitive=case_sensitive,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_get_class_outline(
        analysis_id: AnalysisId, class_name: ClassName, offset: Offset = 0, limit: Limit = 200
    ) -> DexMemberPage:
        """Page interfaces, typed fields and full declared method signatures."""
        return run(
            analysis_id, "get_class_outline", class_name=class_name, offset=offset, limit=limit
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_get_class_hierarchy(
        analysis_id: AnalysisId, class_name: ClassName, offset: Offset = 0, limit: Limit = 200
    ) -> DexMemberPage:
        """Page type hierarchy; external definitions and cycles are explicit."""
        return run(
            analysis_id, "get_class_hierarchy", class_name=class_name, offset=offset, limit=limit
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_get_string_constants(
        analysis_id: AnalysisId, class_name: ClassName, offset: Offset = 0, limit: Limit = 200
    ) -> DexReferencePage:
        """Read this class's literal const-string/jumbo instruction sites."""
        return run(
            analysis_id, "get_string_constants", class_name=class_name, offset=offset, limit=limit
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_search_method_bodies(
        analysis_id: AnalysisId,
        query: Query,
        class_name: OptionalClass = None,
        case_sensitive: CaseSensitive = False,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexReferencePage:
        """Search decoded instruction/operand text including literals; this is not source search."""
        return run(
            analysis_id,
            "search_method_bodies",
            value=query,
            class_name=class_name,
            case_sensitive=case_sensitive,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_disassemble_method(
        analysis_id: AnalysisId,
        class_name: OptionalClass = None,
        method_name: MethodName = None,
        descriptor: Prototype = None,
        method_descriptor: MethodId = None,
        offset: Offset = 0,
        limit: Limit = 200,
    ) -> DexInstructionPage:
        """Page one exact method's structured instructions with 16-bit code-unit offsets."""
        return run(
            analysis_id,
            "disassemble_method",
            class_name=class_name,
            method_name=method_name,
            target_descriptor=descriptor,
            method_descriptor=method_descriptor,
            offset=offset,
            limit=limit,
        )

    @registry.tool(annotations=READ_ONLY)
    def apk_get_class_source_metadata(
        analysis_id: AnalysisId, class_name: ClassName, offset: Offset = 0, limit: Limit = 200
    ) -> DexSourceResult:
        """Page decompiler token links with Unicode code-point spans, not instruction xrefs."""
        return run(
            analysis_id,
            "get_class_source_metadata",
            class_name=class_name,
            offset=offset,
            limit=limit,
        )
