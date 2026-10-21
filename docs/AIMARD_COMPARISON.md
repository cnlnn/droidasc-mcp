# aimardcr/asc-mcp: source-backed comparison

Reviewed: 2026-10-21. Competitor commit:
[`848c711f1d80a1c2577283f1fa5f475ff734aa40`](https://github.com/aimardcr/asc-mcp/tree/848c711f1d80a1c2577283f1fa5f475ff734aa40).
Our original baseline was `8cab43f4159ddc7252322f12a831dd98146d88d6`; the measured
index, type relationships, optional Rust backend and workflow-guidance changes
are now committed in `a96ea4c`, discovery/page-cache changes in `88de70b`, and
opt-in cross-restart index persistence in `9712467`.
This report is not a claim of complete parity, a performance victory, or a release gate.
No competitor implementation was copied into our package.

## What the stars do and do not establish

The GitHub repository API returned **19 stars / 2 forks** for aimardcr/asc-mcp and
**15 stars / 2 forks** for cnlnn/droidasc-mcp during this review. The difference is
four stars, not evidence that either engine is more correct, faster, or safer.
The API does not establish why people starred either repository. Attribution,
discovery, documentation and install friction are hypotheses to measure, not a
causal explanation to invent. [Competitor repository](https://github.com/aimardcr/asc-mcp),
[our repository](https://github.com/cnlnn/droidasc-mcp).

The present competitor is **not merely the earlier thin wrapper**: its pinned
implementation includes structured artifact sessions, 25 purpose-specific tools,
typed outputs, direct DEX query code, a worker runtime, tests and benchmark gates.
Its broader investigation workflow is a real product advantage worth adopting.
[Tool implementation](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/server.py),
[service implementation](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py),
[test workflow](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/.github/workflows/tests.yml).

## Independent execution performed

Cloned the pinned repository under ignored `artifacts/aimard-asc-mcp`; the clone's
tracked worktree remained clean after execution. Used an isolated uv environment,
not our product environment, with Python 3.13.11 on Linux, asc-mcp 0.2.0,
Androguard 4.1.4, MCP 2.2.0 and mutf8 1.1.0:

```sh
uv run --no-project --with ./artifacts/aimard-asc-mcp python artifacts/aimard-asc-mcp/tests/run_tests.py --require-decompiler --suite all
```

Result: **52 tests passed, zero skips, 4.898 seconds**, exit 0. This includes the
competitor's synthetic APK/DEX/JAR/AAR integration checks and its real stdio smoke
test. It does not establish performance on our production APK corpus, Windows
behavior, HTTP transport correctness, hostile-input isolation, or signed production
APK verification. The competitor's CI file currently selects Ubuntu and Python
3.10/3.11/3.12; its startup/reference performance gates were inspected but not
executed here. [Test runner](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/tests/run_tests.py),
[MCP integration tests](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/tests/test_mcp_server.py),
[CI scope](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/.github/workflows/tests.yml).

## Confirmed useful implementations

### Large-APK latency measurement

On 2026-10-21, ran the pinned competitor unchanged through real stdio MCP against
the same Taobao 10.62.0 APK (91,402,818 bytes, 12 DEX files, SHA-256
`2d8844a2cefecb8b99f5e8dc83e3eabba39391b02e2dc27c562d8ba3d0755348`).
Each scenario started a fresh server. Explicitly selected one worker for
deterministic cache reuse rather than the default four; OS file caches were not
dropped. Timings exclude server initialization and the separate artifact-open
call (0.19-0.26 seconds). External 120-second/4-GiB safety limits did not trigger.

| Competitor operation | First call | Repeated calls |
| --- | --- | --- |
| Method declaration name contains `equals` | 4.4848 s | 0.3250 / 0.3263 s |
| Exact `String.equals(Object)` references | 4.5192 s | 0.0669 / 0.0674 s |
| Exact `Build.MODEL:String` references | 3.5706 s | 0.0666 / 0.0712 s |

The member search returned 1,440 declarations; the reference tools returned
9,342 and 417 caller rows respectively. These are NOT equivalent to our 24,461
and 332 instruction rows. The field discrepancy is resolved below; the method
comparison still requires an independent oracle. Source APK hash remained unchanged.
Local evidence and repeatable harness are in ignored
`artifacts/reverse-acceptance/aimard-taobao-benchmark.json` and
`artifacts/reverse-acceptance/benchmark_aimard.py`.

Our prior 460.0459-second result is a full method/field/type/annotation relationship
index build, not equivalent work. Our existing non-indexed exact method/field
queries took 9.8224/7.3267 seconds on this APK. Nevertheless, forcing member
discovery to build that full index is an avoidable interactive-latency defect.
The candidate now implements declaration-only discovery and bounded exact-page
caching. On the same APK, member descriptor search `->equals(` took **4.0018 s**,
with repeats at **0.3183-0.6646 s**; string-pool discovery took **2.5270 s**, with
repeats at **0.3156-0.4198 s**. Member matching differs from the competitor's
case-insensitive name search, so this is not an identical-query speed victory.
Our exact method/field first queries remained slower at **8.6978 / 9.3805 s**,
with identical-page repeats **0.2533-0.3975 s**. The separate immutable session
open took **12.8858 s**; do not hide that cost in end-to-end comparisons.
See [local acceptance](VALIDATION.md#interactive-discovery-and-exact-page-reuse).
The full index is no longer a prerequisite for ordinary discovery. Type-relation
queries still build/reuse it. A full competitor call-graph build has not been timed here.

An additional opt-in durable index cache now reuses a completed full index across
server restarts. On the same APK, a fresh server restored the 2.19-GiB index and
queried all 332 field-reference rows in **3.3324 seconds**, with Java intentionally
unavailable. The separate session preparation took **12.0965 seconds**; the first
build/publication took **471.5827 seconds**. This avoids repeated full builds, not
the initial cost or session validation. See the [completion audit](VALIDATION.md#durable-cache-completion-audit)
for limits, full-row equality and independent process-lifetime evidence.

### Confirmed field-reference false positives

Independently decoded all 606,974 declared methods / 12,495,817 instructions in
the same APK with Androguard 4.1.4, without using either scanner's hit list to
select methods. Normalized byte offsets against our 16-bit code-unit offsets and
compared complete `(DEX, caller descriptor, offset, opcode)` sets for the exact
`Landroid/os/Build;->MODEL:Ljava/lang/String;` operand:

| Implementation | Instruction hits | Distinct callers | Extra / missing vs oracle |
| --- | --- | --- | --- |
| Independent sequential decoder | 332 | 320 | baseline |
| Our dexlib2 instruction scan | 332 | 320 | 0 / 0 |
| Pinned competitor scanner | 429 | 417 | 97 / 0 |

Raw DEX `code_item.insns_size` confirms **96 extra hits are outside the claimed
method's instruction array**. One additional hit is inside a `fill-array-data`
payload, not an executable field instruction. The source cause is specific:
`InsnLocator` maps offsets to coarse 16-byte buckets, records only method starts,
and regex-verifies instruction lengths without checking the exact method end;
its fixed-width `nop` pattern also does not skip variable-length payloads.
The byte-level prefilter is useful, but these missing boundary checks must not
be adopted. [Locator source](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/core/findrefs/locator/insn_locator.py),
[prefilter source](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/core/findrefs/scan/code_item_scan.py).

A public independent [Smali fixture](../tests/fixtures/xrefs/boundary/Boundary.smali)
reproduces both errors without the private APK: `aNoReference` has only
`return-void`, but the next code item's register-count bytes look like `sget`;
`cPayload` holds matching bytes as short-array data. The competitor reports these
at byte offsets 4 and 24 plus the real `dReal` reference at 0. Our streamed and
indexed queries return only `dReal`, as enforced by
`test_field_opcode_bytes_in_payload_and_adjacent_header_are_not_references`.
This establishes a concrete correctness advantage for this query and these
fixtures, not universal superiority. The competitor checkout remained unchanged.
Private complete evidence is retained in
`artifacts/reverse-acceptance/field-reference-oracle.json` with its repeatable
`audit_field_refs.py` harness; neither is shipped.

### Confirmed call-graph integration failure

The same unchanged competitor, using Androguard 4.1.4, was also exercised through
real stdio MCP on our public source-built Android fixture. Opening the APK
succeeded; `apk_get_call_graph` for
`org.example.droidascfixture.MethodCases.choose(I)Ljava/lang/String;` at depth 1
returned `isError=true` with `'list' object has no attribute 'get_class_name'`.
The index builder calls `dex.get_cm_method(...)`, which returns a list in this
dependency version, then invokes object-style accessors on it. This fails before
graph expansion; the implemented graph feature therefore did not pass this
integration check. Its 52 passing synthetic tests do not cover this real-library
contract. [Index builder](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L141-L173).

The boundary-reference fixture was independently repeated through real stdio MCP
in the same run and reproduced both extra callers. Local evidence is
`artifacts/reverse-acceptance/check_competitor_regressions.json`; the corresponding
`check_competitor_regressions.py` harness uses only our public fixtures. This does
not establish that our one-hop tools implement the competitor's multi-hop API;
bounded graph exploration remains a separate feature gap.

| Area | What the pinned implementation actually does | Our status / next action |
| --- | --- | --- |
| Agent routing | Server instructions distinguish declarations, string-pool matches, const-string use sites and type operands; each parameter has a description; read-only tools have MCP annotations. | Candidate now has initialization instructions, an analysis-guide resource, two prompts and annotations distinguishing read-only queries from session state. Per-parameter guidance and typed output contracts still need alignment. |
| Target discovery | `search_members` searches method/field declarations and returns full descriptors; `search_strings` searches the DEX pool with DEX name and string index. | Candidate now has declaration-only method/field discovery and DEX string-pool search, with explicit case-sensitive literal semantics and provenance. Neither scans instructions or builds the full index. |
| Query reuse | Resident workers cache parsed DEX and complete reference result sets by path/size/mtime; the reference cache has an eight-key LRU. | Candidate reuses exact query pages by immutable input/backend identity, capped at 32 pages / 4 MiB and charged to the existing index reservation. Different pages may rescan; isolation and byte bounds are retained, but warm queries remain slower than its resident cache. |
| APK contents | Sorted entry inventory, asset/resource reads, binary XML decoding and native-library ABI inventory. | Our baseline APK info does not replace this workflow. Add bounded reads with provenance and explicit decoding/truncation status. |
| Manifest analysis | Package/SDK/component structure, inherited application permission, and separate effective provider read/write permissions. | Raw XML is available; structured summaries would reduce client parsing mistakes. Do not equate an absent exported attribute or permission with a confirmed exposure. |
| Calls and hierarchy | Source implements full method prototype selection, overload rejection, cached adjacency and depth 1-3 exploration, but real call-graph execution failed as documented above. Direct interfaces/subclasses and superclass chain are also implemented. | Our exact one-hop edges are more explicit about evidence, but are not yet a multi-hop investigation operation. Reuse our index for a bounded, provenance-preserving graph. |
| Signing | Androguard signing-scheme presence and certificate metadata/fingerprints. | Useful missing triage metadata. Scheme presence must not be advertised as cryptographic verification. |
| Formats | APK/raw DEX; directly embedded DEX in JAR/AAB/APKS/XAPK/ZIP; JVM `.class` inventory, including embedded JARs such as AAR `classes.jar`. | Our raw DEX and APK paths should evolve toward capability-based containers without falsely promising split-APK reconstruction or JVM decompilation. |
| Version comparison | Class inventory added/removed sets and common count. | Useful, but not a code/behavior diff. A bounded inventory comparison can precede later method-body or manifest comparisons. |

Primary implementation references for the table:
[routing/schema](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/server.py#L42-L148),
[declaration and string search](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L506-L547),
[manifest permission semantics](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L291-L355),
[graph](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L605-L659),
[contents and signing](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L661-L786),
[format capability detection](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/sessions.py#L88-L161),
[JVM inventory](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L191-L213),
[class diff](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L896-L917).

## Boundaries not to copy blindly

Unless explicitly linked to an execution result above, these are source observations,
not reproduced vulnerability claims:

- The reusable `ProcessPoolExecutor` awaits jobs without an explicit per-operation
  timeout, aggregate memory budget, output byte cap or process-tree cancellation
  mechanism in `AnalysisRuntime`. Session count/TTL limits are not present in its
  registry. Our supervised fresh-worker timeout/memory/output/cancellation and
  bounded immutable session lifecycle are valuable properties to retain.
  [Runtime](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/runtime.py),
  [registry](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/sessions.py),
  [our supervisor](../src/droidasc_mcp/runner.py), [our sessions](../src/droidasc_mcp/sessions.py).
- It hashes artifacts at open but subsequent session checks and reusable caches
  use size/mtime, not immutable content snapshots. Cache entry counts are bounded;
  this is not a total-byte bound. Our per-session copied evidence and source hashes
  should not be weakened merely to emulate resident-cache speed.
  [Session checks](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/sessions.py#L163-L176),
  [cache keys and cached parsed DEX](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L90-L173).
- Graph depth is bounded, but emitted node/edge cardinality is not separately
  capped. The index handles `invoke-*` as method references; special dynamic
  instruction coverage is not separately declared here. Do not inherit that as
  a runtime-resolution guarantee. Our graph must preserve external and unresolved
  dynamic diagnostics and expose fan-out truncation. The real MCP graph failure
  above concerns an ordinary method-reference API contract, not proof of dynamic
  instruction coverage.
  [Index](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L141-L173),
  [depth expansion](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L632-L659).
- `resource_content` permits archive members up to 64 MiB, reads the complete
  member, then slices to `max_bytes`. Binary XML conversion occurs after that
  slice; input byte bounds are not necessarily decoded-output bounds. Retain
  streaming/bounded-output behavior, and never label truncated binary XML as a
  successfully complete document.
  [Resource read](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L689-L740).
- `apk_scan_secrets` applies five regular expressions to DEX strings. Results are
  candidate pattern matches, not evidence that credentials are live, sensitive,
  or exploitable. It does not inspect every archive resource. Native-library
  output is an archive inventory, not ELF symbol or native-code analysis. Signing
  output collects scheme/certificate metadata rather than running an APK
  signature-verification tool.
  [Secret patterns](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L21-L28),
  [secret scan](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L788-L814),
  [native/signing](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/service.py#L742-L786).
- Its type-reference tool intentionally covers explicit type operands, not all
  declaration, annotation, signature, field or method-owner relationships. Our
  candidate typed index is broader in that particular dimension, but remains
  static evidence, not reflection/JNI/runtime class loading coverage.
  [Type-tool scope](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/server.py#L123-L148),
  [our typed index bridge](../src/droidasc_mcp/IndexBridge.java).

## Prioritized implementation and acceptance

The list is an explicit remaining-work inventory, not a completion checklist with
implicit green marks. Complete the existing index/Rust/cross-platform objective
without sacrificing its evidence gates while adding these bounded slices.

| Priority | Slice | Acceptance that establishes a useful improvement |
| --- | --- | --- |
| P1 | Agent-readable routing and schemas | Initialize instructions, resource and prompts must travel over real stdio and HTTP; every public argument describes units, scope and semantics; schema constrains incompatible inputs; zero-hit explanations do not imply absence of behavior. |
| P1 | Discovery before exact references | Method and field declarations plus DEX string-pool search, source DEX/index provenance, literal and case behavior explicitly defined, paging before output limits; overload/constructor/Unicode/array/multidex fixtures; found identities round-trip unchanged into exact xrefs and Smali. |
| P1 | APK inventory and content | List assets/resources/native entries with ABI and size; bounded text/binary read and binary-XML decoding; duplicate names, traversal, oversized/invalid ZIP members, malformed XML and cancelled workers rejected or explicitly partial; original SHA-256 unchanged; no filesystem extraction needed for reads. |
| P2 | Structured manifest triage | Preserve declared values separately from computed values; exercise application inheritance, provider read/write precedence, aliases and intent filters; distinguish unsupported defaults/resource references from known values; no automatic vulnerability finding. |
| P2 | Indexed multi-hop static call graph | Direction, depth, node/edge budget and continuation/truncation explicit; cycles, recursion, overloads, external targets and invoke-custom/polymorphic handled without runtime overclaim; same edges before/after source reads; independent bytecode oracle; large-APK cold/warm evidence. |
| P2 | Signing and certificate inventory | Compare known signed/unsigned/multisigner/tampered APK fixtures with an independent signing tool; separate block presence, certificate fingerprints and cryptographic verification; unsupported schemes reported, not guessed. |
| P2 | Capability-based archive inputs | DEX-JAR, pure JVM JAR, AAR classes.jar and AAB direct DEX fixtures; nested split APKs explicitly unsupported until implemented; archive/nested byte budgets; malformed container and duplicate class diagnostics; do not silently treat JVM inventory as decompilable DEX. |
| P3 | Revision inventory and candidate secrets | Hash-bound sample pairs, sorted paginated class/member changes; unchanged inventory must not mean unchanged behavior. Redacted candidate-only secret matches with precise source locations; never probe real credentials automatically. |

### Candidate guidance acceptance during this review

The new [workflows module](../src/droidasc_mcp/workflows.py) is wired into
[server construction](../src/droidasc_mcp/server.py). Independent rerun of
`uv run pytest tests/test_server.py -q` returned **3 passed**. A separate real
`stdio_client` / `ClientSession` launch of `python -m droidasc_mcp` verified:
initialization instructions include code-unit semantics; prompt listing contains
`triage_apk` and `trace_exact_method`; reading `droidasc://analysis-guide` and
retrieving the exact-method prompt succeed. HTTP and complete parameter-schema
parity were not established by this narrow check.

## Definition of better

Do not optimize for tool count or README adjectives. The defensible target is a
shorter investigation from an unknown artifact to a precise, independently
checkable result: discover a target, preserve its identity, traverse references,
read exact evidence, explain incomplete coverage, and release resources. Compare
the same fixtures, limits, transport, cold/warm state and host. Publish correctness
and memory/latency data including failures. Current evidence supports specific
strengths and concrete gaps; **it does not yet support "better in every area."**
