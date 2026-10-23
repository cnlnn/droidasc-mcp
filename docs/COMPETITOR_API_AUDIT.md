# Competitor API Source Audit

Baseline: aimardcr/asc-mcp commit `848c711f1d80a1c2577283f1fa5f475ff734aa40`,
rechecked against GitHub main on 2026-10-23. This is a functional workflow map,
not a drop-in API-name compatibility promise or a blanket performance claim.

Read the actual [server](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/server.py),
[service](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py),
[session registry](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/sessions.py)
and DEX container/artifact-handler implementation, rather than deriving coverage from README names.
All public tools, resource templates, prompts and non-context parameter names are recorded below.
`scripts/audit_competitor.py artifacts/aimard-asc-mcp` checks this table against its Python AST
and commit, failing on missing, extra, duplicate or changed parameter entries. This inventory
check is not a substitute for the behavioral tests linked in each row.

## Complete Public Surface

| Kind | Competitor name | Parameters excluding ctx | Our equivalent workflow | Behavioral evidence |
| --- | --- | --- | --- | --- |
| tool | `load_artifact` | `path` | Raw DEX: asc_open_dex_session; archive: asc_inspect_artifact then asc_open_artifact_session when dex_analysis=true. Inventory-only inputs need no retained handle. SHA-256 and capability fields accompany results. | tests/test_dex.py; tests/test_containers.py; tests/test_dex_container.py |
| tool | `close_artifact` | `analysis_id` | asc_close_dex_session releases immutable preparations; stateless archive inventory needs no close. | tests/test_sessions.py; tests/test_integration.py |
| tool | `server_status` | `` | asc_ping reports effective roots, process/session limits, open_count, active_queries and opening_count. Capacity is supervised fresh workers, not a resident process pool. | tests/test_server.py; tests/test_sessions.py; tests/test_integration.py |
| tool | `apk_get_summary` | `analysis_id` | asc_inspect_artifact(include_summary=true) returns hash/size, container capabilities, selected DEX, entry count, bounded native ABIs and compact manifest package/version/SDK declarations in one response. Manifest status and ABI truncation/count are explicit; AAB selects one module. asc_manifest_summary adds component details; entry tools add library sizes. | tests/test_artifact_summary.py; tests/test_archive.py; tests/test_integration.py |
| tool | `apk_get_manifest` | `analysis_id,include_xml` | asc_manifest_summary plus paged decoded manifest resource. Preserve declared versus effective permissions; XML is opt-in through resource/read tool rather than duplicating it in every summary. | tests/test_archive.py; tests/test_integration.py |
| tool | `apk_list_classes` | `analysis_id,prefix,query,cursor,limit` | DEX list_classes or search_classes(value=query,case_sensitive=false,prefix=prefix); JVM inventory asc_inspect_artifact(class_query,class_prefix). Both dotted and Dalvik class names/prefixes, literal substring, offset/limit pagination. Manifest component names can be passed directly; results keep exact Dalvik identities. | tests/test_structure.py; tests/test_containers.py; tests/test_integration.py |
| tool | `apk_get_class_outline` | `analysis_id,class_name` | get_class_outline: flags/superclass, paged interfaces, fields with types/storage and methods with complete identities/flags/code/dispatch. | tests/test_structure.py; tests/test_integration.py |
| tool | `apk_get_class_source` | `analysis_id,class_name` | get_class_source; get_class_source_metadata adds original ASC token references with global code-point spans and a complete-source hash. Source links are not instruction xrefs. | tests/test_structure.py; tests/test_integration.py |
| tool | `apk_find_method_references` | `analysis_id,class_name,method_name,fuzzy_class,exact_name,descriptor,cursor,limit` | find_method_refs selects a full identity; search_refs(kind=method) scans a fuzzy owner/name union once, with optional exact prototype, omitted name, case mode and global pagination. | tests/test_native_dex.py; tests/test_methods.py; tests/test_integration.py |
| tool | `apk_find_field_references` | `analysis_id,class_name,field_name,fuzzy_class,exact_name,field_type,cursor,limit` | search_refs(kind=field) supports owner/name/type filtering in one pass; find_field_refs selects a full class->name:type. Read/write filters and checked individual instruction sites are preserved, without heuristic byte matches. | tests/test_native_dex.py; tests/test_methods.py; tests/test_integration.py |
| tool | `apk_find_type_instructions` | `analysis_id,type_name,cursor,limit` | find_type_refs with exact Dalvik type and type_relation=instruction. Dotted names become Lpkg/Type;. Broader pattern discovery uses class search before exact queries; declarations/annotations are separate optional relations. | tests/test_xref_index.py; tests/test_integration.py |
| tool | `apk_find_string_references` | `analysis_id,value,cursor,limit` | find_string_refs(value=literal) accepts a discovered string unchanged and returns checked const-string/jumbo sites, global pagination and explicit case mode. Legacy find_refs retains its regex semantics. get_string_constants provides class-scoped use sites; pool search alone is not a use-site claim. Included in consolidated v0.2.3; original v0.2.4 acceptance remains historical evidence. | tests/test_string_refs.py; tests/test_structure.py; tests/test_integration.py; scripts/verify_string_references.py |
| tool | `apk_search_members` | `analysis_id,kind,query,cursor,limit` | search_members(kind=method/field,value=query,member_match=name,case_sensitive=false). Includes declaring class, name, flags and full identity. Descriptor matching remains the backward-compatible default, explicitly distinct. | tests/test_structure.py; tests/test_xref_index.py; tests/test_integration.py |
| tool | `apk_search_strings` | `analysis_id,query,cursor,limit` | search_strings(value=query,case_sensitive=false), with original DEX entry/string index. Case-sensitive default remains available. | tests/test_structure.py; tests/test_xref_index.py; tests/test_integration.py |
| tool | `apk_get_string_constants` | `analysis_id,class_name` | get_string_constants exact class, all const-string/jumbo instructions and decoded Unicode/empty values, method identity and code-unit offsets. | tests/test_structure.py; tests/test_dex_container.py; tests/test_integration.py |
| tool | `apk_search_method_bodies` | `analysis_id,query,cursor,limit` | search_method_bodies(value=query,case_sensitive=false) searches canonical DAD opcode/operand text, including registers, numeric literals, switch/array payloads. Not source search or symbolic reference resolution. | tests/test_structure.py; tests/test_integration.py |
| tool | `apk_disassemble_method` | `analysis_id,class_name,method_name,descriptor` | disassemble_method accepts exact class_name plus method_name directly; target_descriptor optionally filters the prototype. Only a unique declared definition executes; ambiguous_method and candidate_count preserve ambiguity. Full method_descriptor remains available, including from list_methods/get_class_outline. Paged structured opcode/operands/code-unit offsets; get_method_source uses the same selection for Smali or explicit Java. | tests/test_method_selection.py; tests/test_structure.py; tests/test_methods.py; tests/test_integration.py; scripts/verify_method_selection.py |
| tool | `apk_get_class_hierarchy` | `analysis_id,class_name` | get_class_hierarchy reports superclass chain, direct interfaces/subclasses/implementors, external definitions and cycle diagnostics. | tests/test_structure.py; tests/test_integration.py |
| tool | `apk_get_call_graph` | `analysis_id,class_name,method_name,descriptor,depth` | get_call_graph accepts full method_descriptor or exact class_name plus method_name, with optional target_descriptor prototype; ambiguous selection fails before indexing/scanning. direction=both and depth 1-5 include competitor's 1-3. Independent node/edge/output caps preserve call-site offsets, external roots and unresolved dynamic sites. Bounded frontiers avoid mandatory full-index materialization; existing-index and dense-frontier fallback costs remain explicit. | tests/test_method_selection.py; tests/test_call_graph.py; tests/test_native_graph.py; tests/test_integration.py |
| tool | `apk_list_entries` | `analysis_id,kind,cursor,limit` | asc_list_apk_entries works for supported archives and standalone DEX, category/prefix/offset/limit. Standalone entries retain the original basename, size and whole-file hash, without ZIP CRC metadata or code-validation claims. AndroidManifest.xml is our separate manifest category. | tests/test_archive.py; tests/test_containers.py; tests/test_raw_dex_entries.py; tests/test_integration.py |
| tool | `apk_get_resource_content` | `analysis_id,path,max_bytes` | asc_read_apk_entry supports generic archives and original standalone DEX bytes, including physical 041 bytes, with bounded text/XML/base64. 128-KiB pages plus byte_offset/next_byte_offset reconstruct content larger than competitor's 1-MiB response cap; XML decoding and CRC status remain explicit. | tests/test_archive.py; tests/test_containers.py; tests/test_raw_dex_entries.py; tests/test_integration.py |
| tool | `apk_list_native_libraries` | `analysis_id` | asc_list_apk_entries(kind=native), all pages, ABI/original and compressed sizes. Archive inventory, not native-code disassembly. | tests/test_archive.py; tests/test_integration.py |
| tool | `apk_get_signing_info` | `analysis_id` | asc_signing_inventory: v1/v2/v3 certificate metadata and v3.1 presence; cryptographic_verification=not_performed. Do not convert mere block presence into valid signatures. | tests/test_signing.py; scripts/verify_signing.py; tests/test_integration.py |
| tool | `apk_scan_secrets` | `analysis_id,include_values,limit` | asc_secret_candidates covers the competitor's five pattern families plus GitHub tokens, include_values=false by default, explicit opt-in matched values, pages/fingerprints/source locations and scan limits. No automatic credential use. | tests/test_review.py; tests/test_structure.py; tests/test_integration.py |
| tool | `apk_diff` | `left_analysis_id,right_analysis_id` | asc_diff_dex_sessions for DEX classes/methods/fields; asc_inspect_artifact(compare_to=...) for JVM class sets/common counts. Mixed artifacts require both operations. All comparisons hash-bound; unchanged identities do not mean unchanged behavior. | tests/test_review.py; tests/test_containers.py; tests/test_integration.py |
| resource | `artifact://{analysis_id}/manifest.xml` | `analysis_id` | droidasc://artifact/manifest{?apk_path,offset,limit}, allowed-root checks and hash-bound paged JSON XML envelope. Percent-encode URI query values. | tests/test_integration.py |
| resource | `artifact://{analysis_id}/class/{class_name}` | `analysis_id,class_name` | droidasc://session/{session_id}/class{?class_name,offset,limit}, immutable session source with pagination/provenance. | tests/test_integration.py |
| prompt | `artifact_triage` | `analysis_id` | triage_apk plus common analysis-guide routing, capabilities and evidence boundaries. | tests/test_server.py; tests/test_integration.py |
| prompt | `trace_behavior` | `analysis_id,class_name,method_name` | trace_exact_method accepts class_name plus method_name directly, with optional target_descriptor prototype or a full method_descriptor. Selector validation/normalization uses the same query path; ambiguity resolution, source/disassembly/call-site and exact-page handoff are explicit. | tests/test_server.py; tests/test_integration.py |
| prompt | `compare_artifacts` | `left_analysis_id,right_analysis_id` | compare_versions includes declaration/body/manifest/resource/signing follow-up and untrusted-input quoting. | tests/test_server.py; tests/test_integration.py |

