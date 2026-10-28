"""Wire-compatible typed MCP output contracts, including optional diagnostics."""

from typing import Literal

from pydantic import ConfigDict
from typing_extensions import Required, TypedDict


class Object(TypedDict, total=False):
    __pydantic_config__ = ConfigDict(extra="allow", strict=True)


class Source(Object, total=False):
    path: str
    dex_entry: str
    container_entry: str
    size_bytes: int
    sha256: str
    dex_version: str
    declared_class_count: int


class Result(Object, total=False):
    status: Literal["ok", "partial", "error", "not_applicable"]
    code: str
    message: str
    backend: str
    backend_version: str
    apk_path: str
    apk_sha256: str
    artifact_path: str
    artifact_sha256: str
    input_id: str
    session_id: str
    sources: list[Source]
    total: int
    offset: int
    limit: int
    truncated: bool
    has_more: bool
    next_offset: int | None
    coverage: str
    limitations: list[str]


class Capabilities(Object, total=False):
    configured: bool
    enabled: bool
    operations: list[str]
    reference_kinds: list[str]
    default: bool
    limitation: str
    tested_commit: str
    max_count: int
    idle_ttl_seconds: int
    max_disk_bytes: int
    max_index_bytes_per_session: int
    memory_page_cache_bytes_per_session: int
    memory_page_cache_max_entries: int
    selected_reference_cache: "Capabilities"
    durable_index_cache: "Capabilities"
    max_bytes: int
    max_entry_bytes: int
    scope: str


class ArtifactInputs(Object, total=False):
    dex_sessions: list[str]
    inventory_only: list[str]
    direct_dex_paths: str
    signing: str
    v31: str
    revision_diff: str
    secret_candidates: str


class PingResult(Result, total=False):
    status: Required[Literal["ok"]]
    server: Required[str]
    server_version: Required[str]
    droidasc_version: Required[str]
    allowed_roots: Required[list[str]]
    timeout_seconds: Required[int]
    max_worker_memory_bytes: Required[int]
    max_page_size: Required[int]
    artifact_inputs: Required[ArtifactInputs]
    rust_backend: Required[Capabilities]
    method_backend: Required[Capabilities]
    dex_sessions: Required[Capabilities]


class ApkInfoResult(Object, total=False):
    apk_path: Required[str]
    size_bytes: Required[int]
    dex_entries: Required[list[str]]
    has_manifest: Required[bool]
    sha256: str


class Entry(Object, total=False):
    path: Required[str]
    kind: Required[str]
    size_bytes: Required[int]
    compressed_size_bytes: int
    crc32: str
    encrypted: bool
    abi: str | None


class ArchiveResult(Result, total=False):
    status: Required[Literal["ok", "partial", "error", "not_applicable"]]
    format_validation: Literal["not_performed"]
    items: list[Entry]
    entry: Entry
    entry_path: str
    content: str
    encoding: Literal["utf-8", "base64"]
    returned_bytes: int
    byte_offset: int
    next_byte_offset: int | None
    content_complete: bool
    crc_verified: bool
    decoded: bool
    decoding_status: str
    decoding_warnings: list[str]
    xml_format: str


class Permission(Object, total=False):
    value: Required[str | None]
    source: Required[str]
    resolved: Required[bool]


class IntentFilter(Object, total=False):
    declarations: dict[str, str]
    actions: list[dict[str, str]]
    categories: list[dict[str, str]]
    data: list[dict[str, str]]


class Component(Object, total=False):
    kind: Required[str]
    name: Required[str | None]
    target_activity: str | None
    declarations: dict[str, str]
    exported: bool | None
    exported_status: str
    enabled: bool | None
    effective_enabled: bool | None
    effective_permission: Permission
    effective_read_permission: Permission
    effective_write_permission: Permission
    intent_filters: list[IntentFilter]
    metadata: list[dict[str, str]]
    path_permissions: list[dict[str, str]]
    grant_uri_permissions: list[dict[str, str]]


