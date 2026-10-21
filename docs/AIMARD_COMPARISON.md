# aimardcr/asc-mcp: source-backed comparison

Reviewed: 2026-10-21. Competitor commit:
[`848c711f1d80a1c2577283f1fa5f475ff734aa40`](https://github.com/aimardcr/asc-mcp/tree/848c711f1d80a1c2577283f1fa5f475ff734aa40).
Our committed baseline was `8cab43f4159ddc7252322f12a831dd98146d88d6`, plus the
in-progress index, type relationships, optional Rust backend and workflow-guidance changes.
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

| Area | What the pinned implementation actually does | Our status / next action |
| --- | --- | --- |
| Agent routing | Server instructions distinguish declarations, string-pool matches, const-string use sites and type operands; each parameter has a description; read-only tools have MCP annotations. | Candidate now has initialization instructions, an analysis-guide resource, two prompts and annotations distinguishing read-only queries from session state. Per-parameter guidance and typed output contracts still need alignment. |
| Target discovery | `search_members` searches method/field declarations and returns full descriptors; `search_strings` searches the DEX pool with DEX name and string index. | Candidate now discovers method/field declarations with literal search, full descriptors and DEX provenance, round-tripped into exact xrefs over both transports. It first builds the disk-bounded index; DEX string-pool discovery remains missing. |
| APK contents | Sorted entry inventory, asset/resource reads, binary XML decoding and native-library ABI inventory. | Our baseline APK info does not replace this workflow. Add bounded reads with provenance and explicit decoding/truncation status. |
| Manifest analysis | Package/SDK/component structure, inherited application permission, and separate effective provider read/write permissions. | Raw XML is available; structured summaries would reduce client parsing mistakes. Do not equate an absent exported attribute or permission with a confirmed exposure. |
| Calls and hierarchy | Full method prototype selection, overload rejection, cached caller/callee adjacency, depth 1-3 exploration; direct interfaces/subclasses and superclass chain. | Our exact one-hop edges are more explicit about evidence, but are not yet a multi-hop investigation operation. Reuse our index for a bounded, provenance-preserving graph. |
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

These are source observations, not reproduced vulnerability claims:

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
  dynamic diagnostics and expose fan-out truncation. No failure on dynamic
  instructions was reproduced in this review.
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
