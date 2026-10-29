# droidasc-mcp

A small, defensive MCP server for [Droid ASC](https://github.com/MG1937/ASC), the fast
on-demand Android APK decompiler.

`droidasc-mcp` exposes ASC's public CLI as typed, read-only MCP tools. Every analysis runs in an
isolated subprocess group, accepts only input paths under configured roots, and returns paginated
structured data instead of unbounded terminal output.

> Community project. Not affiliated with or endorsed by the Droid ASC maintainers.

[中文文档](README.zh-CN.md)

## Tools

| Tool | Purpose |
| --- | --- |
| `asc_ping` | Show adapter/engine versions and effective runtime limits |
| `asc_apk_info` | Return size, SHA-256, manifest presence, and DEX entries |
| `asc_list_apk_entries` | Page archive contents or inventory a standalone DEX file |
| `asc_read_apk_entry` | Read bounded archive/DEX bytes and decode binary XML |
| `asc_manifest_summary` | Page structured components, filters and permission provenance |
| `asc_signing_inventory` | Inspect signature-container presence and certificate fingerprints, without signature verification |
| `asc_inspect_artifact` | Page container capabilities; optional compact manifest/native summary |
| `asc_open_artifact_session` | Snapshot selected container DEX into the existing session workflow |
| `asc_diff_dex_sessions` | Compare sorted class/member identities between hash-bound revisions |
| `asc_secret_candidates` | Search fixed DEX string patterns with redacted source locations |
| `asc_get_manifest` | Decode `AndroidManifest.xml` with line pagination |
| `asc_list_classes` | List class descriptors with prefix filtering and pagination |
| `asc_get_class_source` | Decompile one class with line pagination |
| `asc_find_refs` | Find string/type/method/field references; direct hierarchy queries |
| `asc_analyze_dex` | Analyze a bare DEX or explicit DEX set with source hashes |
| `asc_open_dex_session` | Snapshot validated DEX inputs into an immutable bounded session |
| `asc_query_dex_session` | Query that session with the original hashes and DEX provenance |
| `asc_close_dex_session` | Close the session and release its private files |

### Artifact workflow profiles

The opt-in `DROIDASC_MCP_TOOL_PROFILE=artifact` adds focused
handle-oriented DEX tools: `apk_list_classes`, `apk_list_methods`, class outlines,
exact method source/disassembly/calls, references, literal searches, hierarchy and
bounded graphs. All use `analysis_id` from `load_artifact`. Each tool advertises only
its relevant selectors. Exact methods accept a full `method_descriptor`, or an exact
`class_name`/`method_name` with `descriptor` for an overloaded prototype.
`apk_search_references` handles partial/fuzzy member targets separately.
`apk_find_type_instructions` selects explicit type operands; `apk_find_type_references`
retains the broader static relation scopes. The generic DEX selector remains callable
but is not advertised in this profile. The default stays `legacy`.

The compatibility profile `DROIDASC_MCP_TOOL_PROFILE=artifact_preview` advertises
`load_artifact`, `close_artifact`, `apk_get_summary`, `apk_get_manifest`,
`apk_list_entries`, `apk_get_resource_content` and `apk_get_signing_info`, plus the
status, DEX query, revision diff and secret-candidate bridges. Open an artifact once
and use its `analysis_id` for metadata. Code queries use the same value as
`asc_query_dex_session.session_id`; DEX preparation starts on the first code query.
Close with `close_artifact`. Metadata and code share the immutable original hash,
storage quota and lifetime. The default `legacy` profile and all old callable tools
remain unchanged. This preview is not the final focused DEX tool surface.

Manifest and class resources also accept the handle at
`droidasc://analysis/{analysis_id}/manifest?offset=0&limit=100` and
`droidasc://analysis/{analysis_id}/class?class_name=...&offset=0&limit=100`.
URI query values must be percent-encoded. Existing resource URIs remain valid.

For AAB inputs, `module` defaults to `base`. Select one exact name,
an explicit list such as `["base", "feature"]`, or `"*"` for every module on
`load_artifact`, `asc_inspect_artifact` or `asc_open_artifact_session`. Union queries
retain original module/DEX provenance and reject duplicate class definitions.
Multi-module summaries return `manifests`, not a merged manifest. For a manifest
read, pass one selected `module` to `apk_get_manifest` or use
`droidasc://analysis/{analysis_id}/module/{module}/manifest?offset=0&limit=100`.
Resources use their exact module-prefixed entry path. AAB protobuf XML decoding and
nested split reconstruction remain unsupported; raw entry bytes stay readable.

## Install

Version 0.2.5 adds selected string/type reference reuse, compact grouped pages, the opt-in
artifact workflow, multi-module AAB analysis and original-byte native DEX 041 queries.
Existing tools and matching defaults remain compatible. It retains checked native
DEX references, discovery, structural views and lazy
indexes. An optional C accelerator has an independent Python fallback; ASC remains the public
Smali engine. The [native-query validation](docs/NATIVE_QUERY_VALIDATION.md) records accuracy,
workload-specific cold-query improvements and the remaining startup/first-result cost.

It also includes class search/outline/hierarchy, constant use sites, decoded instruction
search/disassembly and source-token links through the existing DEX query tools. It also adds
strict DEX 041 imports, first-level JVM JAR inventory/diffs, resumable archive byte pages,
manifest/class resource templates, `compare_versions` and opt-in secret candidate values.
The [complete competitor source map](docs/COMPETITOR_API_AUDIT.md) records all 25 tools,
two resources, three prompts and 87 parameters, including intentional interface differences.
Functional parity does not establish universal performance superiority.

Container, signing and review workflows and their support boundaries are described in
[REVERSE_WORKFLOW.md](docs/REVERSE_WORKFLOW.md). Release gates cover cross-platform,
transport and clean-package execution.

Python 3.10 or newer is required. CI checks Linux and native Windows runners on Python 3.10-3.13, including
all 18 tools over stdio/HTTP against a source-built
[acceptance APK](tests/fixtures/android/README.md)
and package installation. macOS remains unverified.

Install the version-pinned packages from
[Releases](https://github.com/cnlnn/droidasc-mcp/releases).
CPython 3.11+ on x86-64 Linux:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --force-reinstall --no-cache-dir https://github.com/cnlnn/droidasc-mcp/releases/download/v0.2.5/droidasc_mcp-0.2.5-cp311-abi3-manylinux_2_34_x86_64.whl
```

CPython 3.11+ on Windows (PowerShell):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --force-reinstall --no-cache-dir https://github.com/cnlnn/droidasc-mcp/releases/download/v0.2.5/droidasc_mcp-0.2.5-cp311-abi3-win_amd64.whl
```

For CPython 3.10, create the environment with `python3.10` or `py -3.10` and replace
`cp311-abi3` in the wheel URL with `cp310-cp310`. The stable-ABI wheels support CPython 3.11
and newer; the Linux wheels require glibc 2.34 or newer. The canonical source archive is
`droidasc_mcp-0.2.5.tar.gz`. Source installation retains the Python fallback if no compiler is
available. macOS remains unverified. If you installed a withdrawn 0.2.3-0.2.9 package,
use `--force-reinstall --no-cache-dir` to replace it with this build. Withdrawn historical
builds were consolidated into v0.2.3; current assets are built and validated separately.
Windows uses `.venv\Scripts\droidasc-mcp.exe` for the server command. For development,
clone this repository and run `uv sync --locked --extra dev` instead.

The development branch selects the reviewed downstream ASC source compatibility
build at an immutable Git commit. Installing development source or development
wheels therefore also requires Git and HTTPS access to GitHub. This includes the
method-annotation and original-type-link fixes described in
[the source provenance](third_party/droidasc_sourcefixes/PROVENANCE.md); it does not
change the dependency or assets of the published v0.2.5 release.

## Connect

The default transport is stdio. Limit the server to directories that contain APKs:

```bash
export DROIDASC_MCP_ALLOWED_ROOTS=/absolute/path/to/apks
.venv/bin/droidasc-mcp
```

### Codex

```bash
codex mcp add droidasc \
  --env DROIDASC_MCP_ALLOWED_ROOTS=/absolute/path/to/apks \
  -- /absolute/path/to/droidasc-mcp/.venv/bin/droidasc-mcp
```

### Claude Desktop and compatible hosts

```json
{
  "mcpServers": {
    "droidasc": {
      "command": "/absolute/path/to/droidasc-mcp/.venv/bin/droidasc-mcp",
      "env": {
        "DROIDASC_MCP_ALLOWED_ROOTS": "/absolute/path/to/apks"
      }
    }
  }
}
```

### Streamable HTTP

```bash
DROIDASC_MCP_ALLOWED_ROOTS=/absolute/path/to/apks \
  .venv/bin/droidasc-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

The endpoint is `http://127.0.0.1:8000/mcp`. Keep it on loopback unless you add an authenticated,
TLS-terminating reverse proxy.

## Examples

Ask an MCP host to call:

```text
asc_apk_info(apk_path="/samples/app.apk")
asc_manifest_summary(apk_path="/samples/app.apk", limit=20)
asc_list_apk_entries(apk_path="/samples/app.apk", kind="resource", limit=100)
asc_read_apk_entry(apk_path="/samples/app.apk", entry_path="res/xml/config.xml")
asc_list_classes(apk_path="/samples/app.apk", prefix="com.example", limit=100)
asc_find_refs(apk_path="/samples/app.apk", kind="string", value="Authorization")
asc_find_refs(apk_path="/samples/app.apk", kind="extends", value="android.app.Activity")
asc_find_refs(apk_path="/samples/app.apk", kind="impl", value="java.lang.Runnable")
asc_get_class_source(apk_path="/samples/app.apk", class_name="com.example.MainActivity")
```

### APK contents and manifest triage

The three archive tools bind every successful result to `apk_sha256`. Match hashes before
correlating resources, components and code. Inventory supports a category and a literal,
case-sensitive path prefix; its CRC values are ZIP metadata, not integrity verification.
Native rows report archive paths and ABI directories, not ELF analysis.

`asc_read_apk_entry` streams a bounded prefix without filesystem extraction. `max_bytes`
defaults to 16 KiB, with a 128 KiB maximum before UTF-8/base64 encoding. XML decoding reads
only complete inputs up to 4 MiB. `decoded`, `decoding_status`, `decoding_warnings`,
`truncated`, `content_complete` and `crc_verified` distinguish successful decoding, decoder
warnings, output truncation and incomplete raw reads. Resource-table values remain unresolved.

These two entry tools also accept a standalone `.dex` path. Use its returned basename as
`entry_path`, then follow `next_byte_offset` with `byte_offset` for subsequent pages. Results
retain `artifact_sha256` and original bytes, including physical DEX 041 bytes. Raw files have
no ZIP CRC fields; `format_validation=not_performed` distinguishes byte reads from validated
code analysis through `asc_open_dex_session`.

`asc_manifest_summary` preserves raw namespaced declarations and component order, intent
filters, metadata, provider path/URI-grant rules, and permission inheritance sources. Explicit
empty permissions clear inherited requirements; an alias without its own permission requires
none, rather than inheriting its target/application permission. Absent exported defaults and
resource-dependent values remain unresolved. These are static declarations, not proof of
runtime accessibility. Follow `next_offset`; reduce page size on an explicit `response_limit`.
See [archive workflow boundaries and acceptance](docs/ARCHIVE_WORKFLOW.md).

Results include `total`, `offset`, `limit`, `truncated`, and `next_offset`. Use `next_offset` for the
next request (`null` means done): the response budget can shorten a page. A single line
that exceeds the budget produces an explicit error rather than silent truncation.

Reference fields are best-effort parsing of ASC CLI text. Embedded newlines can split records;
`total` counts output lines, not semantic references. Reference lines are sorted before pagination.
Values such as `--help` are query data, not CLI options. ASC's matching semantics still apply:
string/type queries accept regular expressions, and invalid patterns return errors. The exact
value `--gui` returns an explicit error because ASC reserves it before parsing CLI arguments.
Exact method/field class names accept
Java names or Dalvik descriptors; fuzzy class patterns retain their original meaning.

The `extends` and `impl` kinds query **direct** superclass/interface declarations,
including interface-to-interface declarations. They require Droid ASC 0.1.2.post2 or newer
(installed by the updated dependency requirement). Supply a Java name or Dalvik descriptor in
`value`; class filters are rejected for these kinds. Records contain `dex`, `class_name`,
`relation`, `target`, and `raw`, with `relation_scope="direct"`. They are not transitive
subclass searches or runtime dispatch graphs. Unrecognized text remains a raw-only record.
The same queries work with `asc_analyze_dex(operation="find_refs", ...)`.

Snapshots are decoded and sorted once, then cached for 60 seconds (up to 8 entries). The cache
budget accounts for Python strings and tuple pointers, not just original output bytes. Identical
concurrent queries share a single computation; unrelated queries and cache hits do not wait on
a global computation lock. Snapshots are
keyed by query and file identity/size/timestamps. Cache misses rerun ASC; this is not an immutable
content-addressed evidence store. Do not modify APK files between pages.

## Bare DEX analysis

Available in v0.2.3.
It accepts 1-64 explicit `.dex` paths under the allowed roots, with a combined size bounded by
`DROIDASC_MCP_MAX_APK_BYTES`. Directories, APKs and CompactDex are not accepted by this tool.
DEX 041 containers are supported, with the combined limit of 64 logical DEX files.

```text
asc_analyze_dex(dex_paths=["/samples/classes.dex", "/samples/classes2.dex"])
asc_analyze_dex(dex_paths=["/samples/classes.dex"], operation="list_classes", prefix="com.example")
asc_analyze_dex(dex_paths=["/samples/classes.dex"], operation="get_class_source", class_name="com.example.Main")
asc_analyze_dex(dex_paths=["/samples/classes.dex"], operation="find_refs", kind="string", value="Authorization")
```

`operation` defaults to `info`. Successful responses have `status="ok"` and a `sources` array
mapping internal `dex_entry` names to original paths, SHA-256 hashes, sizes and class counts.
Class/source results retain `dex_entry`; reference results retain ASC's best-effort `dex` field.
Input order determines entry names. Keep both the order and file bytes stable between pages and
compare the returned hashes. Each call imports and analyzes afresh; APK cross-request caching
does not apply to this tool.

Standard little-endian DEX headers (035/037/038/039/040), fixed ID-table bounds, file size, SHA-1
signature and Adler-32 checksum are checked before analysis. Checksum validation does not prove
method bodies or runtime coverage are complete. The tool preserves input bytes, creates private
temporary analysis containers, and invokes ASC's public module entry point in the supervised worker.
Containers are not installable APKs and are removed after success, failure, timeout or cancellation.
Temporary disk usage can approach twice the combined input size, plus ZIP overhead.

DEX 041 inventory, focused references, discovery, structure and indexes read each logical
header against the original physical bytes without Java. One physical snapshot backs the
logical entries; `snapshot_entry`, `stored_size_bytes`, `logical_header_offset` and
`logical_size_bytes` distinguish storage from logical ownership. The original physical
SHA-256 is retained in `sha256`/`container_sha256`. Shared later pools are supported, and
every logical header and checksum is validated before publication.

ASC class/Smali source uses a temporary selected-header view when needed, recording its
separate `source_view` hash. Explicit Java source still uses JADX 1.5.5/JDK 17+ and a bounded,
temporary dexlib2 standalone conversion; the JADX distribution supplies the required jars.
The legacy `operation="find_refs"` adapter retains its previous standalone DEX 041 conversion
and requires `DROIDASC_MCP_DEXLIB_HOME` (Google Smali 3.0.9) plus JDK 17+, not JADX.
Use focused reference operations for native DEX 041 queries. Conversion views reserve up to
seven times the original physical bytes plus metadata; they never replace the original snapshot.

Duplicate class definitions are rejected with `status="error", code="duplicate_class"` rather
than selecting one silently (up to 20 conflicts are returned). `get_manifest` returns
`status="not_applicable", code="no_manifest"`. Invalid input/query and engine failures return
diagnostic codes; a successful empty reference search is `status="ok", total=0`.
Path policy, worker startup, timeout, memory and stream-limit failures remain MCP tool errors.
Clients must inspect both MCP errors and the structured `status`.

This is post-export static analysis, not automatic unpacking or DEX repair. It does not recover
missing code, decrypt runtime-only method bodies, or reconstruct the original manifest/resources.
Every result is limited to supplied files (`coverage="supplied_files_only"`), with runtime
completeness marked unknown. Untrusted dumps still require an isolated analysis environment.

### Immutable sessions

Open with `asc_open_dex_session(dex_paths=[...])`, retain its `session_id`, then call
`asc_query_dex_session(session_id="...", operation="list_classes")`. Query parameters match
`asc_analyze_dex`. Close with `asc_close_dex_session(session_id="...")`.

The `input_id` binds ordered DEX SHA-256 hashes, schema and ASC version. The UUID session ID
identifies one private snapshot, not a global current sample. Changing/deleting original files
does not mutate that snapshot. Cache keys include complete query options and backend identity,
not merely the input ID; distinct queries cannot share a cached page.
Reuse skips reimport, integrity checks and the duplicate-class scan; **it does not retain a
resident decompiler or promise warm engine latency**. Method results identify the optional backend
version separately. Sessions are local to this server process, not shared across hosts/restarts.

Idle sessions expire (swept at most every 30 seconds), and least-recently-used idle sessions can
be evicted at capacity. Active queries pin storage. Closing an active session prevents new queries
and returns `cleanup_pending=true`; the last active query releases the files. Normal MCP lifespan
shutdown cleans sessions; abrupt host termination may leave OS temporary files. A lost handle
returns `session_not_found`, never silently reloads changed evidence. Cancellation or failed opens
release their reservations. Concurrent preparation has reserved disk/count capacity before starting.

### Exact methods and Smali

Core focused DEX queries, discovery, indexes and structural views do not need Java or JADX.
`source_format=auto` (the default) and `smali` use ASC 0.1.2.post3 directly.
Set `debug_info=true` to include upstream debug directives.

Only explicit `source_format=java` needs the official [JADX 1.5.5 distribution](https://github.com/skylot/jadx/releases/tag/v1.5.5)
and a JDK 17 or newer. Set `DROIDASC_MCP_JADX_HOME` to its extracted directory (containing `lib/`).
Set `DROIDASC_MCP_JAVA` to the JDK's `java` executable, or put it on `PATH`. A JRE alone cannot run
the source bridge. The Python package does not bundle/download JADX or require Java for ASC tools.

```text
asc_query_dex_session(session_id="...", operation="list_methods", class_name="com.example.Main")
asc_query_dex_session(session_id="...", operation="get_method_source", method_descriptor="Lcom/example/Main;->check(I)Z")
asc_analyze_dex(dex_paths=["/samples/classes.dex"], operation="get_method_source", method_descriptor="Lcom/example/Main;->check(I)Z", source_format="smali")
```

`list_methods` reads raw DEX definitions natively, including constructors, synthetic/bridge
methods, native/abstract declarations, complete parameter types and return types. It sorts full
descriptors before pagination. No method name, partial prototype, or overload index selects a body.
`get_method_source` requires the exact full descriptor; an absent overload returns `method_not_found`.
Class mismatches are rejected rather than choosing another owner.

`source_format=auto` returns ASC's exact-method Smali without attempting Java decompilation.
Results carry `format`, `fell_back`, `fallback_reason`, backend version, original hashes and
`dex_entry`. Explicit `java` returns `java_unavailable` instead of falling back when no exact
Java method body is available; missing Java configuration returns `backend_unavailable`.
Java error/warning counts are engine diagnostics, not proof of semantic correctness. Reference
tools named `find_refs` still use ASC's best-effort name-level text.

`find_field_refs` requires `field_descriptor`, for example `Lcom/example/Config;->enabled:Z`.
Set `field_access` to `all` (default), `read` or `write`. Rows contain the exact caller and field
descriptors, `access`, `storage` (`static`/`instance`), opcode, DEX provenance and code-unit offset.
Filtering occurs before pagination, so totals and page cursors refer to the selected access kind.
Same-name fields with different types are distinct; an unused or absent field returns zero matches,
while references to external fields retain `target_dex_entry=null`. Definition lookup is literal:
inherited field resolution is not performed. Reflection, JNI, method-handle targets and encoded
initial values are not direct instruction accesses and are not claimed as reads or writes.
This operation uses the native instruction scanner on one-shot inputs and sessions, without Java.

```python
asc_query_dex_session(
    session_id="...",
    operation="find_field_refs",
    field_descriptor="Lcom/example/Config;->enabled:Z",
    field_access="write",
)
```

`find_method_refs` and `get_method_calls` are separate descriptor-exact operations on DEX inputs
and sessions, using the native instruction scanner. Each result row carries full `caller`/`callee`
descriptors, caller `dex_entry`, `opcode`, and `instruction_offset` in **16-bit code units from
the method's first instruction**, not a file offset. `target_dex_entry` and `target_resolution`
describe whether the declared operand has a definition in the supplied files. Incoming queries
may target external methods; outgoing queries require a definition. Rows sort by DEX entry,
class, caller descriptor and instruction position before pagination.

```text
asc_query_dex_session(session_id="...", operation="find_method_refs", method_descriptor="Lcom/example/Main;->check(I)Z")
asc_query_dex_session(session_id="...", operation="get_method_calls", method_descriptor="Lcom/example/Main;->check(I)Z")
```

These scan declared method operands, not resolved runtime targets. Counts report scanned methods
and instructions, declarations without code, undefined operands and dynamic sites. Polymorphic
calls preserve their call-site prototype; dynamic sites include at most 20 diagnostic examples.
`instruction_scan_complete` means the selected scope was decoded, not that a runtime call graph
is complete. Virtual dispatch, reflection, JNI and runtime-loaded code remain unresolved. Unknown
instructions or decoding failures return an error rather than partial results marked complete.

Only explicit Java source queries start the optional JVM (512 MiB maximum heap), sharing the
worker's timeout, aggregate memory, output and cancellation limits. Other JADX versions are rejected.
Reference pages expose `total`, `offset`, `limit`, `next_offset`, `truncated` and `has_more`.
For method references, field references, outgoing calls and fuzzy member references, `limit`
is a maximum: a page can stop earlier at the same 256-KiB encoded DEX-response budget.
Such pages report `page_limited_by="response_bytes"` and `response_byte_limit`; follow
`next_offset`, not `offset + limit`, to retain every site. A complete row or metadata that
cannot fit still returns `response_limit`. The API takes DEX inputs/sessions, not an APK path.

Development grouped references: `asc_query_dex_session(reference_format="grouped")`
returns `groups` containing `caller`, `dex_entry`, `target_field`, first-appearance-ordered
deduplicated `matches`, and every original `evidence` row. Each evidence row's `target_index`
selects its target from `matches`; restore it under `target_field`. Restore caller/DEX and
the optional shared `offset_unit` from the group header. This applies to method,
field, outgoing, fuzzy member, literal string and explicit type-operand references.
The default remains flat. In grouped mode `limit` counts caller groups, while `total`,
`offset`, `next_offset` and `returned_sites` count individual sites. A large caller can
span multiple byte-bounded pages. Continue with `cursor=next_cursor`, unchanged selectors
and `offset=0`; the page limit may change. Cursors are versioned and bound to the session,
query and immutable preparation/runtime identity; closing or expiring the session ends
their lifetime. Group evidence in response order reconstructs the original flat stream,
including duplicates. No new release or benchmark parity is implied by this development API.

### Indexed investigation

`operation="get_call_graph"` explores an exact `method_descriptor` with
`direction="incoming"|"outgoing"|"both"` (default both), `depth=1..5` (default 2),
`max_nodes=1..500` (default 200) and `max_edges=1..1000` (default 500).
Without an existing session index it scans bounded BFS frontiers, validating every instruction
without first materializing all APK call sites (`backend="native-dex-frontier"`, no `index`
field). Exact-page reuse is reported by `query_cache.hit`, not by a fabricated index flag.
Existing calls-only or complete xref indexes remain reusable. Explicitly configuring the durable
xref cache opts into the original calls-only build/restore path. Unusually dense frontiers fall
back to an atomic disk-bounded calls-only index; no field/type index is built just for a graph.
Preparation and either scan/index cost are included in cold measurements, not hidden in readiness.
Nodes retain minimum hop distance and definition DEX; edges retain **individual call sites**
including repeated calls, original opcode, offset and target provenance. Cycles and recursive
calls terminate without duplicate call sites. External method operands can be roots too.
Graph exploration has a 128 KiB content budget, separate from ordinary pagination.
`truncation_reasons` distinguishes depth, node, edge and byte boundaries;
`traversal_complete_within_depth` describes only the requested static neighborhood.
Expand boundary descriptors as new roots or raise budgets to investigate further;
node `expansion_status` identifies expanded, pending and depth/budget-boundary methods.
`offset` must be zero and ordinary `limit` does not control graphs. Diagnostics count dynamic
sites only in returned nodes (at most 20 examples), including unresolved invoke-custom targets;
these do not become fabricated call edges. Runtime dispatch remains unresolved.

`build_xref_index` scans all supplied DEX files once and atomically publishes a bounded SQLite
index. Subsequent exact method/field references reuse it without rescanning. `find_type_refs` builds/reuses it
and separates `type_relation=instruction|declaration|annotation|all`, including nested annotation
type values. Types and arrays match exactly, not by assignability or array component expansion.
`search_members` discovers full method/field declarations without knowing their class first:

```python
asc_query_dex_session(session_id="...", operation="search_members", kind="method", value="->check(")
asc_query_dex_session(
    session_id="...",
    operation="find_type_refs",
    type_descriptor="Lcom/example/Main;",
    type_relation="annotation",
)
```

Search uses a case-sensitive literal substring of the full descriptor, not a regex. An optional
`class_name` restricts its exact owner. Feed returned descriptors unchanged into exact references
or Smali queries. Searching declarations is not searching DEX string pools or runtime usages.
Member discovery reads declarations only and does not build the full xref index. Use
`operation="search_strings", value="https://"` for case-sensitive literal DEX string-pool
search with `dex_entry`, `string_index` and `value` provenance; pool presence is not a use site.
Both discovery operations return `instruction_scan_complete=false`.

Added in 0.2.4: pass a discovered string unchanged to
`operation="find_string_refs", value=...` for literal const-string/jumbo use sites.
It returns caller, opcode, string index and code-unit offset without building an index;
`case_sensitive=false` enables case-insensitive substring matching. Pages retain a complete
scan count; pool-only/encoded initial values are not instruction use sites. Existing
`find_refs` remains the legacy regex/name-level interface.

Use `search_refs` for a single-pass union of matching reference sites, without first enumerating
declarations or building a full index. For example:

```python
asc_query_dex_session(
    session_id=sid,
    operation="search_refs",
    kind="method",
    class_name="java.lang",
    fuzzy_class=True,
    value="equal",
    member_match="name",
)
asc_query_dex_session(
    session_id=sid,
    operation="search_refs",
    kind="field",
    class_name="android.os.Build",
    target_descriptor="Ljava/lang/String;",
    access="read",
)
```

`member_match` selects `name` (literal substring), `exact_name`, `prototype` (method prototype
substring), or `descriptor` (literal
substring of the complete identity). `case_sensitive` defaults to true; `fuzzy_class` applies a
literal owner substring rather than a regex. Omit `value` to select an owner; either a value or
an owner is required. `target_descriptor` filters an exact method prototype or field type.
`matched_targets` counts referenced identities, not unused declarations. Pagination spans the
entire union, preserving exact descriptors and checked instruction boundaries.

Session preparation reports actual validation progress over MCP. It snapshots and checks input
integrity and the class directory, but defers heavy indexes until requested. It does not hide
unvalidated data behind a successful response or start background whole-program decompilation.

A resident cache holds up to 32 serialized pages / 4 MiB per session (256 KiB per
page). It avoids worker startup for repeated exact pages, and invalidates on implementation,
engine or index-file identity changes. It never retains parsed DEX or worker processes.
Selected method, field, outgoing-call, fuzzy-reference, string and operand-only type
queries also stream complete matched site sets to private session storage. Later pages
reuse that checked set rather than scanning the input again. This cache reserves at most
32 MiB per session, with a 16-MiB entry/build limit, within
`DROIDASC_MCP_MAX_DEX_SESSION_BYTES`. Reservation is lazy;
insufficient space, oversized sets or cache failures preserve the normal scan path.
Selected rows use independently compressed, bounded blocks; public flat rows and page
offsets are unchanged. Compression does not relax entry, session or response-size limits.
First-query cost includes writing and checking the complete selected set. Reuse reports
`query_cache.scope=selected_reference_set`, its reserved budget and retained bytes.
Input/backend changes invalidate reuse; session close/expiry removes the stored sets.
All 18 tools expose typed MCP output schemas, including nested result rows and diagnostics.

Index construction costs time/disk upfront. Default per-session index quota is 512 MiB of disk, reserved
from the session storage budget; large applications may need an explicitly larger index quota,
session budget and timeout. Cancellation, malformed input or quota failures do not publish a
partial index. Identity includes input hashes, schema and backend files. Close/expiry/server
shutdown deletes the working copy. By default, one-shot indexes are temporary too.

To retain reusable indexes across sessions and server restarts, explicitly set
`DROIDASC_MCP_XREF_CACHE_DIR` to a dedicated private directory (0700 on POSIX; private ACLs on
Windows). This opt-in store retains derived identifiers and relationships, not the original APK.
It is keyed by ordered input hashes, schema, index scope and native parser source hashes.
Reopening still validates the supplied DEX files; a matching complete index is copied into the
new session and checksum-verified before use. Exact references and member discovery restore an
available index without rebuilding it. `index.durable_cache` reports `stored`, `restored`,
`not_accessed`, `disabled` or `too_large`; session working copies still have `session_lifetime`.

The durable store defaults to 1 GiB (`DROIDASC_MCP_MAX_XREF_CACHE_BYTES`), 64 entries and seven
idle days (`DROIDASC_MCP_XREF_CACHE_TTL_SECONDS`). These bytes are separate from the session
reservation. Reads/writes serialize across processes; TTL/LRU cleanup runs on cache access.
Checksums, incomplete-write cleanup and atomic publication protect against interrupted writes;
eviction does not invalidate active session copies. Large indexes need sufficient limits in both
stores. Cache misses keep the ordinary streamed discovery/reference path; they do not force a
full build. Stop servers before manually removing the dedicated cache directory.

The server also exposes initialization instructions, `droidasc://analysis-guide`, and
`triage_apk` / `trace_exact_method` prompts. Artifact contents remain untrusted query data.
`trace_exact_method` accepts either a full `method_descriptor` or exact `class_name` plus
`method_name`; optional `target_descriptor` selects an overload prototype. It normalizes
selectors for direct query handoff and keeps ambiguous names explicit until resolved.
See the [source-backed competitor comparison](docs/AIMARD_COMPARISON.md) for remaining gaps.

### Optional Rust ASC

Run `uv run python scripts/setup_rust.py` with Rust installed, then set
`DROIDASC_MCP_RUST_ASC` to the resulting `artifacts/rust_ASC/target/release/rust_ASC`
(`rust_ASC.exe` on Windows). The setup script pins source and radguard revisions.
Select `backend="rust_asc"` on the manifest, class-list, class-source or APK-reference tool.
Python ASC remains the default; no silent fallback occurs. Rust does not provide our exact DEX
index/Smali queries or `extends`/`impl` path. Its upstream reference scanner can discard per-DEX
failures, so results explicitly report unverified coverage: zero hits are not absence proof.
Both engines share scope/concurrency/process-tree budgets. See [backend details](docs/RUST_BACKEND.md).

## Configuration

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `DROIDASC_MCP_ALLOWED_ROOTS` | current directory | Allowed roots, separated by `os.pathsep` (`:` on Unix, `;` on Windows) |
| `DROIDASC_MCP_TOOL_PROFILE` | `legacy` | `legacy`, opt-in `artifact_preview` (generic code bridge) or `artifact` (focused DEX tools); old calls stay valid |
| `DROIDASC_MCP_TIMEOUT_SECONDS` | `180` | Per-operation timeout |
| `DROIDASC_MCP_MAX_APK_BYTES` | `2147483648` | Maximum APK size or combined DEX input size |
| `DROIDASC_MCP_MAX_OUTPUT_BYTES` | `67108864` | Captured stdout limit and aggregate decoded snapshot budget |
| `DROIDASC_MCP_MAX_WORKER_MEMORY_BYTES` | `2147483648` | Worker-tree budget (Windows Job aggregate; POSIX per-process address-space cap plus aggregate RSS watchdog) |
| `DROIDASC_MCP_MAX_PAGE_SIZE` | `1000` | Maximum lines returned by one call |
| `DROIDASC_MCP_MAX_PARALLEL` | `2` | Maximum concurrent ASC subprocesses |
| `DROIDASC_MCP_MAX_DEX_SESSIONS` | `4` | Maximum open/preparing DEX sessions |
| `DROIDASC_MCP_DEX_SESSION_TTL_SECONDS` | `1800` | Idle session expiry |
| `DROIDASC_MCP_MAX_DEX_SESSION_BYTES` | `4294967296` | Session storage, index/reference-cache budgets and concurrent preparation reservations |
| `DROIDASC_MCP_JADX_HOME` | unset | Optional JADX 1.5.5 distribution directory |
| `DROIDASC_MCP_DEXLIB_HOME` | unset | Standalone Google Smali 3.0.9 JAR directory, for DEX 041 normalization only |
| `DROIDASC_MCP_JAVA` | `java` on PATH | Optional JDK 17+ executable |
| `DROIDASC_MCP_MAX_XREF_INDEX_BYTES` | `536870912` | Per-session index disk quota/reservation, not resident memory |
| `DROIDASC_MCP_RUST_ASC` | unset | Optional Rust ASC executable path |

## Design

- Uses the public `droidasc` CLI module entry point; it does not import ASC private internals.
- Never invokes a shell and does not expose a generic command tool.
- Drains stdout and stderr concurrently with hard capture caps; no bulk output files are created.
- Caps stderr at 64 KiB and budgets page content conservatively within 256 KiB.
- Runs ZIP inspection and hashing in a supervised worker under the same concurrency budget.
- On POSIX, kills the operation's process group on completion or failure, even if its leader exited.
- On Windows, assigns the worker to a kill-on-close Job Object before starting ASC. Cleanup
  includes descendants even after the worker exits; Job setup failure prevents analysis from starting.
- Propagates MCP request cancellation through queue/snapshot waits and active sync tools; cleanup
  completes before the cancelled server task exits, and the session can continue serving requests.
- Applies the configured worker memory ceiling before importing ASC. Windows limits aggregate
  committed memory for the Job tree. POSIX applies an inherited per-process kernel `RLIMIT_AS`
  and samples aggregate tree RSS every 50 ms, terminating the tree if it crosses the same budget.
- Resolves symlinks before checking the allowed-root policy.

ASC and its dependencies still parse untrusted binary input. Use a container or disposable VM for
hostile APKs. This adapter is a process boundary, not a malware sandbox.

Native Windows CI checks live-parent and orphan cleanup, including grandchildren, successful
completion, output overflow, reader termination, and repeated-operation handle counts.
Capture buffers, snapshots being built, and active pages can coexist with the cache; this budget
is not a hard MCP-host total-RSS cap. The POSIX aggregate tree check is a sampled watchdog, while
the inherited per-process address-space ceiling is kernel-enforced. Dense outputs may hit the
decoded-memory budget before the wire cap.

## Development

See [local acceptance checks](docs/VALIDATION.md) for real-process tests, optional APK transport
checks, measured outcomes, and the remaining verification limits.

```bash
uv sync --locked --extra dev
uv run ruff check .
uv run pytest --cov --cov-report=term-missing
uv run python scripts/validate_corpus.py /path/to/one.apk /path/to/another.apk
uv run python scripts/stability_check.py /path/to/one.apk --duration 300 --workers 2
uv build
# Python 3.12+; use fresh dist outputs matching the current version:
uv run python scripts/verify_dist.py dist/droidasc_mcp-0.2.5.tar.gz dist/*.whl
```

## License

Apache License 2.0. Droid ASC is a separate upstream project and retains its own copyright and
license.