## Parameter And Format Rules

- Competitor cursor strings encode integer offsets; our next_offset is an integer. Follow pages,
  not tool-count equivalence. Default page sizes differ; both accept explicit bounded limits.
- Our DEX worker also caps encoded responses at 256 KiB. A valid row limit can still return
  response_limit; retry with a smaller limit at the same offset. The complete-reference
  verifier exercises that recovery and all subsequent pages without weakening the byte cap.
- Our empty member queries enumerate declarations; the competitor rejects them. Empty class
  queries use list_classes; an empty
  string/body search is intentionally rejected rather than returning every pool/instruction row.
- Method/field exact_name=false and fuzzy_class workflows use the single-pass `search_refs`
  union, including omitted member names and exact prototype/type filtering. Exact-reference
  operations resolve a unique declared definition for class/name selectors, or accept the
  complete identity directly; fuzzy results retain exact per-site identities.
- Competitor evidence offsets are caller-relative **bytes**; ours are **16-bit code units**.
  Multiply ours by two only when comparing the same instruction stream. Source token spans
  are Unicode code points; resource offsets are bytes. None is an absolute DEX file address.
- Both implementations inventory JVM classes and nested APKs without JVM decompilation or
  split reconstruction. Our first-level nested JAR inventory is bounded and rejects invalid,
  duplicate or unsafe paths instead of silently accepting ambiguous evidence.