class ManifestResult(Result, total=False):
    status: Required[Literal["ok", "partial", "error", "not_applicable"]]
    items: list[Component]
    entry: Entry
    package_name: str | None
    declarations: dict[str, str]
    sdk: dict[str, str]
    application: dict[str, str]
    declared_permissions: list[dict[str, str]]
    application_metadata: list[dict[str, str]]
    resource_values_resolved: bool
    exported_defaults_resolved: bool


class Certificate(Object, total=False):
    sha256: Required[str]
    sha1: Required[str]
    subject: Required[str]
    issuer: Required[str]
    serial_hex: str
    not_before_utc: str
    not_after_utc: str
    public_key_algorithm: str
    public_key_bits: int | None
    public_key_sha256: str
    certificate_signature_oid: str


class Signer(Object, total=False):
    signer_index: int
    certificates: Required[list[Certificate]]
    certificate_order: str
    attribute_ids: list[str]
    rotation_lineage: str
    min_sdk: int
    max_sdk: int
    entry: str


class SigningScheme(Object, total=False):
    scheme: Required[Literal["v1", "v2", "v3", "v3.1"]]
    container_present: Required[bool | None]
    signers: list[Signer]
    containers: list[Signer]
    certificate_role: str
    certificate_extraction: str


class Diagnostic(Object, total=False):
    code: Required[str]
    message: str
    scheme: str
    entry: str


class SigningResult(Result, total=False):
    status: Required[Literal["ok", "partial", "error"]]
    schemes: list[SigningScheme]
    unknown_signing_block_ids: list[str]
    diagnostics: list[Diagnostic]
    cryptographic_verification: Literal["not_performed"]
    apk_content_integrity: Literal["not_verified"]
    certificate_trust: Literal["not_evaluated"]
    v4_sidecar: Literal["not_inspected"]


class ArtifactDifference(Object, total=False):
    class_name: Required[str]
    change: Required[Literal["added", "removed"]]


class ManifestHeader(Object, total=False):
    status: Required[Literal["ok", "error", "not_applicable"]]
    entry: Required[str]
    code: str
    message: str
    xml_format: Literal["text_xml", "android_binary_xml"]
    decoding_warnings: list[str]
    package_name: str | None
    version_name: str | None
    version_code: str | None
    min_sdk: str | None
    target_sdk: str | None
    application_name: str | None
    resource_values_resolved: Literal[False]


class ArtifactSummary(Object, total=False):
    entry_count: Required[int]
    native_scope: Required[Literal["archive", "selected_module"]]
    native_library_count: Required[int]
    native_abis: Required[list[str]]
    native_abi_count: Required[int]
    native_abis_truncated: Required[bool]
    manifest: Required[ManifestHeader]


class ArtifactResult(Result, total=False):
    status: Required[Literal["ok", "error"]]
    artifact_kind: Literal["apk", "jar", "aar", "aab", "apks", "xapk", "zip"]
    selected_module: str | None
    modules: list[str]
    dex_entries: list[str]
    jvm_class_count: int
    nested_apk_count: int
    dex_analysis: bool
    jvm_decompilation: bool
    split_reconstruction: bool
    items: list[Entry | ArtifactDifference]
    summary: ArtifactSummary


class ArtifactHandleResult(Result, total=False):
    status: Required[Literal["ok", "error"]]
    analysis_id: str
    name: str
    artifact_type: Literal["apk", "dex", "jar", "aar", "aab", "apks", "xapk", "zip"]
    capabilities: list[str]
    size_bytes: int
    sha256: str
    entry_count: int
    dex_count: int
    stored_bytes: int
    idle_ttl_seconds: int


class CloseArtifactResult(Object):
    analysis_id: Required[str]
    closed: Required[bool]
    cleanup_pending: Required[bool]


