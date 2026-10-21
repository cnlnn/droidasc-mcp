# Android reverse-engineering MCP implementation comparison

Reviewed: 2026-10-21. This is a source-and-test inspection, not a performance benchmark. No competitor build scripts or test suites were executed. Statements marked source-verified mean the implementation was read; test descriptions mean assertions exist, not that they passed here. No competitor source was copied into this product.

## Pinned repositories

| Repository | Inspected commit | Relevant implementation |
| --- | --- | --- |
| [Qtty/jadx-mcp-server](https://github.com/Qtty/jadx-mcp-server/tree/4e6d890d1d3753d2bb47d492a9523ef98874df85) | `4e6d890d1d3753d2bb47d492a9523ef98874df85` | Python MCP adapter, shared JVM analyzer, DEX reverse index |
| [1013503897/jadx-headless-mcp](https://github.com/1013503897/jadx-headless-mcp/tree/e06a4ae20e5331258520855cabe755015ffb0dbd) | `e06a4ae20e5331258520855cabe755015ffb0dbd` | Kotlin MCP, one loaded JADX session, method/Smali tools |
| [subwire/jadx-mcp-server](https://github.com/subwire/jadx-mcp-server/tree/2b3e51cc115c914b2a311c64d95fd5f850c75fd3) | `2b3e51cc115c914b2a311c64d95fd5f850c75fd3` | Java MCP, UUID-addressed JADX sessions |
| [zinja-coder/jadx-ai-mcp](https://github.com/zinja-coder/jadx-ai-mcp/tree/9f4fce6f49902e95c62479c02d985d1eb0b3cbe1) | `9f4fce6f49902e95c62479c02d985d1eb0b3cbe1` | JADX GUI plugin backing the Python MCP bridge |
| [androguard/androguard](https://github.com/androguard/androguard/tree/3ea3da38e74b4d74579463d0688ab513786c4750) | `3ea3da38e74b4d74579463d0688ab513786c4750` | Python MCP, bounded session store, optional native analysis extras |

## Findings worth aligning

### 1. Stable references independently checked against bytecode

Qtty's `DexReverseIndex` is a substantive implementation, not a README-only capability. It visits a copied instruction reader, resolves method/field/type operands, adds declaration and annotation relationships, compacts adjacency lists to arrays and exposes unmodifiable views. `JadxAnalyzerCore.reverseIndex()` lazily publishes one index per analyzer. This avoids asking a mutable decompiler usage graph for the same answer after different prior operations. [Index implementation](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/main/java/com/example/jadxmcpserver/core/DexReverseIndex.java#L178-L299), [instruction scan](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/main/java/com/example/jadxmcpserver/core/DexReverseIndex.java#L301-L404), [lazy publication](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/main/java/com/example/jadxmcpserver/core/JadxAnalyzerCore.java#L2089-L2103).

The accompanying tests check synthetic accessors, fields, class references and sink results before/after decompilation, then check a known accessor's four callers against manually recorded Smali. This combines history-independence with an independent oracle; comparing two outputs from the same implementation alone is weaker. [XrefStabilityTest](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/test/java/com/example/jadxmcpserver/core/XrefStabilityTest.java#L80-L141), [whole-APK and bytecode assertions](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/test/java/com/example/jadxmcpserver/core/XrefStabilityTest.java#L153-L272).

Limitations: this is not a runtime call graph. Unresolved methods are excluded from this reverse index; unreadable methods increment `scanErrors`; recursive self-edges are intentionally excluded. Source comments' timings and large-production-APK counts were not reproduced here. [Resolution and scan limits](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/main/java/com/example/jadxmcpserver/core/DexReverseIndex.java#L314-L389), [self-edge test](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/test/java/com/example/jadxmcpserver/core/XrefStabilityTest.java#L274-L289).

Our immediate alignment: retain ASC's bounded fresh-worker architecture and raw output; add real MCP references-before/source/references-after regressions for both APK and DEX. No JVM reverse index is needed merely to acquire this invariant. Ensure the test cannot pass solely because a response cache returns the first answer. A future structured bytecode backend should expose coverage/scan failures rather than an unjustified complete-graph claim.

### 2. Full method identity and round-trippable references

Qtty resolves pinned aliases, current aliases and raw DEX names in separate precedence tiers, then narrows by the complete `(arguments)return` descriptor. Ambiguous names produce an explicit notice; an invalid signature raises an error instead of masquerading as an empty caller list. Tests cover ambiguity, descriptor selection and invalid signatures. This is a better contract than picking the first same-name method. [Resolver](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/main/java/com/example/jadxmcpserver/core/JadxAnalyzerCore.java#L1615-L1692), [ambiguity and errors](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/main/java/com/example/jadxmcpserver/core/JadxAnalyzerCore.java#L1695-L1755), [MethodIdentityTest](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/test/java/com/example/jadxmcpserver/core/MethodIdentityTest.java#L219-L272).

Original gap: the public ASC CLI output consumed by [runner.py](../src/droidasc_mcp/runner.py) is `cli-text-best-effort`; it does not supply a trustworthy full caller descriptor or instruction offset. That legacy path remains unchanged. The candidate's separate descriptor-exact operations now use dexlib2 instruction operands, never displayed Java names or text line counts; see the current alignment below.

### 3. Structured hierarchy with explicit semantics

Qtty separates `superClass`, directly declared `interfaces`, transitive `superTypes`, direct `subClasses`, inner/outer classes and `inApk`. Its tests explicitly distinguish direct subclasses from the superclass closure and check that emitted names resolve back to the same class. [Hierarchy implementation](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/main/java/com/example/jadxmcpserver/core/JadxAnalyzerCore.java#L4247-L4315), [hierarchy tests](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/test/java/com/example/jadxmcpserver/core/TypeHierarchyTest.java#L59-L81), [round-trip test](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/test/java/com/example/jadxmcpserver/core/TypeHierarchyTest.java#L193-L224).

Our immediate alignment: expose existing ASC `extends`/`impl` operations, return `dex`, `class_name`, `relation`, `target`, `raw`, and explicitly mark `relation_scope=direct`. This is useful parity, not a claim that ASC now supplies a complete transitive hierarchy or framework classpath. Accept canonical descriptors and dotted names; test classes beginning with `L`, interface-to-interface inheritance and indirect relationships that must not appear as direct matches.

### 4. Reuse analysis state without mixing samples

Qtty keeps loaded analyzers in a capacity-limited registry with LRU-like eviction, explicit close, reuse/eviction/thrash counters and heap-derived capacity. Tests assert reuse, eviction, thrash accounting and actual release of the decompiler. These lifecycle and observability properties are worth adopting. [AnalyzerRegistry](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/main/java/com/example/jadxmcpserver/core/AnalyzerRegistry.java#L127-L177), [registry tests](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/test/java/com/example/jadxmcpserver/core/AnalyzerRegistryTest.java#L35-L81), [thrash and cleanup tests](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/test/java/com/example/jadxmcpserver/core/AnalyzerRegistryTest.java#L118-L234).

Do not copy its global current-APK behavior: the implementation itself notes that all clients answer against the most recently selected APK and merely logs a warning on switches. Cache keys are APK paths, not content identities. This is not safe sample isolation for simultaneous analyses. [Current-APK warning](https://github.com/Qtty/jadx-mcp-server/blob/4e6d890d1d3753d2bb47d492a9523ef98874df85/src/main/java/com/example/jadxmcpserver/core/AnalyzerRegistry.java#L179-L199).

Subwire uses UUID session handles and requires a session for reads; closing removes and closes the corresponding decompiler. This is a better wire-level sample identity than a global current APK. However, its manager has no visible capacity or TTL, loads a fresh analyzer for every create, and does not bind sessions to input hashes. No tests directory was present in the inspected repository tree. [Session manager](https://github.com/subwire/jadx-mcp-server/blob/2b3e51cc115c914b2a311c64d95fd5f850c75fd3/src/main/java/jadxmcp/JadxSessionManager.java#L15-L60), [pinned repository tree](https://github.com/subwire/jadx-mcp-server/tree/2b3e51cc115c914b2a311c64d95fd5f850c75fd3).

Our APK snapshot cache is bounded and coalesces identical in-flight requests. One-shot DEX calls rebuild validated temporary input on each request; the candidate now additionally offers immutable hash/engine-bound DEX sessions with disk/count limits, TTL/close, active-query pinning and cancellation cleanup. Query options remain per request because sessions cache input preparation, not query results. There is no global current sample or resident analyzer. Real-query performance still needs representative measurement before claiming speed parity. See [sessions.py](../src/droidasc_mcp/sessions.py), [runner.py](../src/droidasc_mcp/runner.py) and [dex_worker.py](../src/droidasc_mcp/dex_worker.py).

### 5. Structured decompilation fallback, but preserve exact targets

1013503897 returns `mode`, `fell_back`, failure `markers`, overload index/count and body from `get_method_body`. It distinguishes strong/soft decompilation text markers and provides method-level Smali slicing. These fields are preferable to silently presenting partial Java as a successful decompilation. [Tool response](https://github.com/1013503897/jadx-headless-mcp/blob/e06a4ae20e5331258520855cabe755015ffb0dbd/src/main/kotlin/com/atxx/jhmcp/MethodTools.kt#L107-L131), [marker implementation](https://github.com/1013503897/jadx-headless-mcp/blob/e06a4ae20e5331258520855cabe755015ffb0dbd/src/main/kotlin/com/atxx/jhmcp/DecompileFailure.kt), [marker tests](https://github.com/1013503897/jadx-headless-mcp/blob/e06a4ae20e5331258520855cabe755015ffb0dbd/src/test/kotlin/com/atxx/jhmcp/DecompileFailureTest.kt).

Source-verified limitation: after choosing one overload, `getMethodBodySmart` calls `getMethodSmali(owner, method.name)` and joins all blocks of that name. Thus the fallback can return all overloads rather than only the requested method. `findMethod` and method xrefs also select the first same-name method. Our eventual method API should require/return descriptors and keep the identical target across Java-to-Smali fallback. [Fallback and slicer call](https://github.com/1013503897/jadx-headless-mcp/blob/e06a4ae20e5331258520855cabe755015ffb0dbd/src/main/kotlin/com/atxx/jhmcp/JadxSession.kt#L409-L457), [first-match lookup](https://github.com/1013503897/jadx-headless-mcp/blob/e06a4ae20e5331258520855cabe755015ffb0dbd/src/main/kotlin/com/atxx/jhmcp/JadxSession.kt#L310-L319), [xref tools](https://github.com/1013503897/jadx-headless-mcp/blob/e06a4ae20e5331258520855cabe755015ffb0dbd/src/main/kotlin/com/atxx/jhmcp/XrefTools.kt).

The inspected Smali tests explicitly assert that all overloads are extracted; they do not prove exact selected-overload fallback. `McpToolLayerTest` invokes registered handlers through a proxy, rather than launching an actual stdio/HTTP transport, and covers basic class tools/paging. Our real transport acceptance should be retained rather than replaced with handler-only tests. [Smali tests](https://github.com/1013503897/jadx-headless-mcp/blob/e06a4ae20e5331258520855cabe755015ffb0dbd/src/test/kotlin/com/atxx/jhmcp/SmaliSlicingTest.kt), [MCP handler test](https://github.com/1013503897/jadx-headless-mcp/blob/e06a4ae20e5331258520855cabe755015ffb0dbd/src/test/kotlin/com/atxx/jhmcp/McpToolLayerTest.kt#L25-L76).

Subwire likewise lists signatures but selects method source/xrefs by name and first match; its method helpers are not an exact-overload implementation to emulate. [Method listing](https://github.com/subwire/jadx-mcp-server/blob/2b3e51cc115c914b2a311c64d95fd5f850c75fd3/src/main/java/jadxmcp/JadxSessionManager.java#L63-L75), [source and xref lookup](https://github.com/subwire/jadx-mcp-server/blob/2b3e51cc115c914b2a311c64d95fd5f850c75fd3/src/main/java/jadxmcp/JadxSessionManager.java#L131-L179).

### 6. Bounded sessions and machine-readable capability errors

Androguard's current MCP `SessionStore` defaults to four sessions with a 30-minute idle TTL, UUID identities, oldest-used eviction, allowed-root checking and explicit close/list tools. Missing native extras become an `extra_missing` error with an installation hint rather than an empty result. These are useful API patterns for future analysis reuse and optional backends. [Session implementation](https://github.com/androguard/androguard/blob/3ea3da38e74b4d74579463d0688ab513786c4750/androguard/mcp/session.py), [capability error handling](https://github.com/androguard/androguard/blob/3ea3da38e74b4d74579463d0688ab513786c4750/androguard/mcp/tools.py).

Do not copy the invalidation semantics: `get()` compares floating-point `st_mtime` and silently replaces the `Application` inside the same session ID when a file changes. The session is not bound to immutable evidence or a content hash. `_parse_roots` splits on `:` rather than the host path separator, so Windows drive-letter roots require separate treatment. These are source observations, not a reproduced Windows failure. [Identity and root parsing](https://github.com/androguard/androguard/blob/3ea3da38e74b4d74579463d0688ab513786c4750/androguard/mcp/session.py).

The `list_methods` field named `descriptor` is constructed as `class_name->name`, without the argument/return prototype. `find_refs` accepts only string/type/method/field and pages with offset fixed at zero. Neither is full descriptor-aware or complete multi-page xref parity. Its method decompiler delegates `CLASS#METHOD` selection to `Application`, rather than establishing an exact-overload contract at the MCP layer. [Tool implementation](https://github.com/androguard/androguard/blob/3ea3da38e74b4d74579463d0688ab513786c4750/androguard/mcp/tools.py), [application selector](https://github.com/androguard/androguard/blob/3ea3da38e74b4d74579463d0688ab513786c4750/androguard/application.py#L222-L232).

The inspected tests cover open/summary/close, count-based eviction, roots, unknown sessions and tool registration; native decompile/disassembly smoke tests are conditional on extras. They do not establish TTL expiry, concurrent-session behavior or Windows drive parsing. Retain our real Windows/Linux transport and worker-lifecycle acceptance when adopting these ideas. [MCP tests](https://github.com/androguard/androguard/blob/3ea3da38e74b4d74579463d0688ab513786c4750/tests/test_mcp.py).

### 7. GUI and debugger context is a different product surface

The Zinja JADX plugin exposes debugger stack frames, selected threads and register/this-object trees by reading an attached JADX GUI debugger. This is useful interactive context our static headless adapter does not have; it requires an active debugger and reflective access to GUI internals, not merely an extra ASC query. Keep this as an optional integration rather than an unconditional JVM/GUI dependency. No debugger runtime acceptance was performed here. [Debug routes](https://github.com/zinja-coder/jadx-ai-mcp/blob/9f4fce6f49902e95c62479c02d985d1eb0b3cbe1/src/main/java/com/zin/jadxaimcp/server/routes/DebugRoutes.java).

Its method route accepts a signature parameter, including one embedded in the method name. However, lookup uses case-insensitive names and returns the first matching method, while `MethodSignatures.matches` uses substring containment rather than exact prototype equality. This is not the exact identity contract proposed above. No matching method/signature/debug test files were found in the inspected tree; this is a source review, not a reproduced defect report. [Method routes](https://github.com/zinja-coder/jadx-ai-mcp/blob/9f4fce6f49902e95c62479c02d985d1eb0b3cbe1/src/main/java/com/zin/jadxaimcp/server/routes/MethodRoutes.java), [signature matcher](https://github.com/zinja-coder/jadx-ai-mcp/blob/9f4fce6f49902e95c62479c02d985d1eb0b3cbe1/src/main/java/com/zin/jadxaimcp/utils/MethodSignatures.java).

## Alignment sequence and acceptance

| Priority | Change | Acceptance / boundary |
| --- | --- | --- |
| Immediate | Direct `extends`/`impl`, typed relationship fields | Real APK/DEX over stdio/HTTP; descriptor normalization; negative indirect-edge cases; retain raw output |
| Immediate | History-independent references regression | Same references before/after source reads; force a fresh analysis path; fixed fixture ground truth, not only self-comparison |
| Next | Bounded DEX analysis reuse | Hash-bound input identity, concurrent sample isolation, TTL/close/cancellation cleanup, warm-vs-cold measurements |
| Next | Full method descriptor and precise Smali fallback | Supported engine API, overload/constructor/synthetic cases, invalid identity is an error, Java and Smali target same descriptor |
| Later | Bytecode-level structured xrefs and callers/callees | Stable original identities; explicit unresolved/partial coverage; independent bytecode oracle and call-order regression |

This table is the original prioritization, not a blanket parity claim. The candidate now implements
bounded immutable DEX preparations, exact-method source and instruction-level method/field references.
The later candidate adds a bounded on-disk reverse index with annotation/type/declaration
relationships. Working copies belong to a session; an explicitly configured, checksum-verified
durable cache can restore matching indexes across sessions and server restarts. It does not
resolve runtime targets. Cross-platform and large-input evidence is recorded separately in
[validation results](VALIDATION.md).

### Second alignment implementation

- Sessions bind ordered source SHA-256 hashes and ASC version, not mtime or a global current APK.
  They reuse validated containers only; engine processes and query options remain per request.
  Count/disk reservations, TTL reaping, explicit close, active-query pinning and shutdown cleanup
  are in [sessions.py](../src/droidasc_mcp/sessions.py).
- Full method identities come from dexlib2 DEX method definitions, including return types and
  synthetic methods. The optional backend uses JADX 1.5.5's public exact short-ID lookup and
  `JavaMethod.getCodeStr`, not `getMethodNode`/`getClassNode` internal APIs and not Java-text slicing.
  Java fallback Smali is emitted from the same exact dexlib2 `Method` through baksmali, never all
  name-matched overloads. Explicit Smali now uses ASC post3's public `--method` CLI without Java.
  See [MethodBridge.java](../src/droidasc_mcp/MethodBridge.java) and the pinned
  [public method API](https://github.com/skylot/jadx/blob/v1.5.5/jadx-core/src/main/java/jadx/api/JavaMethod.java).
- JADX is optional, independently installed, version-checked and not redistributed in our package.
  JVM startup cost is explicit. The bridge runs under the existing supervisor on both platforms;
  no native GUI/debugger or complete runtime reference graph is claimed.

### Current instruction-reference alignment

- `find_method_refs` and `get_method_calls` scan declared method operands with exact identities,
  DEX ownership, code-unit offsets, deterministic paging and bounded unresolved/dynamic diagnostics.
  Decode errors and optimized-only/unknown opcodes fail the query rather than claiming coverage.
- `find_field_refs` scans full `class->name:type` operands, reports read/write and static/instance
  access and filters before pagination. External targets remain visible with explicit unresolved
  definition provenance; no inherited/reflected field resolution or encoded initializer edges
  are claimed. This does not reproduce all relationships in Qtty's reverse index.
- Independent source-built Smali fixtures verify positions and types. Both MCP transports test
  source-read history independence; Kotlin/R8 fixtures test renamed method identity and coroutines.
  Sessions reuse validated input preparations, an optional reverse index and bounded exact-query
  pages, not a resident JVM. [Measured cold/warm behavior](VALIDATION.md#interactive-discovery-and-exact-page-reuse)
  and the [later aimard comparison](AIMARD_COMPARISON.md) separate specific improvements from
  remaining latency and feature gaps; no universal benchmark advantage is claimed.