- DEX 041 supports one or multiple logical files and shared physical string data through a
  strict validator and version-pinned dexlib2 normalization. Original hashes/header offsets
  and normalized-byte hashes are distinct. Normalized files share a total input byte limit
  and at most twice their source container size; imports are temporary and disk-reserved.
  [DEX format](https://source.android.com/docs/core/runtime/dex-format).
- Existing original-DEX strict checksum/table/class-count validation remains active. Normalization
  does not silently repair a malformed original container. Missing Java is an explicit backend error.
- Optional Rust remains an independently limited APK backend. No automatic fallback can silently
  change query semantics. Immutable sessions, cancellation, memory/output/disk limits and cache
  identity checks are retained rather than copied from the competitor's weaker boundaries.

## Acceptance Status

The development-branch compact-summary and direct trace-prompt additions pass the local
1213-test source suite on Linux Python 3.13, including real stdio/HTTP handoff and error
recovery. scripts/verify_artifact_summary.py compares real-MCP summary fields with the
pinned competitor and original ZIP/hash evidence on the private large-APK corpus.
These additions are separate from the frozen, published v0.2.3 acceptance. The subsequent
workflow/raw-DEX candidate e3f381927c98976d4b2052ec29e0d86136e47c48 passes CI
39967501671: all 25 jobs, Linux/Windows Python 3.10-3.13, 1264 source tests per cell
with zero failures/errors/skips, and the same count for each canonical-sdist/native-wheel
installation. Downloaded package/source identity and signing variants are checked separately.
The exact Linux wheel also independently verifies all 884805 original class/owner identities
and snapshot bytes across the three private APKs, plus every selected Taobao method/field
reference row and diagnostic over three rounds. Receipts are under
artifacts/workflow-entry-ci-39967501671. These are candidate gates, not release approval or
evidence of universal workflow/performance superiority.

The later real-stdio complete-reference exercise verifies all ordered method/field sites
for two selected identities across Taobao, WeChat and Douyin, including adaptive recovery
from response_limit, every successful continuation and scanner diagnostics. Independent
original DEX enumeration prevents the oracle from inheriting a missing source entry.
The final three receipts cover 98581 rows and 200 successful pages, with immutable
input/runtime/oracle identity and temporary cleanup; see VALIDATION.md. This is not a
full collection-latency comparison or all-query coverage. Current exact-page caches retain
offset/limit in their keys, so a new page still takes the scan path; that amplification
needs its own matched competitor measurement before claiming paging superiority.

The 2026-10-23 parameter exercise reads the pinned server's forwarding of `fuzzy_class`,
`exact_name`, `descriptor`/`field_type`, `cursor` and `limit` and checks the corresponding
selectors over both real transports. `test_native_fuzzy_references_without_java` now
checks all four exact/fuzzy owner/name combinations against exact-site responses for
both `pick` overloads and both `value:I`/`value:J` fields. It also checks omitted names,
case-sensitive misses, prefix-plus-substring class selection, complete one-row pagination
and beyond-end pages. This exercises combinations rather than counting parameter names.

`test_resource_content_continuation_over_transport` follows an inventory `next_offset`
to a path containing spaces and a plus sign, then follows nine `next_byte_offset` values
to reconstruct all 1,048,832 original binary bytes. Every page is bounded and hash-bound;
EOF, invalid-offset recovery, no retained session and unchanged input are checked. This
exercises the documented paged alternative to the competitor's larger single response,
not a same-call `max_bytes` compatibility claim. The four targeted stdio/HTTP cases pass,
zero skips: `artifacts/startup-next-20261023/workflow-parameters-targeted-fixed.xml`.
The initial resource-test failure was an incorrect test assumption about inventory order;
the final test follows the returned cursor instead. No runtime change was required.

Further source inspection of `service.py:list_entries/resource_content` identified an
actual standalone-DEX gap, not covered by archive-only equivalence. The candidate now
routes those two entry operations through the existing supervised worker and original
before/after file identity/hash checks. The file read is bounded to a page plus one
sentinel byte; inventory does not normalize 041 or validate code. Missing names,
unsafe paths, unsupported archive capabilities, invalid page selectors and changed inputs
fail explicitly. ZIP CRC fields are absent for a raw file. `asc_inspect_artifact` and archive
session loading retain their existing archive policy; raw analysis still opens DEX paths.
The targeted entry/archive/container/schema/real-transport selection passes 178 cases,
zero skips and 56 deliberate transport deselections:
`artifacts/startup-next-20261023/raw-dex-targeted-zero-skips.xml`.
The full current Linux Python 3.13 suite subsequently passes 1262 cases in 212.53 seconds,
zero failures/errors/skips: `artifacts/startup-next-20261023/source-full-raw-dex-entry.xml`.
Windows and canonical-package gates for this new runtime are separate from that local result.

`test_complete_investigation_handoffs_without_java[stdio/http]` exercises one connected
investigation, rather than independent calls with every descriptor hard-coded: capability
selection, manifest component to dotted class search, paginated outline to exact method,
disassembly/default Smali, outgoing operands to incoming/fuzzy references, discovered field
identity to field sites, constants/string/body search, hierarchy, bounded graph expansion,
class/manifest resources, native inventory, asset reads, signing, redacted secrets, revision
comparison, prompts, missing-method recovery and session/resource cleanup. Both transports
passed locally on 2026-10-22 with Java deliberately invalid and JADX/dexlib configuration unset.
The fixtures are assembled before disabling Java; fixture generation is not a runtime dependency.
That targeted receipt alone was not release approval. The subsequently withdrawn v0.2.5 passed all 17 CI
jobs on commit 1b25267d2f123b03d722509f56425da347031818, including both transports,
1096 tests per OS/Python cell without skips, and canonical-package acceptance. The next
input-integrity increment requires its own final-commit gates.

This matrix describes implemented equivalents and intentional interface differences. The release
authority is a fresh feature-frozen Linux/Windows matrix, real stdio/HTTP tests, independent signing
variants, stability checks and clean sdist/wheel installations. Receipts for the withdrawn original v0.3.0 do not
approve this candidate. See VALIDATION.md for the final commit/run-specific gate receipt.
Historical cold-reference timings do not describe this candidate's native scanner. Refresh the
same-condition runtime and independent accuracy receipts before claiming a performance advantage;
functional coverage must not be advertised as universal superiority.

Performance attribution also requires reading the execution topology. The pinned runtime's
outer ProcessPoolExecutor passes worker_count through server.py:_run to the artifact handler;
_for_each_findrefs creates an additional ProcessPoolExecutor with the same max_workers.
Matching the worker setting alone is not a total CPU ceiling. The current comparison harness
applies the same inherited logical-CPU affinity before either server imports, then verifies
owned descendants after transport startup. Old reports without cpu_budget_version=1 remain
configuration-matched historical evidence, not strict aggregate CPU-budget evidence. This
correction concerns benchmark resources, not a missing tool or a changed query contract.