class DexRow(Object, total=False):
    target_index: int
    value: str
    instruction: str
    dispatch_kind: str
    class_name: str
    descriptor: str
    method_descriptor: str
    name: str
    kind: str
    dex_entry: str
    caller: str
    callee: str
    source: str
    type_descriptor: str
    field_descriptor: str
    instruction_offset: int | None
    offset_unit: str | None
    opcode: str
    relation: str
    detail: str
    access: Literal["read", "write"]
    storage: Literal["static", "instance"]
    target_resolution: str
    target_dex_entry: str | None
    parameter_types: list[str]
    return_type: str
    access_flags: int
    has_code: bool
    string_index: int
    string: str
    raw: str
    method: str
    matched: str
    dex: str
    target: str
    reason: str
    call_site_prototype: str


class ReferenceGroup(Object, total=False):
    dex_entry: Required[str]
    caller: Required[str]
    target_field: Required[Literal["callee", "field_descriptor", "value", "type_descriptor"]]
    offset_unit: str | None
    matches: Required[list[str]]
    evidence: Required[list[DexRow]]


class Index(Object, total=False):
    schema: Required[str]
    input_id: Required[str]
    backend_id: Required[str]
    reused: Required[bool]
    stored_bytes: Required[int]
    persistence: str
    durable_cache: str
    format: str


class QueryCache(Object, total=False):
    hit: Required[bool]
    stored: bool
    scope: Required[str]
    budget_bytes: int
    stored_bytes: int


class GraphNode(Object, total=False):
    method_descriptor: Required[str]
    depth: Required[int]
    definition_resolution: Required[str]
    dex_entry: Required[str | None]
    without_code: Required[bool | None]
    expansion_status: Required[str]


class SourceReference(Object, total=False):
    start: Required[int]
    end: Required[int]
    kind: Required[str]
    declaring_class: str
    name: str
    descriptor: str
    declaration: bool


class DexResult(Result, total=False):
    type_relation: str
    type_match: Literal["exact", "substring"]
    page_limited_by: Literal["response_bytes", "caller_groups"]
    reference_format: Literal["grouped"]
    groups: list[ReferenceGroup]
    returned_sites: int
    limit_unit: Literal["caller_groups"]
    total_unit: Literal["reference_sites"]
    next_cursor: str | None
    response_byte_limit: int
    member_references: list[SourceReference]
    source_sha256: str
    source_start: int
    source_end: int
    span_unit: str
    superclass: str | None
    access_flags: int
    field_count: int
    method_count: int
    hierarchy_cycle_detected: bool
    status: Required[Literal["ok", "partial", "error", "not_applicable"]]
    input_kind: str
    runtime_completeness: str
    engine_version: str
    has_manifest: bool
    items: list[DexRow]
    source: str
    format: Literal["java", "smali", "cli-text-best-effort"]
    class_name: str
    method_descriptor: str
    method_name: str
    candidate_count: int
    field_descriptor: str
    type_descriptor: str
    dex_entry: str
    scanned_methods: int
    scanned_instructions: int
    methods_without_code: int
    scan_errors: int
    unresolved_matches: int
    dynamic_sites: int
    unresolved_sites: list[DexRow]
    unresolved_sites_truncated: bool
    instruction_scan_complete: bool
    runtime_target_resolution: str
    reference_semantics: str
    index: Index
    query_cache: QueryCache
    nodes: list[GraphNode]
    edges: list[DexRow]
    node_count: int
    edge_count: int
    depth: int
    max_nodes: int
    max_edges: int
    direction: Literal["incoming", "outgoing", "both"]
    truncation_reasons: list[str]
    traversal_complete_within_depth: bool
    edge_counts: dict[str, int]
    definition_count: int
    cleanup_pending: bool
    stored_bytes: int
    reserved_index_bytes: int
    idle_ttl_seconds: int


class DexInfoResult(Result, total=False):
    status: Required[Literal["ok", "partial", "error", "not_applicable"]]
    input_kind: str
    engine_version: str
    runtime_completeness: str
    has_manifest: bool
    definition_count: int


class ClassRow(Object, total=False):
    class_name: str
    dex_entry: str


class MemberRow(ClassRow, total=False):
    kind: str
    name: str
    descriptor: str
    parameter_types: list[str]
    return_type: str
    access_flags: int
    has_code: bool
    relation: str


class InstructionRow(Object, total=False):
    dex_entry: str
    method_descriptor: str
    instruction_offset: int | None
    offset_unit: str | None
    opcode: str
    instruction: str


class DexClassPage(DexInfoResult, total=False):
    items: list[ClassRow]
    query_cache: QueryCache


class DexMemberPage(DexInfoResult, total=False):
    items: list[MemberRow]
    class_name: str
    dex_entry: str
    superclass: str | None
    access_flags: int
    field_count: int
    method_count: int
    hierarchy_cycle_detected: bool
    query_cache: QueryCache


class DexSourceResult(DexInfoResult, total=False):
    source: str
    format: Literal["java", "smali", "cli-text-best-effort"]
    class_name: str
    method_descriptor: str
    method_name: str
    candidate_count: int
    dex_entry: str
    member_references: list[SourceReference]
    source_sha256: str
    source_start: int
    source_end: int
    span_unit: str


class DexInstructionPage(DexInfoResult, total=False):
    items: list[InstructionRow]
    class_name: str
    method_descriptor: str
    method_name: str
    candidate_count: int
    dex_entry: str
    query_cache: QueryCache


class DexReferencePage(DexInfoResult, total=False):
    items: list[DexRow]
    class_name: str
    method_descriptor: str
    candidate_count: int
    field_descriptor: str
    type_descriptor: str
    type_relation: str
    type_match: Literal["exact", "substring"]
    dex_entry: str
    scanned_methods: int
    scanned_instructions: int
    methods_without_code: int
    scan_errors: int
    unresolved_matches: int
    dynamic_sites: int
    unresolved_sites: list[DexRow]
    unresolved_sites_truncated: bool
    instruction_scan_complete: bool
    runtime_target_resolution: str
    reference_semantics: str
    query_cache: QueryCache
    index: Index
    page_limited_by: Literal["response_bytes", "caller_groups"]
    reference_format: Literal["grouped"]
    groups: list[ReferenceGroup]
    returned_sites: int
    limit_unit: Literal["caller_groups"]
    total_unit: Literal["reference_sites"]
    next_cursor: str | None
    response_byte_limit: int


class DexGraphResult(DexInfoResult, total=False):
    method_descriptor: str
    candidate_count: int
    nodes: list[GraphNode]
    edges: list[DexRow]
    node_count: int
    edge_count: int
    depth: int
    max_nodes: int
    max_edges: int
    direction: Literal["incoming", "outgoing", "both"]
    truncation_reasons: list[str]
    traversal_complete_within_depth: bool
    edge_counts: dict[str, int]
    index: Index


class DexIndexResult(DexInfoResult, total=False):
    index: Index
    stored_bytes: int
    reserved_index_bytes: int


class DiffRow(Object, total=False):
    kind: Required[Literal["class", "method", "field"]]
    descriptor: Required[str]
    change: Required[Literal["added", "removed"]]
    old_dex_entry: Required[str | None]
    new_dex_entry: Required[str | None]


class DiffResult(Result, total=False):
    status: Required[Literal["ok", "error"]]
    old_session_id: str
    new_session_id: str
    old_input_id: str
    new_input_id: str
    old_sources: list[Source]
    new_sources: list[Source]
    items: list[DiffRow]
    counts: dict[str, int]
    scope: str
    behavior_comparison: str
    declaration_attributes_comparison: str


class SecretRow(Object, total=False):
    value: str
    pattern: Required[str]
    dex_entry: Required[str]
    string_index: Required[int]
    candidate_sha256: str
    redacted: str
    utf16_offset: int
    length_utf16: int
    confidence: str


class SecretResult(Result, total=False):
    values_included: bool
    status: Required[Literal["ok", "partial", "error"]]
    items: list[SecretRow]
    scanned_strings: int
    scanned_utf8_bytes: int
    skipped_oversize_strings: int
    capped_pattern_string_pairs: int
    coverage_complete: bool
    credential_validity: str
    instruction_use_sites: str
    pattern_version: int


class LegacyResult(Result, total=False):
    items: list[str | DexRow]
    xml: str
    source: str
    class_name: str
    kind: str
