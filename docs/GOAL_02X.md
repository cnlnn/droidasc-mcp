# 0.2.x incremental completion goal

## Current implementation plan, 2026-10-27

Status: goal execution active; B1 implementation and local acceptance in progress. This section is the
single current execution ledger and ordered backlog. Older sections below retain
historical decisions and receipts; their candidate/release statuses do not override
this section. The cross-platform/package requirements and invariants below still apply.
The maintainer requested continuous goal-mode execution on 2026-10-27: finish each
batch's gates and automatically advance to the next without repeated confirmation.
Publication is separate; this instruction does not approve another release.

### Baseline and evidence

- Product baseline: published v0.2.4, commit
  `5eddd07d5bbe362c2273938501cdda363c4f1d73`; initially clean main.
- Comparator: aimardcr/asc-mcp
  `848c711f1d80a1c2577283f1fa5f475ff734aa40`, checked against GitHub on 2026-10-27.
  Inventory covers 25 tools, two resources, three prompts and 87 non-context parameters;
  inventory coverage is not proof of equivalent behavior.
- Fresh MCP evidence: `artifacts/competitor-gap-audit-20261027/probe.json` and
  `type-scope.json`; harnesses, fixtures and both tools/list responses are adjacent.
  Preserve these originals. Promote relevant fixture generation and regression checks
  into tests/scripts during B1 so acceptance does not depend on ignored local files.
- `evidence-check.json` verifies current runtime identity against the preserved
  2026-10-24 performance receipts and 36 linked evidence files. Timing was not rerun
  on 2026-10-27. New implementation acceptance requires new measurements.
- Confirmed gaps: type-instruction semantic mismatch/mandatory full index; missing
  complete-result string caching; excessive complete-reference pagination; fragmented
  artifact/session interfaces; eager preparation/storage cost; single-module AAB scope;
  Java/dexlib2 dependency for the exercised shared-data DEX 041 class inventory.
- Tool-schema size and interface fragmentation support an ergonomics hypothesis, not
  a measured model-success deficit. Existing manifest/resources/signing, multi-hop graph
  and ASC Java class source are present. Comparator graph failures and incorrect field
  sites are not correctness targets. Neither product resolves all runtime/reflection edges.

### Compatibility and scope decisions

- Keep existing tools, defaults, flat reference rows, literal string-substring matching,
  exact Dalvik identities, offset units and explicit error behavior. Add new behavior
  explicitly; changing an existing default requires a separately recorded decision.
- Keep `type_relation=instruction` as the existing broad instruction/catch/member-type
  relation set. Do not silently redefine it as explicit type operands. Keep `all`,
  `declaration` and `annotation` unchanged, including their existing index path.
- B1 adds `type_relation=operand` and `type_match=exact|substring`, default `exact`.
  `substring` is allowed only for the new operand scope, is case-sensitive and literal,
  and matches normalized Dalvik descriptors. Exact mode retains array dimensions and
  existing dotted-name normalization. Empty selectors fail validation; regex is not added.
  Cache identities include both fields. Reject non-default type_match on other scopes.
- Preserve original-input checks, immutable identities, instruction validation, bounded
  output/cache/disk reservations, cancellation and full owned-process cleanup. Reuse the
  existing selected-result spool/publication machinery; no full-APK resident worker pool,
  second session database or independent parallel cache implementation.
- No runtime dependency, version bump, tag/main publication, release withdrawal or
  broad architecture replacement is part of B1. Existing graph limits stay explicit.
  Preparation/compression changes and unified handles are separate batches.

### Ordered batches

| Batch | Deliverable | Dependency | State |
| --- | --- | --- | --- |
| P0 | Source-backed plan and compatibility decisions | Current audit | complete |
| B1 | Operand-only type scan, selected-set reuse, string cache and accurate API mapping | P0 | in progress |
| B2 | Compact reference output and resumable full-result collection | B1 accepted | deferred |
| B3 | Unified artifact workflow and smaller tool contracts | B2 accepted | deferred |
| B4 | Measured preparation reuse/cost reduction | B3 accepted | deferred |
| B5 | Explicit multi-module AAB analysis | B4 accepted or closed with measured residuals | deferred |
| B6 | Native DEX 041 logical views and query coverage | B5 accepted | deferred |

Execution order changes need an evidence-backed entry here, not a silent expansion of B1.
A failed optimization does not block unrelated later capabilities indefinitely: retain its
failure and residual gap, then record the revised order. Never call the overall gap closed
because a batch or patch release passed.

### B1 work packages

1. **B1.1: Freeze semantics with failing regressions.** Promote the current type/string
   probes into deterministic tests. Separate actual type-operand opcodes from field/method
   owner types, prototypes, catches, declarations and annotations. Cover exact object and
   array descriptors, literal substring, dotted names, missing targets, invalid selectors,
   multiple DEX entries, repeated use sites and deterministic global ordering. Preserve
   the existing broad-instruction fixture result instead of relabeling its extra rows as
   false positives. Decode original instruction streams independently for expected sites.
2. **B1.2: Add the narrow native query path.** Route operand queries before automatic index
   selection in `dex_worker.py`; use checked instruction traversal and existing selector
   helpers, with a small dedicated module if separation warrants it. Update validation in
   `service.py`, tool annotations/docs in `server.py` and generated schema sources/caches.
   Native and Python fallback paths must agree. A cold operand query, including no-match,
   must neither build/restore an all-relations index nor require Java. Existing indexes
   must not change its semantics. Old broad relation queries retain their current behavior.
3. **B1.3: Reuse complete selected results.** Extend `native_strings.py` and the new operand
   scanner to stream complete selected sets through `runner.reference_spool`. Integrate
   `reference_page.py`, `reference_cache.py`, `sessions.py` and worker routing with a
   query-aware eligibility predicate: only operand type queries gain the native cache path,
   not every `find_type_refs` variant. Keep the existing quotas/reservations and validated
   atomic publication. Do not collect unbounded rows in a Python list.
4. **B1.4: Verify page/cache lifecycle.** Exclude offset/limit from complete-set identity,
   retain every result-affecting selector and backend/input/schema identity, and retain
   exact-page caching as a separate layer. For fitting sets, new offsets and changed page
   sizes reuse the published set without rescanning. Oversized/quota-unavailable sets use
   the correct uncached path. Cover partial writes, corruption, invalidation, cancellation,
   concurrent same/different selectors, close/expiry and reservation release. Preserve all
   diagnostics and every const-string/jumbo value/site, including Unicode and long values.
5. **B1.5: Bound pages and verify handoff.** Apply byte-bounded complete prefixes to the
   newly cached paths; next_offset advances by emitted rows and collection has no gaps or
   duplicates. A single unpageable row remains an explicit response_limit. Check offset 0,
   middle, beyond-end, empty results, varying limits and repeated full collections through
   both stdio and HTTP. Verify cache-hit/uncached response equality after excluding only
   documented cache-execution metadata, not semantic fields or scan diagnostics.
6. **B1.6: Correct claims and freeze acceptance.** Update `COMPETITOR_API_AUDIT.md` to
   distinguish broad type relations, exact operands and competitor substring/regex behavior.
   Literal substring support is not regex parity. Update tool descriptions/schema fixtures
   from actual behavior. Run the gates below and record source, harness, input and package
   identities. B1 completion does not imply B2-B6 or live-model parity.

### B1 acceptance matrix

| Gate | Required evidence |
| --- | --- |
| Semantic accuracy | Original-byte expected sites including DEX entry, caller, opcode, referenced type/string and code-unit offset; exact old-query compatibility; native/Python equality |
| Cold query topology | Empty/nonempty operand query creates no xrefs.sqlite/calls.sqlite and invokes no full-index builder/restore or Java; instrument invocation counts, not just filenames |
| Cache mechanism | Fitting first query scans once; later unseen offsets and full repeats scan zero additional times; selector separation, quotas and all lifecycle failures tested |
| Real transports | stdio and HTTP collect every page, preserve diagnostics/identity, recover from invalid input and release sessions/processes/files |
| Large inputs | Taobao, WeChat, Douyin plus a frozen held-out input; independent string/type sites; cached-versus-uncached equality and unchanged method/field reference regressions |
| Performance | Matched baseline/candidate/comparator full collections; process-start-to-first-useful, first complete, repeated complete and concurrent complete times; page/call/retry counts and resource costs |
| Distribution | Final commit passes Linux/Windows Python 3.10-3.13 source and canonical-sdist/exact-native-wheel gates, real transports, signing, Rust and stability checks; no required skipped cells |

Use `tests/test_xref_index.py`, `test_string_refs.py`, `test_reference_cache.py`,
`test_reference_page.py`, `test_sessions.py`, `test_service.py`, `test_server.py`,
`test_tool_registry.py` and `test_integration.py`, plus focused new operand tests.
Extend `scripts/verify_string_references.py` and add an independent operand verifier;
reuse the existing CPU-budget and full-page benchmark harnesses rather than inventing
different timing boundaries. Standard schema/quality checks remain:

```sh
uv run ruff check .
uv run ruff format --check .
uv run python scripts/compile_input_schemas.py --check
uv run python scripts/compile_output_schemas.py --check
uv run python scripts/audit_competitor.py artifacts/aimard-asc-mcp
```

Run targeted tests during implementation, then the complete configured source suite and
CI matrix at candidate freeze. Fixture/tool setup follows `.github/workflows/ci.yml`;
missing tools or unavailable Windows/model access are blockers, not skipped passes.
Fresh evidence root: `artifacts/competitor-gap-b1-<date>/`, with separate baseline,
candidate, comparator, failed attempts and a final hash-bound summary. No existing probe
or historical benchmark output is overwritten. Add tracked reproduction instructions.

For performance, use the same interpreter, inherited two/four-CPU affinity, worker and
RSS/temp budgets for both products, with full-page accuracy before ratios. Use at least
five alternating paired rounds and retain every trial; expand noisy cells rather than
selecting favorable rounds. Report medians and paired spread. A >5% and >100-ms median
regression in an existing complete workflow requires investigation/repetition before B1
acceptance; these are proposed engineering gates, not prior measured thresholds. A fitting
string/type selected-set workload must demonstrate scan elimination and repeatable
complete-collection improvement, not just a cache-hit flag. If timings remain inconclusive,
record mechanism completion separately and leave performance acceptance open. Estimate
p95 only from a separately declared sample of at least 30 repetitions. Report process RSS,
retained disk and tmpfs separately; startup includes preprocessing and initialization.

### Later batch boundaries and completion conditions

- **B2:** Opt-in grouped references/common identity tables plus stable, versioned cursors;
  flat responses/defaults remain compatible. Reconstruction must equal every flat site and
  diagnostic. Cover a single caller spanning pages, cursor mismatch/expiry, response caps
  and resumed collection. Measure bytes, page count and end-to-end latency together;
  fewer pages alone are not success. No blanket response-limit increase or dropped fields.
- **B3:** One artifact identity for inventory/manifest/resources/signing and lazy DEX work;
  existing sessions/path tools remain adapters. Reuse current ownership/lifetime logic,
  bind every operation to verified content and preserve resource/prompt links. Choose the
  advertised tool surface and migration policy before coding; do not advertise both a full
  duplicate wrapper set and the current giant selector by default. First freeze real-model
  baseline tasks, then compare success, tool calls, retries, schema tokens and complete task
  time with unchanged model/provider settings. Prompts describe user tasks only; expected
  identities, known findings and scoring rules stay in offline judges. No model-access
  result is implied by the current tools/list byte counts.
- **B4:** Profile read/hash/inflate/directory/index/worker/transport phases; adopt only
  measured removal or bounded reuse of duplicated immutable work. Keep first-use costs
  visible and validate input mutation, concurrency and cleanup. Rejected compression,
  larger SQLite batches and micro-optimizations in STARTUP_STORAGE_EXPERIMENTS.md are not
  defaults to retry without new evidence. No total-memory claim from process RSS alone.
- **B5:** Add explicit multiple/all-module AAB selection while keeping default base behavior.
  Preserve module/original-entry provenance and reject or explicitly select duplicate
  classes. Verify base-to-feature and feature-to-feature references plus unified inventory,
  empty/invalid modules and manifest/resource routing. Current fresh evidence demonstrates
  only the comparator's unified class inventory, not its cross-module graph correctness.
- **B6:** Introduce validated DEX 041 physical/logical address views, initially inventory and
  instruction queries without Java; keep pinned dexlib2 normalization as an explicit
  compatibility path. Verify shared strings/tables, nonzero header offsets, all logical
  files, malformed layouts, original-byte provenance and original-input integrity with an
  independent oracle. Decompiler/source handoff is a separate gate; native class enumeration
  alone does not justify removing normalization or claiming full 041 support.

### Execution ledger and next action

| Item | Current record |
| --- | --- |
| Current task | B1 Taobao two-CPU five-round comparator cell accepted; product runtime CI passes all 25 jobs; revision wrapper passes 1649 full-source tests; B1 remains open |
| Next action | Finish alternating old/new Taobao regression timing, then four-CPU and remaining corpus cells; run CI for the added revision wrapper and retain all measured residuals |
| Product changes | Native/Python operand scanner, explicit type match contract, existing bounded selected-set spool for string/type, query-aware routing/cache locks and byte-bounded paging; old broad relation behavior retained |
| Planning checks | Follow-up full-source, Ruff, formatting, schema and diff checks pass; pinned competitor inventory remains 25 tools, two resources, three prompts and 87 parameters; inventory is not behavior acceptance |
| Open dependencies | Large-input performance matrix remains open; CI 40465990968 passes both prior failure classes on b9f98c8; the later revision wrapper needs its own matrix; real-model access is a later B3 gate |
| Fixed architecture decisions | Backward-compatible broad type scope; explicit operand scope; bounded existing selected-set cache; original-input provenance; no resident full-APK pool |
| Release state | No new release/version selected; development completion and publication approval remain distinct |

Initial test setup selected the host's JDK 8 and failed fixture assembly, preserved as
`artifacts/competitor-gap-b1-20261027/baseline/string-red.xml`. Rerun with the existing
`/opt/tools/environment/jdk-17/bin/java`; this setup error is not the intended regression.

B1 local progress, 2026-10-27 (not batch/release acceptance):

- `baseline/string-red-final.xml` reproduces a new page invoking another worker;
  `baseline/type-red.xml` reproduces the unsupported operand scope. The earlier broad
  `https://` test selected four sites, not the intended three-site literal; its failed
  `string-red-jdk17.xml` is retained as test-development evidence, not a product finding.
- `candidate/string-green.xml`: 134 string/cache/page cases pass. A complete result is
  streamed through the existing bounded spool; cache reads no longer add method-target
  fields to string/type rows. No separate cache database or quota increase was introduced.
- `candidate/operand-native.xml`: 281 native/type/string/cache/legacy-index/service cases
  pass. The seven explicit type opcodes use the checked C cursor's new mode 3 and an
  independent Python token path; old native binaries fall back rather than misparse mode 3.
- `candidate/type-cache-lifecycle-final.xml`: 99 cases pass, including no-match/index-present
  paths instrumented against index lookup/build/restore, unchanged ten broad type relations,
  cache quotas, cancellation, same-selector coalescing and cleanup. First lifecycle run
  rejected an exact selector validation gap; that failure remains in type-cache-lifecycle.xml.
- `candidate/real-transports.xml`: all four selected stdio/HTTP string/type cases pass;
  complete repeats, different page sizes, input identity, invalid-selector recovery and
  session cleanup checked. Other transport cases were deliberately deselected in this run.
- `candidate/wide-operand-pages.xml`: four cases preserve all 100 long string/type sites
  across byte-limited pages, both with a fitting cache and a deliberately overflowing lease.
- `candidate/source-full-first.xml`: 1541 tests pass without skips on local Linux/Python 3.13.
  This precedes the dotted-name fix below and is not the final source or Windows/package gate.
- Exact dotted names beginning with `L` exposed an additive-selector normalization bug.
  `baseline/dotted-l-red.xml` reproduces it; `candidate/dotted-l-green.xml` passes four cases.
  Current full-suite revalidation in `candidate/source-full-second.xml` passes all 1549
  tests without failures/errors/skips on local Linux/Python 3.13, including the wide-page and
  dotted-name regressions. Both schema checks, Ruff lint/format, diff checks and the pinned
  competitor inventory audit pass. These are not new Windows or exact-package receipts.
- New `scripts/verify_type_operands.py` compares complete site multisets and scan diagnostics
  against Androguard 4.1.4 decoding of every original DEX instruction. The positive fixture
  has two sites; Termux verifies 219 selected sites over 272074 instructions and 18613 methods.
  The Termux receipt binds the current post-normalization runtime; the earlier fixture
  receipts retain their own pre-fix runtime hashes. These are scanner, not MCP/performance gates.
- `candidate/taobao-type-oracle.json` independently verifies all 56791 selected type operand
  sites over 12495817 instructions and 606974 methods, with original/runtime/verifier hashes
  unchanged. This still does not close large-input MCP paging or comparative latency gates.
- Pure-Python `setup.py build_ext` could not import setuptools in the runtime venv. Rebuilt
  the optional accelerator with `uv pip install --python .venv/bin/python --no-deps --offline -e .`;
  this adds no product dependency. The oracle's initial offline 4.1.3 request was unavailable;
  the locally cached, explicitly pinned acceptance dependency is Androguard 4.1.4.

Reproduce the focused checks from the repository root with the existing fixture toolchain:

```sh
export DROIDASC_MCP_JAVA=/opt/tools/environment/jdk-17/bin/java
export DROIDASC_MCP_JADX_HOME="$PWD/artifacts/jadx-1.5.5"
.venv/bin/pytest tests/test_type_operands.py tests/test_string_refs.py tests/test_reference_cache.py tests/test_reference_page.py -q
.venv/bin/pytest tests/test_integration.py -q -k operand_and_string_complete_sets_over_real_transports
PYTHONPATH="$PWD/src" uv run --no-project --offline --with androguard==4.1.4 python scripts/verify_type_operands.py artifacts/device-corpus-20260921/com.termux.apk --type-descriptor 'Ljava/lang/String;' --type-match substring --output artifacts/competitor-gap-b1-20261027/candidate/termux-type-oracle-rerun.json
```

Full-suite runs also configure DROIDASC_MCP_DEXLIB_HOME, DROIDASC_MCP_RUST_ASC,
ASC_TEST_EXPECT_FIXTURE=1 and the existing public/complex APK and mapping inputs, following
the CI matrix. Use fresh receipt names; preserve earlier failures and runtime-bound results.

Full-collection acceptance extension, 2026-10-27:

- The existing `benchmark_competitor_runtime.py` now exposes `full_string`, `full_type`
  and concurrent `full_operands`, keeping its common timer/CPU/process/resource monitor.
  Exact old scenarios are unchanged. It now refuses to overwrite an existing receipt.
  `candidate/operand-benchmark-red.xml` preserves the five missing-capability failures;
  `candidate/operand-benchmark-green.xml` passes the 134 existing/extended harness cases.
- New `scripts/verify_operand_page_benchmark.py` replays every recorded MCP request,
  continuation and retry, checks input provenance and native scan diagnostics, then
  compares every site with independent Androguard original-byte decoding. Comparator
  caller groups are expanded to sites; duplicate sites, byte offsets and targets remain
  significant. Native string indexes are checked independently as well. Verification is
  outside measured calls and binds original, runtime, harness and decoder source hashes.
  `candidate/operand-verifier-red.xml` preserves the initially absent verifier;
  `candidate/operand-harness-verifiers.xml` passes 169 combined harness/acceptance cases,
  including altered provenance, diagnostics, arguments, missing/extra pages and duplicates.
- `candidate/termux-operands-smoke.json` is a failed configuration attempt: a 2048 MiB
  expansion reservation needs more than the 8192 MiB session budget (7x normalization
  reserve plus index/metadata). No safety limit was weakened. With an explicit 128 MiB
  expansion budget, `termux-operands-smoke-budget-fixed.json` completes all six fresh-server
  trials and two repeats. `termux-operands-smoke-verified.json` independently accepts all
  16 collections, preserving 35 string and 219 type operand sites. One round is only a
  harness smoke test, not the required five-round performance result.
- Large-input runs use an explicit 768 MiB expansion and 8192 MiB session budget with the
  original cache quotas and common 4096 MiB descendant RSS cap. They do not inherit the
  invalid 2048/8192 reservation combination above. No product runtime edit or native
  rebuild occurs during a frozen benchmark.
- The additional B1 holdout is frozen before its new operand/cache measurements:
  `artifacts/device-corpus-20260921/org.fdroid.fdroid.apk`, SHA-256
  `985f5181d48bb6bafd54083a048b391271e0ab28385881cc41294fb01a222762`.
  It is held out from B1 tuning, not claimed to be absent from all historical corpus work.
  The old product has a separate detached checkout at
  `artifacts/competitor-gap-b1-20261027/baseline/source`; no current runtime is replaced by it.
- The first five-round Taobao attempt, `candidate/taobao-operands-cpu2.json`, failed rather
  than completing. At 13:34:40 local time the kernel killed the benchmark client PID 762938
  with exit 137 and 5817680 KiB anonymous RSS. It retained all prior response trees and
  repeatedly serialized a cumulative inline report. The last saved report is still
  `status=running`; no ratio or successful subset is promoted to performance acceptance.
  The kernel evidence is recorded in `taobao-operands-cpu2-failure.json`; the exact earlier
  harness is preserved as `benchmark-operand-retained-responses.py`. Post-failure checks
  found no remaining benchmark server/worker descendants. This is a harness failure,
  not a product-worker memory measurement.
- The corrected harness streams each finished trial's full operations to an immutable,
  size/hash-bound `.trials/NNNN.json` sidecar, releases that response tree and atomically
  updates a compact report outside measured calls. Both reference verifiers read one trial
  at a time, verify sidecar identities and still support historical inline receipts.
  `candidate/bounded-benchmark-red.xml` preserves six missing-capability failures;
  `candidate/bounded-harness-verifiers.xml` passes 175 cases, including sidecar tampering,
  changed sizes, missing files, path traversal, immutable prior trials and legacy input.
  Fresh large-input revalidation starts with a two-round parallel smoke before repeating
  the required complete five-round matrix. This does not weaken product cache limits.
- `candidate/taobao-operands-bounded-smoke.json` now completes four alternating fresh-server
  trials (two rounds, two full repeats, concurrent string/type). All transport, CPU and
  original/runtime identity gates pass. Benchmark-client RSS sampled after spilling each
  trial is 202/255/270/261 MiB, instead of retaining every earlier response tree; these are
  post-trial samples, not peak process memory claims. Separate offline site acceptance is
  still required, and two rounds do not meet the five-round performance gate.
- `candidate/taobao-operands-bounded-smoke-verified.json` independently accepts all 16
  complete MCP collections from those four trials: exactly 2163 string-use and 56791
  explicit type-operand sites per corresponding collection, zero missing or extra sites
  for either implementation. Native string indexes and counts for all 12495817 instructions,
  606974 methods and 33709 methods without code match original-byte decoding. The verifier
  checks the source-to-original DEX mapping, all page/retry metadata and sidecar hashes;
  original, product runtime and verifier/decoder sources remain unchanged. The oracle's
  temporary bundle is removed. This closes this Taobao correctness cell, not the remaining
  corpus, five-round latency, baseline, Windows or package cells.
- The v0.2.4 baseline wheel was built offline from the detached, unchanged baseline source
  and installed only under `baseline/runtime`, not over the active environment. Its import
  and native accelerator paths were read back from that directory; the baseline accelerator
  correctly lacks the new `type_operands` capability. Use an explicit per-command PYTHONPATH
  to select it for old-string measurements, and current `src` for candidate measurements.
- The next frozen harness additionally samples and caps its own client RSS (1024 MiB by
  default, separate from descendant RSS) and bounds complete-trial elapsed time (600 s by
  default). A bound violation stops only owned descendants, retains all recorded attempts
  and fails the trial; partial collections are not accepted. `client-rss-guard-red.xml` and
  `trial-deadline-red.xml` preserve the missing-stop regressions; `runtime-safety-guards.xml`
  passes 177 cases. The graph receipt verifier was also adapted to the hash-bound sidecars.
  A broader unconfigured harness check passed 190 cases but skipped four JVM-fixture cases;
  those skips are not acceptance and are being rerun in the fully configured source gate.
- `candidate/wechat-operands-first.json` completes one fresh paired round with two complete
  concurrent string/type collections per server, under an explicit 180 s complete-trial
  bound. Both servers pass transport/CPU/resource/identity checks. Independent decoding is
  pending; this single paired round does not establish performance acceptance.
- `candidate/source-full-freeze.xml` passes all 1599 tests with zero failures/errors/skips
  on local Linux/Python 3.13 in 582.81 s, including the configured graph-fixture cases that
  were skipped in the narrower unconfigured run. Product files remain the same frozen
  runtime as the large-input receipts. This candidate is ready for development-branch CI;
  Windows/canonical-sdist/native-wheel gates and the remaining B1 matrix are still open.
- Candidate commit `3b1de370bbfcebbd7547c1681ade2ca6259fca02` is pushed only to
  `codex/competitor-gap-b1`; CI run `40458754727` is active. No main merge, tag or release
  was performed. CI completion and downloaded per-cell receipts must still be inspected.
- `candidate/wechat-operands-first-verified.json` accepts all eight full MCP collections:
  738 string-use and 44002 type-operand sites, with zero missing/extra sites for both
  products. Native diagnostics match 865327 methods, 21430036 instructions and 41085
  methods without code. Original, runtime and all bound verifier/sidecar inputs are
  unchanged; oracle cleanup is verified. The one-round performance limitation remains.
- `candidate/douyin-operands-first.json` fails the explicit 180 s complete-trial bound for
  both products. Ours returns all 4778 string sites but only the first 1000 of 115306 type
  sites before another long worker query is stopped. The comparator completes its first
  pair of collections but not its second. This is a measured remaining gap, not a pass.
- `candidate/douyin-spool-diagnostic.json` confirms the cache cause through the existing
  native scanner/spool: the 16 MiB lease raises `SQLITE_FULL` after 60658 stored rows while
  13.6 GB of temporary storage remains available, so no complete set is published. The
  same uncached page and diagnostics compare equal. In-process scans with and without
  the spool take about 52 s each; they are diagnostic, not matched MCP performance numbers.
- **Evidence-backed B1.3 follow-up:** retain the current spool, publication, identity and
  quota architecture, but encode selected rows in bounded independently compressed
  SQLite blocks instead of one repeated JSON string per site. Keep the 16/32 MiB entry/
  session limits, flat public response, exact ordering and byte-page bounds unchanged.
  Bound both writer buffers and decompression, reject malformed blocks, and repeat legacy
  method/field, cancellation, quota, source/transport and package gates. A storage-only
  estimate from the comparator's complete first type collection yields 29.7 MB raw row
  JSON versus 2.0 MB in 901 blocks (128 rows/64 KiB targets); this is motivation, not an
  accuracy oracle or accepted implementation. This is selected-result storage, not a retry
  of previously rejected whole-APK preparation/compression changes. B1 remains unaccepted;
  commit 3b1de37 and its CI remain the pre-follow-up baseline, not evidence for new code.
- CI run `40458754727` completed successfully for `3b1de37`: all 25 jobs pass, including
  Linux/Windows source, distribution, signing, Rust and stability gates. The eight downloaded
  source JUnit receipts each contain 1599 tests and zero skips/errors/failures. These are
  pre-block-storage results; they cannot close the new candidate's cross-platform gate.
- The selected-set follow-up stores at most 128 rows or a 64 KiB target per compressed
  SQLite block; a single legal wide row retains its existing 256 KiB bound. Decoding has
  explicit compressed/uncompressed bounds, rejects extra streams/trailing data, and reads
  only blocks intersecting the requested page. Public rows, duplicates, offsets and quotas
  are unchanged. An accounting regression initially charged the last compressed block
  rather than the owned SQLite/receipt files; `block-accounting-red.xml` preserves it.
  The corrected accounting is checked against actual owned file sizes.
- `candidate/block-cache-bounds.xml` passes 98 cases; `block-scanner-transport.xml` passes
  all 249 selected scanner/string/type/cache/page/real-stdio-and-HTTP cases without skips.
  Corrupt layouts/payloads, decompression bombs, wide rows, byte paging, cancellation and
  actual storage accounting are covered. The wide-operand fixture now uses deterministic
  distinct high-entropy identities, so the unchanged 64 KiB overflow case still overflows
  after compression rather than accidentally becoming a fitting-cache test. Historical
  failed block-cache attempts are retained. Large-input evidence is being regenerated.
- `candidate/douyin-operands-blocks-smoke.json` completes both fresh-server trials with
  two full concurrent string/type collections per product. Ours now completes all 115306
  type sites; its first unseen type page reports selected-set reuse and 3174751 retained
  bytes for both stored queries, within the unchanged 32 MiB session/16 MiB entry quotas.
  The first/repeated complete pairs take 95.0581/36.6602 s versus 145.8802/58.4986 s for
  the comparator in this one paired round. All source/input/resource checks pass, but
  this is not the five-round performance gate. The complete-trial bound is explicitly
  600 s for both, unlike the failed earlier 180 s run; no failed-subset ratio is used.
- The first offline Douyin oracle attempt used an insufficient 900 s deadline: after
  229 s only eight of 53 DEX files had been decoded. It was stopped deliberately before
  that deadline and its original running receipt retained alongside
  `douyin-operands-blocks-verifier-budget.json`; owned processes and the exact temporary
  bundle were removed. Independent verification restarts under a declared 2400 s bound
  in `douyin-operands-blocks-verified-2400s.json`. This is an offline acceptance budget,
  not an increased product or MCP performance limit. Partial decoding is not acceptance.
- `candidate/block-source-full.xml` passes all 1628 configured source tests in 689.59 s,
  with zero failures/errors/skips. Ruff, formatting, both generated-schema checks and
  whitespace checks also pass. The independent offline Douyin oracle ran concurrently
  with this correctness suite, not with the timed MCP trial. This candidate is ready for
  its own development-branch CI; neither the prior commit's CI nor this source gate
  substitutes for current Windows/distribution evidence or remaining B1 performance cells.
- Candidate `b71962411f3a00c10ebf78331278dc1f23b89a88` is pushed only to the development
  branch. CI `40464186953` is its separate current matrix; no main merge/tag/release occurs.
- `douyin-operands-blocks-verified-2400s.json` completes independent decoding of all
  53 original DEX files: 2708565 methods, 52547329 instructions and 213254 methods without
  code. All four product collections match exactly (4778 string/115306 type sites), as
  do both comparator type collections. Both comparator string collections contain one
  extra site, so the combined receipt correctly stays **failed**, with unchanged bound
  inputs/runtime/oracle and verified temporary cleanup. `douyin-comparator-extra-string.json`
  independently localizes it to byte offset 600 outside a 598-byte method in classes9.dex;
  the last real instruction is return-void at byte offset 596. Comparator source only
  checks a prefix within coarse 16-byte buckets, not the exact method end. Preserve this
  correctness defect, do not copy it or discard the extra site to obtain a speedup ratio.
  The earlier concurrent timings are observed workload times, not equal-correctness parity.
- Frozen B1 holdout `org.fdroid.fdroid.apk` completes the new paired MCP smoke and all
  eight independent collection checks: 62 string sites and 1772 type sites, zero missing
  or extra sites for either implementation. Original-byte diagnostics cover 117352 methods,
  1692420 instructions and 5126 no-code methods. Both source/input identities and oracle
  cleanup pass in `holdout-operands-blocks-smoke.json` and
  `holdout-operands-blocks-verified.json`. This is one round, not performance acceptance.
- CI `40464186953`, job `122056346620`, fails the Linux Python 3.11 installed-wheel gate:
  1627 tests pass and the synthetic competitor full-collection timing case fails. Its
  asynchronous disk sample can still be in flight when the trial judges sample completeness,
  before the existing final monitor join. A delayed-sample test deterministically reproduces
  this for both products in `monitor-completion-red.xml`; do not classify it as flaky and
  merely rerun. The harness now joins that monitor after the measured close response and
  before judging resource gates or deleting the temporary root. Late sample errors and
  quota violations still fail; decoded-response timing boundaries are unchanged.
- `monitor-completion-verifiers.xml` passes 183 focused harness/verifier cases, including
  delayed sample completion/error/over-quota cases. Product runtime bytes are unchanged
  from b719624; the benchmark harness hash changes, so fresh timing receipts name it rather
  than silently relabeling earlier measurements. A new real-MCP holdout smoke is in progress.
- The same CI matrix also exposes a Windows test-collection/setup error: pytest derives
  the decompression-bound test ID from its 263168-byte argument, exceeding Windows'
  32767-character environment-variable limit for PYTEST_CURRENT_TEST. Jobs 122056346594,
  122056346627 and 122056346681 report 1627 passes/two errors for this case. Explicit short
  descriptive parameter IDs fix the test portability issue without reducing its payload;
  collected lines now have maximum length 111. Current Windows acceptance still requires
  a fresh matrix, not a Linux-only inference.
- `candidate/ci-followup-focused.xml` passes all 281 cache/harness/verifier tests, zero
  skips. `holdout-monitor-joined-smoke.json` completes four alternating fresh-server trials
  on the final monitor ordering; `holdout-monitor-joined-verified.json` accepts all 16
  complete string/type collections with unchanged identities and verified cleanup. Full
  source/CI reruns remain open for this test-and-harness-only follow-up; product runtime
  bytes are unchanged from the independently accepted b719624 candidate.
- The next five-round Taobao two-CPU measurement uses the frozen b9f98c8 harness and
  three separate scenarios: complete string, complete operand-type and concurrent complete
  string/type collections. Keep all 30 fresh-server trials in
  `candidate/taobao-final-operands-cpu2.json`; the earlier single/two-round smokes are not
  substituted for it. No product source edits or native rebuilds occur during measurement.
- Baseline regression timing needs alternation between the **product revisions**, not
  all old runs after all new runs. `scripts/benchmark_revisions.py` reuses the same
  supervised real-MCP trial, CPU wrapper, resource bounds and hash-bound spill writer;
  it alternates baseline/candidate each round and replays every page/retry after timing.
  Complete rows and diagnostics must match after removing only per-session identity and
  already-documented cache/page execution fields. Each revision's actual imported package
  and native extension are read back under the same interpreter before/after the run.
  Old v0.2.4 has no equivalent operand scope, so this comparison admits only full string,
  method, field and method/field concurrency, never old broad-type queries as operands.
  `revision-harness-red.xml` records the initially missing wrapper; 15 focused identity,
  replay, tampering, response-limit recovery, alternation/spill/environment restoration
  checks pass in `revision-harness-replay.xml`. Real revision acceptance is still pending.
- `revision-holdout-smoke.json` completes eight fresh baseline/candidate servers across
  full string, method, field and method/field concurrency. All 20 complete collection
  digests (two repeats, including both concurrent queries) match across revisions, with
  original/runtime/helper identities unchanged. This is a functional one-round smoke,
  not the five-round no-regression gate. Full configured source then passes 1649 tests
  without failures/errors/skips in `revision-source-full.xml` (276.36 s).
- `taobao-final-operands-cpu2.json` completes all 30 alternating trials. Independent
  `taobao-final-operands-cpu2-verified.json` accepts all 80 complete collections for both
  products: 2163 string sites and 56791 type sites, zero missing/extra sites, all scan
  diagnostics and original/runtime/sidecar identities checked, oracle cleanup verified.
  Median first/repeated complete-query times (ours/comparator, seconds) are string
  1.0642/3.9659 and 0.3462/0.5914; type 14.4626/17.9456 and 7.5950/12.9306; concurrent
  13.8202/24.9468 and 7.6494/14.0488. Process-start-to-complete medians are respectively
  3.7589/5.2888, 17.0175/19.2732 and 16.1403/26.1577. Every paired round favors ours for
  these metrics: startup paired savings range 1.1620-1.6597 s (string), 1.7662-3.6100 s
  (type), and 8.3783-10.4694 s (concurrent). This closes this two-CPU Taobao comparison
  cell, not the four-CPU/other-input matrix or old-version regression gate. No p95 claim.
- CI `40465990968` completed all 25 jobs successfully on b9f98c8, including the previous
  Windows test-ID and Linux installed-wheel failure cells. Downloaded per-source receipts
  are being inspected. The newly added revision wrapper/source gate is a later change;
  this green CI is not relabeled as its canonical-distribution acceptance.
- All eight downloaded source JUnit files from CI 40465990968 contain 1634 tests with
  zero failures/errors/skips (Linux/Windows, Python 3.10-3.13). Taobao's five-round operand
  comparison still exposes output/storage costs: across both repeats, native/competitor
  page counts are 40/20 for strings, 610/400 for types and 650/420 concurrently, with zero
  retries. Concurrent peak descendant RSS is 160616448/930967552 bytes, but ours also
  retains up to 119199188 sampled temporary bytes versus zero comparator trial files.
  These tmpfs/storage costs are not erased by lower process RSS; B2/B4 remain real work.

Reproduce alternating old/new complete-workflow regression timing (fresh output required):

```sh
PYTHONPATH="$PWD/src" uv run --offline --no-sync --with ./artifacts/aimard-asc-mcp python scripts/benchmark_revisions.py artifacts/large-device-corpus-20260921/com.taobao.taobao-10.62.0.apk --baseline-runtime artifacts/competitor-gap-b1-20261027/baseline/runtime --candidate-runtime src --scenarios full_string full_method full_field full_concurrent --rounds 5 --repeats 2 --workers 2 --expanded-mib 768 --session-disk-mib 8192 --output artifacts/competitor-gap-b1-20261027/candidate/taobao-revisions-rerun.json
```

Reproduce full-collection smoke and verification (choose new output names):

```sh
PYTHONPATH="$PWD/src" uv run --offline --no-sync --with ./artifacts/aimard-asc-mcp python scripts/benchmark_competitor_runtime.py artifacts/device-corpus-20260921/com.termux.apk --scenarios full_string full_type full_operands --rounds 1 --repeats 2 --workers 2 --expanded-mib 128 --session-disk-mib 8192 --output artifacts/competitor-gap-b1-20261027/candidate/termux-operands-rerun.json
PYTHONPATH="$PWD/src" uv run --offline --no-sync --with ./artifacts/aimard-asc-mcp --with androguard==4.1.4 python scripts/verify_operand_page_benchmark.py artifacts/competitor-gap-b1-20261027/candidate/termux-operands-rerun.json artifacts/device-corpus-20260921/com.termux.apk --output artifacts/competitor-gap-b1-20261027/candidate/termux-operands-rerun-verified.json
```

Next acceptance work: The v0.2.4 baseline lacks operand scope; do not compare its broader type query to
the new narrow result as equal semantics. Independently project/verify any baseline
equivalent workflow and count all of its work, or report that baseline cell unavailable.
Finish WeChat/Douyin and a frozen held-out input, full MCP site equality, cache fit/overflow
coverage and the five-round comparisons before calling performance accepted. No benchmark
speed ratio follows from the scanner oracle or scan-elimination tests above.

Update this ledger after each work package with current/next task, changed modules,
commands, evidence paths, verified outcomes, failed attempts and blockers. Preserve original
receipts and record decisions before changing public behavior. Completion means the named
gates passed on the same frozen runtime, not that tests were added or a time budget ended.

## Release candidate v0.2.4, 2026-10-27

The maintainer approved freezing the current workflow increment, correcting the stale
nullable-schema assertion and publishing v0.2.4 only after fresh source, cross-platform
and exact-package acceptance. The published baseline is consolidated v0.2.3 at 12a4fc5;
the withdrawn historical v0.2.4 is not this candidate. Existing tags and releases remain
unchanged. Release scope is selected-reference reuse, byte-bounded paging, compact artifact
summaries, raw DEX entry browsing and method-selector handoff, not overall goal completion.

The initial local assessment is retained under artifacts/release-assessment-20261027:
1487 passed, one stale `anyOf` assertion failed and two Rust checks lacked configuration;
the two Rust transport checks passed separately after configuration. The corrected test
checks nullable-integer acceptance and rejects unrelated JSON types without prescribing
the equivalent schema encoding. Fresh release evidence belongs under
artifacts/release-024-20261027; old CI results do not approve this candidate.
Final CI, package and publication receipts are recorded with the release, after the frozen
commit is accepted. Startup/storage, universal repeat-query superiority and broader workflow
and graph-completeness objectives remain open independently of this incremental release.

The first candidate's Windows gate exposed a leaked SQLite handle in the corruption-test
fixture, not in the product cache. The corrected fixture commits and closes before cleanup;
an explicit closed-handle assertion reproduces the defect on Linux too. CI 40430197917
and its packages remain rejected. Complete logs also reveal a coarse-clock Windows unit-test
failure; deterministic fake-response timing now verifies exact full-collection accounting.
The SQLite-only candidate passes all 1490 local tests; its CI 40431741392 is superseded and
cancelled. Production and real benchmark runtime stay frozen; final source/package gates
are refreshed under artifacts/release-024-20261027/candidate3.

## Consolidation history

Status: active. On 2026-10-23 the maintainer requested consolidation of v0.2.3-v0.2.9
into a freshly built and accepted v0.2.3, preserving all current source improvements and
v0.2.2 and earlier releases. The seven releases, assets and tag objects were backed up
and verified before withdrawal under artifacts/reissue-023-20261023/backup.
This consolidation does not close the overall performance, workflow/source-comparison
or accuracy objectives. Workflow completeness and ergonomics remain mandatory criteria.
Release notes follow the established Highlights / Acceptance / Install / Limits format.
The consolidation is published at commit 12a4fc51ba36a64a54bc3623dc348a499f466ac9;
CI 39939932398 passed all 25 jobs, including Linux/Windows Python 3.10-3.13 source,
canonical-sdist and exact native-wheel acceptance. Release assets and retained/withdrawn
versions were read back; see VALIDATION.md. New workflow changes remain on a separate
development branch and have no publication approval from those earlier receipts.

## Current workflow candidate

On codex/workflow-triage-next, artifact inspection can optionally return a compact,
hash-bound manifest header, entry count and native ABI inventory in one call. Method
trace prompts now accept exact class/name selectors and optional overload prototypes,
using the existing query validator and preserving full-descriptor handoff.
Local Linux Python 3.13 source regression passes 1213 tests, zero failures/errors/skips:
artifacts/workflow-triage-20261023/source-full.xml. This includes real stdio/HTTP triage,
prompt selector handoff, invalid-selector recovery and binary-manifest summary checks.
scripts/verify_artifact_summary.py passes the separate original-ZIP and pinned-competitor
summary oracle for all three private Taobao, WeChat and Douyin APKs. The final receipt is
artifacts/workflow-triage-20261023/large-summary-parity-final.json, with unchanged input,
runtime and verifier hashes. This is summary parity, not a speed or DEX-accuracy claim.
This candidate is not published. The final e3f3819 runtime passes the refreshed
cross-platform/source/package gates recorded below; earlier local counts are historical.
The broader workflow exercise and startup/memory/graph/concurrency criteria below stay open.

Startup/storage experiments on this candidate are recorded in
STARTUP_STORAGE_EXPERIMENTS.md. Larger SQLite batches, native key encoding, ordinary
Deflate recompression and two cursor micro-optimizations did not establish a robust
cross-input benefit and are not retained. LZ4 component measurements alone do not approve
a production format or dependency. The original-compressed-payload/two-slot inflation
prototype also remains isolated: all 27 three-APK/four-CPU direct trials preserve complete
owners, metadata, expanded DEX hashes and first field pages, but first use and repeats slow
down while query RSS increases. Retained files fall 57-60%, not an all-resource or latency
win. No production replacement is adopted; byte-budgeted large-member, Windows, 041 and
source-handoff acceptance are not claimed from this rejected pilot.
At d356da3 the runtime was unchanged from b02c180; the added opcode boundary/counter
regressions increased the complete local Linux Python 3.13 suite to 1231 passing tests,
zero failures/errors/skips: artifacts/startup-next-20261023/source-full-retained-runtime.xml.
This is not a new Windows or canonical-distribution gate.

The real stdio/HTTP parameter exercise now covers all four exact/fuzzy owner/name
combinations for two method overloads and same-named I/J fields, exact prototype/type,
omitted member names, case-sensitive misses, complete one-row pagination and beyond-end
pages. A discovered archive path is also followed through nine bounded content pages to
reconstruct 1,048,832 exact original bytes, then an EOF and invalid-offset recovery check.
The targeted four transport cases pass without skips:
artifacts/startup-next-20261023/workflow-parameters-targeted-fixed.xml.
This strengthens specific workflow evidence, not an assertion that all parameter behavior
or the final cross-platform release gate is closed.

Reading the competitor's raw-file entry branches exposed a concrete remaining gap.
The candidate now accepts standalone DEX paths in the two entry tools, using the existing
supervised worker, input roots/size limits and full before/after identity/hash checks.
Pages retain original bytes/basenames, including physical 041 headers, and do not invent
ZIP CRC or code-validation metadata. Archive inventory/session routing stays unchanged.
The entry/archive/container/schema/real-transport selection passes 178 cases, zero skips:
artifacts/startup-next-20261023/raw-dex-targeted-zero-skips.xml.
The full current Linux Python 3.13 source suite passes 1262 tests in 212.53 seconds,
zero failures/errors/skips, including both transports and the regenerated input/output
schemas: artifacts/startup-next-20261023/source-full-raw-dex-entry.xml.
Candidate-branch Windows and canonical-package acceptance must identify this new runtime;
the earlier b02c180/d356da3 receipts are not reused for it.

Fresh current-runtime field comparisons, full original class-owner/snapshot checks and
the selected full-reference oracle are recorded in STARTUP_STORAGE_EXPERIMENTS.md.
WeChat still loses 0.5736 seconds at process-start-to-first-result; lower query RSS does
not remove the tmpfs-backed preparation-file cost. These remain explicit open gaps.
The oracle driver now constructs Path in its native child command; two regressions
execute that command against a path-checking stub. With this test-driver-only fix, the
local Linux Python 3.13 suite passes 1264 tests in 207.20 seconds, zero failures/errors/skips:
artifacts/startup-next-20261023/source-full-entry-oracle-driver.xml.
CI 39962833696 is bound to f144c0849eb3bab878b79d8fe6472ef1c87b7d25, before those
two driver regressions; it must not be described as a 1264-test gate or release approval.
Its Windows live log reveals setup/teardown errors: automatic IDs embedded the complete
large XML parameters in PYTEST_CURRENT_TEST, exceeding Windows' 32767-character limit.
The seven manifest diagnostic cases now use fixed short IDs and assert a bounded node ID;
their original payloads and parser assertions are unchanged. All 31 summary/driver tests
pass locally without skips: artifacts/startup-next-20261023/windows-id-fixed-targeted.xml.
The failing first attempt remains evidence, not acceptance. The corrected candidate at
e3f381927c98976d4b2052ec29e0d86136e47c48 passes CI 39967501671: all 25 jobs,
1264 tests with zero failures/errors/skips in each Linux/Windows Python 3.10-3.13 source
cell and for each canonical-sdist/exact-wheel installation. Seven signing variants per
source cell, Rust and stability gates also pass. The downloaded ZIP digests, 24 extracted
files, packaged runtime source and installed-wheel identity are verified in
artifacts/workflow-entry-ci-39967501671/acceptance-summary.json.
The exact Linux CI wheel independently passes every original class/owner and snapshot byte
across Taobao/WeChat/Douyin (884805 identities), and all selected Taobao method/field rows
and diagnostics over three rounds: wheel-original-accuracy.json under the same evidence root.
The source worktree, wheel bytes, installed runtime and verifier remain unchanged throughout.
These gates do not close the startup/storage or broader comparative-workflow criteria, and
do not approve a new publication. main and the existing v0.2.3 tag remain at 12a4fc5.

A fresh 27-trial 64/128/256-KiB prefetch sweep suggested preparation gains, but the actual
18-trial real-stdio before/after comparison did not preserve them at first result: WeChat
and Douyin each regress in two of three pairs. The change is removed; production remains
byte-identical to e3f3819. The separate bounded-memory compact pilot also remains rejected
as a default. See STARTUP_STORAGE_EXPERIMENTS.md for complete receipts and resource costs.
Two new full-queue abandonment regressions pass alongside all container/directory cases
(68 tests, zero skips); these are test-only additions, not a new full cross-platform gate.

The current three-APK concurrent corpus now has 36 passing real-stdio trials across two/four
CPU budgets, three alternating rounds each, with equal 4096-MiB aggregate RSS and 8192-MiB
temporary-file caps. All cold/first-complete-batch/repeat medians favor the product for
these method+field pairs; see STARTUP_STORAGE_EXPERIMENTS.md. Inputs, both runtimes and
harnesses remain unchanged. This does not close the separate single-field startup deficit,
storage cost, broader graph comparison or all-query accuracy.

Complete real-MCP reference pagination additionally matches an independently inventoried
original-byte JVM oracle for 98581 method/field sites across all three APKs, 200 successful
pages and full scan diagnostics. Final receipts: current-reference-pages-corpus-final.json
and its three per-APK final reports under artifacts/startup-next-20261023. Failed attempts
and the verifier's missing-DEX/swapped-mapping regressions remain separate evidence.
The final verifier/container/directory selection passes 95 tests, zero skips; no runtime
change or new full cross-platform gate is implied. The existing exact-page cache key includes
offset/limit and unseen pages rescan instructions. Measure full-collection scan amplification
against the competitor rather than inferring paging performance from first-page timings.

The complete-collection pilot now confirms that deficit on all three inputs. First method
collection is 27.1845/36.6546/158.3533 seconds versus the competitor's
5.3954/6.6087/14.4882; second full collections still miss every product page-cache entry.
Every method site matches an independent original-byte oracle for both implementations.
The competitor's Taobao field result instead has 97 extra sites; five independently decoded
examples exceed their named caller's instruction stream. This is not an accuracy target to
copy. See STARTUP_STORAGE_EXPERIMENTS.md for one-round scope, complete receipts, resources
and exact distinctions from earlier first-page/concurrent comparisons. Query-wide selective
result reuse and its host paging path now have priority over cursor micro-optimizations.
An isolated streamed-SQLite/host-reader pilot reduces those first collection observations
to 4.9700/5.2038/10.4062 seconds, with every product row and diagnostic independently equal.
It is not production code or final before/after acceptance: Taobao/Douyin still lose to the
paired competitor at complete-result startup and on repeat; combined session reservations,
concurrent publication, invalidation, corruption and cancellation remain implementation work.
The private prototype and receipts are preserved in STARTUP_STORAGE_EXPERIMENTS.md.

The 2026-10-24 development runtime now implements selected-result streaming and host
pagination, with session-accounted 32-MiB quotas, 16-MiB pending/completed entry leases,
same-selector page scheduling, concurrent private publication, whole-file verification,
invalidation, cancellation and cleanup. Oversized sets and unavailable cache space retain
the normal scan path. The focused suite passes 196 cases with zero skips, including real
stdio/HTTP reference/fuzzy pages; 56 other integration cases were deliberately deselected.
Evidence: artifacts/selected-reference-cache-20261024/focused-transport-bounded-retry-final.xml.
The earlier claim that production still matches e3f3819 is historical, before this change.
Final large-input and comparative receipts belong to the new implementation; prototype
timings and the older e3f3819 Windows/package gates do not approve it for release.
The final bounded-retry corpus passes all 98581 independent selected sites/200 pages,
36 product collection replays and all 36 matched benchmark trials. The competitor's
six Taobao field replays still fail with 97 extra sites each; the other comparison
collections pass. Current first complete method query medians favor the product, but
all three repeat collections and Taobao/WeChat startup-to-complete remain slower.
Evidence: artifacts/selected-reference-cache-20261024/bounded-retry/summary.json.
This is concrete progress, not completion of the remaining startup, transport, graph,
workflow and cross-platform/package criteria below.

The subsequent output-schema increment reduces client nullable-field validation using
Pydantic's equivalent primitive type arrays, retaining the original strict runtime
contracts and falling back to original generation on older Pydantic versions. The
targeted transport/cache/contract gate passes 203 cases with zero skips and 52 deliberate
other-integration deselections. Three alternating frozen-source before/after rounds
per real APK reduce first/repeat complete-query medians in this corpus; one Taobao
pair regresses, so the change is not a universal-speed claim. See
STARTUP_STORAGE_EXPERIMENTS.md and artifacts/selected-reference-cache-20261024/.
Fresh original-byte and competitor comparisons are separate from the historical
bounded-retry/ run; the new runtime still needs its full cross-platform/package gates.
The schema-types/summary.json batch is complete: all 98581 original selected sites,
200 pages and 36 product collection replays pass; six comparator field replays retain
97 extra Taobao sites each. All 36 frozen before/after collections also match accepted
current full responses. First complete method queries and method startup favor the
product in this batch, but all three complete method-repeat medians and WeChat field
startup still lose. Those residuals, storage cost, broader workflow/graph comparisons
and new full cross-platform/package gates remain open.

## Competitor workflow closure

Complete-concurrency follow-up, 2026-10-24: all 72 product method/field collections
pass independent original-byte replay over three APKs and two/four CPUs. Twelve of 72
comparator collections retain the Taobao-field 97-extra-site failure. Four-CPU Douyin
repeated complete concurrency still loses at 7.5007 / 6.2604 seconds median, despite
favorable first-page results. The first graph batch also exposed a cancellation deadline
overrun; it is preserved as rejected timing evidence. The harness now enforces deadlines
with a separate owned-child watchdog and passes 110 focused tests with zero skips.
These are harness/acceptance improvements, not a production performance fix or closure of
the remaining workflow, storage, graph-completeness and cross-platform/package criteria.
The corrected same-budget graph batch now verifies all 24 measured bounded product
graphs against a fresh original-byte full index, plus independent emitted-site decoding.
All comparator trials time out around 30 seconds; no equal-success graph ratio is claimed.
Every product graph explicitly reaches its output-byte bound. This does not independently
prove full-corpus graph completeness. The final receipts are bound in
artifacts/graph-concurrent-20261024/summary.json, including the separately resumed offline
Douyin verification after a host reboot. No additional release is approved.

Latest paging increment, 2026-10-24: reference queries now return byte-bounded complete
prefixes at the original 256-KiB ceiling, retain the requested maximum limit and continue
at the exact next_offset. The targeted gate passes 288 cases with zero skips and 52
deliberate deselections. Fresh independent checks accept all 98581 selected sites over
148 pages and all 36 product collection replays; all 36 frozen before/after collections
also match complete accepted responses. Six comparator Taobao-field replays retain the
97-extra-site failure. The same three-APK timing batch has zero product reference retries,
but Taobao/Douyin complete-method repeats, Taobao method startup-to-complete and WeChat
field startup still lose. Paired before/after effects are also mixed, so fewer pages alone
do not close the performance goal. See STARTUP_STORAGE_EXPERIMENTS.md and
artifacts/adaptive-reference-pages-20261024/accepted/summary.json. Full workflow/graph,
storage and fresh cross-platform/package gates remain open; no new release is approved.

- [ ] Re-read the pinned competitor implementation and test all 25 tools, two resource
  templates, three prompts and 87 non-context parameters against implemented equivalents.
  Refresh the source inventory; distinguish inventory parity from exercised behavior.
- [ ] Exercise import/capability selection, triage/manifest, class/member/string/body search,
  outline/hierarchy, source/disassembly, exact and fuzzy references, multi-hop call graphs,
  resource/native-library browsing, signing, secret candidates and revision comparison.
- [ ] Exercise the complete investigation path through real MCP transports, including
  identifier handoff, overload selection, pagination, bounded truncation, resource links,
  prompt routing, failure recovery and cleanup. Fix missing or unnecessarily indirect steps.
- [ ] Record each equivalent, intentional semantic difference, residual limitation and its
  executable acceptance evidence in COMPETITOR_API_AUDIT.md. Do not label untested workflows
  better solely because their endpoints or output fields exist.

## Confirmed performance deficits

- [ ] Reproduce process-start-to-first-result, validated open and peak startup RSS under
  the same interpreter, input, worker budget and external limits as the competitor.
  Include retained snapshot/index bytes separately from process RSS, and identify RAM-backed
  temporary storage; lower warm process RSS alone is not a total-memory improvement.
- [ ] Profile and reduce actual startup/import, immutable preparation and first-query costs;
  do not omit preprocessing, drop integrity/duplicate checks or report premature readiness.
  The maintainer explicitly authorizes restructuring the affected framework/process/storage
  path if measurements establish an architectural bottleneck; local patches are not a limit.
  Revalidate all affected workflows, cleanup and resource boundaries after any such refactor.
- [ ] Re-measure repeated queries and fix any confirmed residual latency regression while
  keeping host caches bounded and not retaining a full-APK analysis object or worker pool.
  Include complete multipage collection and byte-limit recovery: complete selected sets
  now avoid rescans, but the measured full-collection paging/transport deficit remains.
- [ ] Freeze alternating cold/warm/concurrent and bounded-large-graph comparisons. Include
  both two/four-worker budgets, additional APK workloads, complete-result accuracy and
  separate process RSS versus index disk/tmpfs usage. Report failures and truncation plainly.

## Invariants

- [ ] Core queries, discovery, structure, indexes and default Smali never require JADX.
  Java source remains explicit opt-in; DEX 041 uses separate pinned normalization.
- [ ] Original input hashes, DEX checksum/signature checks, strict instruction/payload
  boundaries, Unicode identity, independent full-site/index parity and fail-closed errors hold.
- [ ] Preserve allowed roots, immutable sessions, cancellation/process-tree cleanup,
  per-query memory/output limits, disk/index/cache budgets and concurrent publication safety.

## 0.2.x release gate

- [ ] Select a coherent increment and finish its implementation before freezing its candidate.
  The consolidated v0.2.3 retains the accepted source at 159a6f3; only version metadata and
  release documentation change. Fresh acceptance is required for the rebuilt packages.
- [ ] All Linux/Windows Python 3.10-3.13 suites pass without skipped tests; real stdio/HTTP,
  signing, Rust and stability acceptance pass on the exact final commit.
- [ ] Clean source and native-wheel acceptance pass on Linux and Windows, using the exact
  same canonical release sdist; inspect installed and archive versions as the selected 0.2.x.
- [x] Back up existing v0.3.0, v0.4.0, v0.4.1 and v0.5.0 release metadata/assets and Git refs.
  Local backup: artifacts/release-renumber-20261022/backup; all asset digests verified.
- [x] Withdraw the four old releases/tags now, preserving v0.2.2 and earlier versions.
  Completed 2026-10-23; the four tags remain absent in the v0.2.8 publication readback.
- [ ] Only after an increment's acceptance: fast-forward main and publish its next 0.2.x tag
  using exact successful CI artifacts. The maintainer explicitly authorized reuse of v0.2.3
  for this consolidation; subsequent updates use new patch versions without rolling back code.
- [ ] Read back main/tag/release target, latest flag, asset versions and server/local SHA-256;
  verify withdrawn versions are absent and the worktree is clean before marking complete.

The active goal and this checklist must not be marked complete merely because a subset of
performance tests passes. Priority: large-APK startup/ZIP memory, workflow
closure and matched accuracy/performance receipts. Each selected increment then requires
unified cross-platform packaging and release acceptance. Candidate branch commits are allowed
for CI, not main/tag/release publication before that increment's gates pass. The original
all-gap completion goal stays active after an intermediate patch is published.

## Historical increment evidence, 2026-10-22

The v0.2.3-v0.2.9 publication statements below describe withdrawn releases and immutable
historical receipts, not current availability or acceptance of the consolidated build.
Original version labels and commit hashes are retained for auditability.

Update, 2026-10-23:

- Published increment: v0.2.8, main/tag target
  188853624a86b4d3159c2fd094fc3d6f42d6890b. CI 39900946375 passes all 25 jobs;
  all eight source cells pass 1155 tests without skips/errors/failures. Every distribution
  cell passes the complete suite from the same canonical sdist and its exact native wheel.
  Fresh source and wheel ownership oracles each verify all 884,805 owners and every snapshot
  DEX byte; bounded graph parity is scoped to the recorded unchanged-decoder comparisons.
  Published assets match server/local digests, main/tag agree, retained tags are unchanged
  and withdrawn versions remain absent. Evidence:
  artifacts/acceptance-0.2.8-ci-39900946375/{acceptance-summary,published-readback}.json.
  The direct-preparation storage measurements below do not become end-to-end speed claims.
- Selected v0.2.9 workflow increment: remove the extra declaration-discovery round trip
  when a class and method name identify a unique supplied definition. Resolve only in its
  owning checked DEX; return full identity, reject ambiguity and permit prototype filtering.
  This covers disassembly, source, incoming/outgoing calls and bounded graphs without Java
  or mandatory preprocessing. Re-read pinned competitor disassembly/graph source; current
  GitHub head remains 848c711f1d80a1c2577283f1fa5f475ff734aa40. New Smali and real-transport
  regressions precede final-runtime, cross-platform and canonical-package acceptance.
- Published increment: v0.2.7, main/tag target
  f7efd9a0f907280c31993b95535ec85ee5bf4494. CI 39866704262 passes all 25 jobs;
  eight source cells pass 1132 tests and seven signing variants each, with zero skips,
  errors or failures. All eight distribution cells test the same canonical sdist and
  their exact native wheel with the complete suite. Fresh source and CI-wheel ownership
  receipts each verify all 884,805 owners and every snapshot DEX byte. Independent fuzzy,
  call/string and bounded graph receipts pass in their recorded scopes. Published assets
  match server/local hashes and retained tags are unchanged. Evidence:
  artifacts/acceptance-0.2.7-ci-39866704262/{acceptance-summary,published-readback}.json.
  This query-memory increment does not close startup, retained-storage or workflow deficits.
- Selected v0.2.8 increment: dictionary-encode DEX owners in the SQLite class directory,
  keeping key order, logical budgets, integrity and legacy read-only formats. Five
  alternating rounds on each original APK preserve every owner, common metadata and full
  snapshot hash. Owner storage falls 21.5/26.3/27.4 percent on Taobao/WeChat/Douyin;
  total retained files fall only about 1-2 percent. Preparation medians (before/after,
  seconds) are 1.3484/1.1736, 2.2570/2.1293 and 5.0610/5.0386. The largest-input
  timing is effectively flat and process RSS is mixed; this is not a universal startup
  or total-memory win. Receipt: increment028-owners-before-after.json. Final-runtime
  independent ownership, real MCP, source, Windows and package gates remain required.
- The first v0.2.8 candidate CI (39899889877) fails its Windows Python 3.10.11
  distribution cell before extraction: tarfile lacks the newer filter keyword. The
  canonical-source acceptance helper now validates portable paths, duplicates and entry
  types before copying regular files into an empty temporary directory. Fourteen new
  regressions pass, including a legacy-API simulation. This failed CI is not release
  approval; the final candidate and canonical packages require a fresh complete run.
- Published increment: v0.2.6, main/tag target
  a0a34d77f0f21cac27b69a69c85070a663605916. CI 39858964129 passes all 17 jobs;
  all eight Linux/Windows Python 3.10-3.13 cells pass 1108 tests without failures,
  errors or skips and seven signing variants each. Both canonical-source/native-wheel
  distribution jobs pass. Fresh source and exact Linux CI-wheel ownership receipts each
  independently verify all 884,805 classes from the three original APKs. Published assets
  match local and server digests; readback verifies main/tag identity, the four withdrawn
  versions' absence and unchanged preexisting tag objects. Evidence:
  artifacts/acceptance-0.2.6-ci-39858964129/{acceptance-summary,published-readback}.json.
  This is an input-integrity increment, not startup/storage or complete-workflow closure.
- The next query-memory experiment replaces whole-member byte allocation with read-only
  stored windows, preserving ZIP header/overlap checks, complete CRC and the same checked
  native decoder. The initial per-call mapping variant is rejected: three alternating
  full-result field/fuzzy trials on each original APK preserve complete response hashes,
  but fuzzy query medians regress by about 19-33%. Its source patch and diagnostic are
  retained as increment027-per-call-experiment.patch and increment027-per-call-before-after.json.
  A second, dual-window variant also remains rejected: WeChat field-query median regresses
  from 0.8084 to 1.0658 seconds. Its source patch and complete diagnostic are retained as
  increment027-dual-window-experiment.patch and increment027-owned-window-before-after.json.
  The current experiment shares one read-only Python mapping with the checked native decoders
  through the public pinned-buffer API; all error paths release the export before unmapping.
  Python 3.10 uses its native wheel ABI and Python 3.11+ uses cp311-abi3, following the actual
  stable-buffer-API floor. Five alternating rounds on each original APK preserve all complete
  field/fuzzy response hashes in all 60 trials. Median query-child RSS decreases by 11-19%
  for fields and 14-17% for fuzzy references; retained tmpfs snapshot bytes are unchanged.
  Timing remains mixed: field medians (owned/mapped, seconds) are 0.4520/0.4912,
  0.6624/0.6266 and 2.3028/2.2131; fuzzy medians are 0.9917/0.9294,
  1.3418/1.3180 and 3.4103/3.4868 (Taobao/WeChat/Douyin). This is not a stable
  across-workload speed win or real-MCP/startup evidence. Receipt:
  increment027-shared-buffer-before-after.json. Final-runtime independent accuracy,
  original-workload MCP performance, full source, Windows and package acceptance remain
  required before adopting or releasing it.
- The pre-freeze shared-buffer source suite passes all 1132 tests, zero skips/errors/failures.
  Locally built cp310-cp310 and cp311-abi3 wheels load in isolated Python 3.10-3.13 environments
  and reproduce the complete fixture class/member/instruction results, including pinned-buffer
  failure cleanup. Receipts: increment027-source.xml and increment027-isolated-wheel-tiers.json.
  Those diagnostic wheels still carry pre-freeze 0.2.6 metadata and are not release assets.
  Those were pre-freeze results. Final v0.2.7 acceptance and publication supersede this
  candidate status as recorded above; no earlier receipt is relabeled as final evidence.
- Published increment: v0.2.5, main/tag target
  1b25267d2f123b03d722509f56425da347031818. CI 39847579502 passes all 17 jobs;
  each Linux/Windows Python 3.10-3.13 cell passes 1096 tests, zero skips/errors/failures,
  and seven independent signing variants. Both clean-distribution jobs verify the same
  canonical sdist and installed native-wheel bytes. Fresh source and exact Linux CI-wheel
  ownership oracles each verify all 884,805 original classes across the three APKs and all
  snapshot DEX bytes. The wheel additionally verifies all 2,914,002 Taobao call sites and
  2163 selected string sites independently. Published assets were downloaded and matched to
  local and server SHA-256 digests. Evidence:
  artifacts/acceptance-0.2.5-ci-39847579502/{acceptance-summary,published-readback}.json.
  Matched real-MCP field/fuzzy/concurrent trials pass on the three original APKs, but Douyin's
  field process-start-to-first-result median remains slower (19.5973 / 18.2279 seconds,
  ours / competitor, four CPUs). The competitor's three Taobao graph trials fail internally;
  their failure times are not graph-speed evidence. Snapshots retain about 119/184/485 MB
  on tmpfs; lower process RSS does not establish a total-memory win. Overall closure stays open.
- The 0.2.6 increment selects a confirmed input-integrity fix, not a performance claim: recheck
  original, reopened and freshly reopened handles after the last complete hash in both container
  preparation and archive reads. Windows identity comparisons consistently use fstat.
  Failed regressions are preserved as increment026-identity-before.xml and
  increment026-archive-final-hash-before.xml. The final targeted hash/archive selection passes
  90 cases, but full source, final-runtime ownership and cross-platform/package gates remain.
- The initial-hash/ZIP-inventory overlap experiment is not adopted. Three alternating rounds
  on three original APKs preserve complete metadata, every owner, every snapshot DEX hash and
  field-result pages. Preparation medians (baseline/experiment) are 2.3208/2.2244, 3.8609/3.9424
  and 7.7915/7.7844 seconds (Taobao/WeChat/Douyin), with no stable broad gain. Immutable retained
  bytes do not decrease. Receipt: increment026-preparation-before-after.json; experimental source
  and tests are archived alongside it. It does not describe the final serial-hash runtime.
  Earlier coarse-profile ru_maxrss values inherit a pre-exec high-water mark on this launcher
  and are not usable process-memory evidence; this alternating diagnostic samples actual RSS.
  The interrupted preliminary full-source run is retained separately and is not acceptance.
- The 0.2.5 preparation increment avoids allocating discarded ZipInfo objects for ordinary
  omitted resources. Timestamp extra-field bounds, all original name/mode/version/offset and
  duplicate checks remain active; other extensions use the unchanged stdlib decoder. Five-round
  alternating directory diagnostics compare all inventory names and every retained ZipInfo slot
  against independent stdlib results on three original APKs. Median directory CPU seconds decrease
  from 0.08159/0.26339/0.87671 to 0.04712/0.13073/0.56246 (Taobao/WeChat/Douyin).
  Receipt: artifacts/release-renumber-20261022/increment025-directory-before-after.json.
  A separate complete preparation diagnostic preserves identical full metadata, ownership
  directories, retained bytes and field pages, but noisy wall time is mixed and Douyin's median
  regresses. It is not evidence of an end-to-end improvement. Receipt:
  increment025-preparation-before-after.json in the same directory. Startup/storage goals remain
  open. At that pre-release diagnostic stage, fresh independent ownership, real MCP,
  Linux/Windows and clean-package gates remained required; the accepted v0.2.5 receipt above
  records their subsequent completion without reinterpreting the mixed timing results.
- Published increment: v0.2.4, main/tag target
  29475d9f58edc09969ee08bd6491bd515752a41a. CI 39836635008 passes all 17 jobs;
  the eight Linux/Windows Python 3.10-3.13 cells each pass 1075 tests, zero skips/errors/failures.
  Both clean-distribution jobs pass canonical-sdist and native-wheel acceptance. Fresh independent
  string oracles match all 7679 selected use sites across 86,473,182 instructions in the three
  original APKs; fuzzy matching verifies 28,110 Taobao sites. The exact Linux CI wheel verifies
  2163 string sites and all 2,914,002 persisted call sites. All four published assets were
  downloaded again and matched to local and GitHub SHA-256 digests. Evidence:
  artifacts/acceptance-0.2.4-ci-39836635008/{acceptance-summary,published-readback}.json.
  This closes the literal-string increment only. Startup/storage and the full workflow/performance
  closure remain active; the following pre-release entries retain their original chronology.
- Published increment: v0.2.3, main/tag target
  4c28572935eda91bd8250c54d1663526d532a858. CI 39826824176 passes all 17 jobs;
  each of the eight Linux/Windows Python 3.10-3.13 cells passes 1019 tests without
  failures/errors/skips. Both clean-distribution jobs use the same canonical sdist and
  verify installed native wheels. The release contains the exact successful CI packages;
  downloaded asset hashes and GitHub server digests match. Receipt root:
  artifacts/acceptance-0.2.3-ci-39826824176; release-published.json,
  acceptance-summary.json and published-readback.json record the accepted increment.
  This closes that release's gates only, not the remaining overall goal or v0.2.4's gates.
- The larger-prefetch experiment is not adopted. Alternating three-round direct preparation
  probes on Douyin/WeChat/Taobao compare 64/256-KiB blocks with unchanged runtime/input and
  identical complete preparation metadata. Douyin improves, but the other medians regress
  and peak RSS increases. Other project tests also introduce host contention; the receipt
  is diagnostic rather than valid evidence of a stable latency advantage. Production keeps
  its two bounded 64-KiB streams. Receipt: increment024-prefetch-probe-cpu4.json.
- Source review found an avoidable literal-string handoff gap: the old string-use workflow
  required clients to escape discovered text as a regex. An in-progress find_string_refs
  operation accepts it unchanged, scans const-string/jumbo with the checked native cursor,
  uses a compact 32-bit-pool bitset, and preserves old find_refs semantics. It remains
  unaccepted for release until independent large-APK, full source, Windows and clean-package
  gates pass. Preparation/storage/startup performance work remains open independently.
- The 0.2.4 increment selects literal-string handoff, checked 32-bit string operands and
  native ASCII pool matching. Profiling identified per-string Python decoding as the initial
  regression; validated ASCII matching now uses a linear-time cursor, while Unicode entries
  and malformed encodings retain strict Python decoding. Three-round alternating real-stdio
  string trials pass on Taobao (four CPUs), WeChat (two) and Douyin (four), with unchanged
  input/runtime/installed competitor and verified descendant CPU affinity. Cold batch medians
  are 0.6325/1.8091, 0.6809/3.6947 and 1.9230/6.6112 seconds respectively (ours/competitor).
  Process-start-to-first-result medians are 3.2130/3.3581, 4.0617/5.1220 and 8.3953/8.8902.
  These are workload-specific measurements, not universal startup or total-memory wins.
  Retained snapshots/tmpfs remain a separate cost and the overall startup/storage goal stays open.
  Receipts: increment024-{taobao-affinity4-ascii-pool,wechat-affinity2-ascii-pool-512mib-8gib,
  douyin-affinity4-ascii-pool-512mib-8gib}.json under artifacts/release-renumber-20261022.
  The earlier slow-string and undersized expansion/reservation-budget failures are retained;
  complete final-commit accuracy, Linux/Windows and canonical-package gates remain required.

- Withdrawal preflight re-read all four live releases and matched metadata, all 16 asset
  sizes/SHA-256 values and remote tag objects to the verified complete Git bundle. All four
  GitHub releases and remote tags were then removed; the retained five release/tag identities
  are unchanged and v0.2.2 is latest. Receipt:
  artifacts/release-renumber-20261022/backup/releases-after-withdrawal-20261023.json.
- The candidate metadata is now 0.2.3; README installation links point to the actually
  retained 0.2.2 and explicitly distinguish prospective 0.2.3 native-wheel installation
  commands, which are unavailable before acceptance publication. No new release, tag or
  main merge has occurred. This changes numbering/rollout, not the remaining completion scope.
- Fresh frontier/full-index traversal checks pass all nine direction/depth combinations:
  frontier-filter-full-index-graph-parity.json. A separate complete sequential Androguard
  call-index oracle matches all 2,914,002 persisted sites and 12,495,817 instructions on this
  runtime: frontier-filter-call-index-parity.json. That large APK contains no dynamic sites;
  it cannot by itself validate invoke-polymorphic formats.
- A compiled fixture exposed Androguard's unimplemented generic method-reference API for
  formats 45cc/4rcc. Acceptance scripts now use its decoded BBBB/HHHH operands and bind their
  own/helper hashes. The failed receipt is preserved. Both compiled polymorphic formats pass
  real MCP and independent site/full-index checks, including exact call-site prototypes:
  frontier-filter-polymorphic-both-formats-{mcp,full-index}.json. The refreshed large-APK MCP
  check independently verifies all 260 emitted sites, not unlimited graph completeness:
  frontier-filter-real-mcp-graphs-polymorphic-fixed.json. All 12 graph-script tests pass.
- The new cross-interpreter source selection initially found three failures on Python 3.10:
  historical environments still contained droidasc 0.1.2.post2, below the declared post3
  minimum. Preserve frontier-filter-py3.10-unsupported-post2.xml as failed evidence. All four
  owned test environments now have post3. The subsequent complete Linux source matrix passes
  989 tests per interpreter on Python 3.10-3.13, with zero failures/errors/skips and identical
  runtime hashes before/after. Receipts: increment023-source-py3.{10,11,12,13}.xml. These
  supported-upgrade environments use Pydantic 2.14.1; locked CI uses 2.13.5. This is not the
  frozen Windows/canonical-distribution gate or a performance comparison.
- The next full-source run exposed five schema-test assumptions under supported Pydantic
  2.14.1: packaged schemas are bound to locked 2.13.5, so the runtime correctly used strict
  SDK fallback rather than the fast path. Tests now require cache hits only for matching
  versions and validate equivalent schemas, arguments and results on fallback. All 23
  schema tests pass separately under both versions. The initial failed XML is preserved as
  increment023-source-py3.10-stale-dependencies.xml; the complete corrected matrix passes.
- Distribution acceptance now compares every packaged Python/Java/C/JSON file with the
  canonical sdist, checks metadata versions and the native accelerator, and checks installed
  package bytes against the exact wheel. Ten additional regressions check changed/missing/
  extra source/data, metadata, CRLF drift and missing/duplicate native accelerators. Checkouts
  now pin LF bytes on both platforms. This stricter clean-package gate still requires CI.
- The frozen candidate's CI 39820634142 failed on newer Python patch releases and was not
  published. Reproduction confirmed live ZipInfo UTF-8 bit drift for ASCII names, plus Python
  3.13 versus older-minor docstring indentation in input-schema descriptions. The reader now
  verifies wire filename bytes and permits only the ASCII-equivalent encoding-bit difference;
  all security-relevant flags and non-ASCII mismatches remain strict. Schema records normalize
  descriptions while SDK tools preserve their original live docstrings. Nine new regressions
  increase the final complete suite to 1008; final cross-platform gates must rerun in full.
- Candidate CI 39822842186 passed all four Linux suites and canonical Linux distribution
  acceptance but failed Windows; its artifacts are not release-approved. Windows Python
  3.10.11 predates ZipInfo's overlap-bound slot, and Windows ZIP writers normalized the
  unsafe-backslash test input. Preparation now retains an explicit payload-bound guard on
  older patch releases, validates original wire paths before Windows normalization, and the
  test constructs actual unsafe wire bytes. Five added legacy-reader cases bring the suite
  to 1013 tests. All 44 preparation ZIP tests pass locally; complete gates must rerun.
- CI 39825195709 confirms both ZIP fixes, including Windows Python 3.10, but Windows
  3.11/3.13 exposed a test observer race: a terminated owner process disappeared between
  is_running() and status(). The assertion now handles disappearance throughout observation
  while continuing to reject live processes. Six deterministic observer cases reproduce
  both missing-process races and check live/stopped/zombie outcomes; suite total is 1019.
  Product runtime bytes are unchanged by this test-only fix. Fresh final-runtime receipts
  increment023-dd3a3a9-* verify all three APK ownership/snapshots, all 2,914,002 call sites,
  complete exact/fuzzy references, nine frontier/full-index traversals, real MCP emitted
  sites and both polymorphic formats. Complete cross-platform gates still must pass.

- Source inventory refreshed: 25 tools, two templates, three prompts, 87 parameters;
  no AST omissions at competitor commit 848c711f1d80a1c2577283f1fa5f475ff734aa40.
- The connected investigation regression passes through real stdio and HTTP with Java
  deliberately invalid and JADX/dexlib configuration unset. Manifest dotted-name handoff
  uncovered a real class-search usability gap; both dotted and Dalvik literal names now work.
- Stale client guidance incorrectly requiring JADX for native operations is corrected.
- A checked C path fuses class-data decoding with instruction candidate selection; pure
  Python cursor differentials and malformed-input regressions remain independent.
- The first matched three-round pilot (optimization-streamed-workers4.json) passes input/
  source stability checks. Cold queries beat the pinned competitor in its four scenarios,
  but method/field/fuzzy startup-to-first-result and validated-open RSS still do not.
  Do not present this as comprehensive performance superiority.
- Class ownership has since moved to a bounded-cache SQLite directory with UTF-16 BLOB keys,
  exact duplicate checks, read-only reopen and paged lookups. A one-round pilot drops open
  RSS from roughly 136 to 131 MB, but is diagnostic only, not a frozen comparative receipt.
  The combined logical metadata budget covers JSON-equivalent ownership and the common
  envelope, with a separate bounded physical SQLite page allowance inside the existing disk
  reservation. Empty DEX still works with a 4-KiB output budget; incomplete builds never publish.
- Targeted storage/DEX/container/session/structure regressions pass: 149 tests, with three
  real-fixture cases deliberately outside this focused selection; the combined metadata-budget
  failure/cleanup regression passes separately. This is not the unified release suite.
- The changed checked C selector passes three alternating complete-result rounds against
  the independent JVM oracle: all 24,461 method sites, 332 field sites and 12,495,817
  instructions/diagnostics match. Receipt: optimization-full-site-parity.json. The oracle's
  Java/JADX jars are acceptance-only; the measured product path still does not use them.
- Evidence root: artifacts/release-renumber-20261022. Final Linux/Windows/package gates
  have deliberately not started while feature/performance work is still changing.
- Preparation now consumes ordered decompression results as they arrive, overlapping snapshot
  validation/copy with subsequent extraction. Original archive hashes are checked again before
  publication. Mutation and late CRC failure regressions cannot emit a ready event.
- A portable read-only mapping window validates each canonical stored DEX directory and full
  entry CRC without allocating full DEX Python bytes. Non-ASCII identities use the unchanged
  strict MUTF-8 decoder. The targeted preparation/storage selection passes 58 tests locally.
- The next matched three-round receipt (optimization-pipelined-mapped-workers4.json) passes
  source/input stability. Median cold method/field/fuzzy/concurrent batches are respectively
  1.0232/0.6517/1.0415/1.0330 seconds versus 2.1860/1.9622/2.4092/3.0446. The corresponding
  process-start-to-first-result values are 3.7952/3.5041/3.8377/3.7322 versus
  3.4747/3.3678/3.6845/4.4141. Open-call peak RSS remains about 121 versus 100 MB.
  Thus three first-result deficits and a startup RSS deficit remain; this is not a release gate.
  Timing comparisons across older receipts are not controlled before/after speedup claims.
- Since that receipt, ownership insertion uses bounded 128-row SQLite statements and an
  entire DEX directory shares one C selection call instead of one Python transition per class.
  The single-class and directory entry points use the same strict cursor. Local differential,
  malformed instruction and independent JVM fixture tests pass (76 targeted cases before
  extending the directory corruption regression); fresh large-input accuracy and runtime
  receipts are still required for this newer cursor.
- The newer cursor's matched receipt (optimization-batched-cursor-workers4.json) also passes
  source/input stability. Median cold method/field/fuzzy/concurrent batches are
  0.7312/0.6318/0.8616/0.8785 seconds versus 2.3374/1.8121/2.2111/2.7265. Process-start-to-first
  result is 3.5619/3.2709/3.5900/3.4707 versus 3.6023/3.1734/3.5979/4.0292. Small method/fuzzy
  differences are not robust superiority claims. Field first-result and startup RSS still
  trail; concurrent warm batches are 0.2244 versus 0.2163 seconds in this receipt.
- Three fresh alternating complete-result rounds for this cursor match the independent JVM
  oracle, all method/field sites and instruction/diagnostic counters unchanged. The receipt
  batched-cursor-full-site-parity.json now binds every runtime source and native-extension hash,
  not only native_dex.py. The newer broad focused regression run passes 174 tests, with four
  compiled-APK integrations explicitly skipped for missing fixture environment variables;
  this is not the required zero-skip release gate.
- The same cursor also passes independent full fuzzy and persisted-call-index comparisons:
  28,110 fuzzy sites and 2,914,002 call sites across all 12,495,817 instructions match the
  independently decoded multisets. Receipts: batched-cursor-fuzzy-parity.json and
  batched-cursor-call-index-parity.json. These precede the following host-only refactor;
  final frozen runtime identities must be rechecked rather than silently reused.
- Startup profiling identified repeated SDK output-schema construction. Tool registration now
  loads a source-hash/Pydantic-version/schema-digest checked packaged schema, with safe current-
  contract generation on cache failure. Public SDK Tool/FuncMetadata/MCPServer interfaces
  retain original input parsing, Context injection and strict per-call output validation.
  No protocol implementation or SDK monkeypatch is used. Twelve focused cache/contract tests
  pass; the real MCP/server/integration selection passes 72 tests with all fixture and Rust
  prerequisites configured, without skips. This is not the final unified release suite.
  The new package asset is included in runtime hashes and distribution-presence checks.
- The compiled-registration three-round matched receipt passes source/input stability:
  method/field/fuzzy/concurrent first-result medians are 3.3104/3.0861/3.2351/3.1330 seconds
  versus 3.2639/3.2467/3.7424/4.2965. The method difference and roughly 120 versus 100 MB
  validated-open peak RSS remain deficits. Receipt: optimization-compiled-registration-workers4.json.
- CRC validation now uses short-lived mapping windows with owned bounded chunks. Full-tail,
  callback-failure and handle-cleanup tests pass, but the one-round crc-windows pilot does
  not show an open-RSS improvement. It is not evidence of closing the memory deficit.
- The worker boundary is now being separated from host configuration/CLI imports. Both use
  one path policy and one pagination validator; the native worker decodes the existing request
  without creating host runners/semaphores/caches. Original CLI configuration is constructed
  only when a CLI operation is selected; package/engine version discovery is deferred until
  needed, not skipped. The fresh-process import regression failed before this refactor and
  now passes. The real transport/worker/CLI/configuration regression selection passes 262 tests
  with fixture/Rust prerequisites configured and no skips. A subsequent buffer-only adjustment
  bounds extraction/copy/hash chunks at 256 KiB; its exact-byte and concurrent regressions are
  checked separately before the next matched comparison. No candidate is frozen yet.
- That worker/buffer revision passes 54 exact-byte/concurrency/configuration tests without
  skips and a fresh three-round matched comparison. Method/field/fuzzy/concurrent first-result
  medians are 2.3010/2.3551/2.3510/2.3405 seconds versus 2.4638/2.1682/2.5927/2.8078.
  Cold and warm query medians are lower in all four scenarios, but field first-result and
  open RSS (about 107.5 versus 100.3 MB) still trail. Receipt: optimization-lazy-worker-workers4.json.
  These are within-receipt comparisons, not speedup ratios against earlier differently timed runs.
- Per-worker package-metadata discovery itself adds about 4.3 MB in a fresh-process diagnostic.
  Engine-version resolution now happens afresh in the trusted host request builder; workers
  retain the prepared/current-version comparison, including a package-change rejection test.
  Direct library requests without this internal field retain their original metadata fallback.
  This private field is not a caller-selected MCP parameter. Native preparation now has a
  fresh-process regression forbidding metadata/CLI/host imports through completion. Exact
  logical metadata accounting uses the standard JSON string encoder directly, still tested
  against full JSON serialization for controls, quotes, backslashes and Unicode surrogates.
  Its real transport/preparation/engine-change/workflow selection passes 144 tests without skips.
- The newest three-round matched receipt (optimization-host-bound-worker-workers4.json) passes
  full runtime/input stability checks. Method/field/fuzzy/concurrent first-result medians are
  2.2038/2.0987/2.3456/2.2555 seconds versus 2.4587/2.1735/2.4920/2.8039. Cold query medians
  are 0.5184/0.3614/0.6416/0.5529 versus 1.5677/1.2561/1.5414/1.8963; final warm batches are
  0.0590/0.0625/0.0655/0.1421 versus 0.0786/0.0625/0.0790/0.1608. This is one APK at four
  workers, not evidence of universal superiority; the field warm result ties at report precision.
  Validated-open RSS still trails at roughly 107.5 versus 100.3 MB. Per-phase memory diagnostics
  locate about 30 MB in the isolated preparation worker, including Python allocation arenas;
  host-bound version resolution improves latency but does not close this measured RSS gap.
  Two-worker/additional-input/large-graph frozen comparisons and independent frozen-runtime
  accuracy receipts still remain, before any unified Linux/Windows/distribution release gate.
- Class-directory mapping now returns flat names instead of unused offset/tuple objects for
  ASCII classes; deferred non-ASCII names still use the strict decoder. The targeted native,
  storage and container selection passes 110 tests. Its three-round real-MCP receipt
  (optimization-flat-directory-workers4.json) passes runtime/input stability, but still shows
  roughly 107 versus 100 MB validated-open RSS. This small allocation change does not close
  the measured memory gap. A 12-trial worker-only allocator diagnostic finds Python malloc
  worse and a single glibc arena only about 1.2 MB lower; production allocator defaults are
  unchanged. These diagnostics are not MCP latency evidence.
- A further preparation refactor streams standard 035-040 DEX entries straight from the
  original archive into the immutable stored bundle, combining decompression, SHA-256,
  DEX SHA-1/Adler validation and exact-byte copy. It removes intermediate raw DEX files and
  preparation extraction threads; snapshot API callers retain bounded concurrent extraction.
  Full ZIP CRC, archive before/after identity/hash, combined-byte limits, class validation and
  late-failure publication gates remain. Only 041 uses private seekable normalization input.
  The new no-materialization regression fails before the change and passes afterward.
- Extending the actual 041 investigation regression to container imports found a pre-existing
  oversized read allocation: a tiny file attempted a read buffer sized to the 2-GiB input cap.
  It now reads the preflight file length plus one byte and retains identity/length/integrity
  checks. The original failing evidence is streamed-preparation.xml; the repaired selection
  passes 102 tests, zero skips (streamed-preparation-fixed.xml), including three real archived
  041 normalization/source/string paths. Matched performance remeasurement is still required;
  this is not a frozen candidate or permission to start release publication.
- The serial direct-stream experiment is not a passing performance solution. Its complete
  three-round receipt (optimization-direct-stream-workers4.json) reduces open RSS to roughly
  104-105 MB but method/field/fuzzy first-result medians trail the competitor. One-stream
  prefetch restores most latency, but field first-result and startup RSS still trail
  (optimization-prefetch-stream-workers4.json). Neither receipt justifies release or a claim
  of comprehensive superiority. An owned-block transfer pilot avoids unnecessary chunk copies;
  its single round is diagnostic, not an acceptance result.
- Preparation now overlaps two bounded 64-KiB prefetch streams with validation/copy instead
  of retaining extracted files. Each queue holds at most one block; full chunks transfer by
  ownership, and short reads are handled by the checksum/copy loop. Tests cover simultaneous
  extraction, exact bytes, late producer failure, abandoned/full queues, joined threads and
  041 fallback. Class-directory CRC windows are now 256 KiB, still covering every byte and
  releasing mappings/owned callback data on exceptions. Capability routing no longer builds
  per-resource reader tuples, while every ZIP member is still validated and nested non-code
  members still count toward the full inventory limit. This revision passes 177 targeted
  tests without skips (dual-prefetch-preparation.xml); same-condition MCP measurements remain
  necessary before adopting it as the frozen candidate.
- A peak-memory-map diagnostic attributes most preparation RSS to interpreter pages and
  Python/native allocator state, not a large resident analysis.apk mapping. The mapping is
  about 0.4 MB in the default allocator peak sample. Therefore a speculative remapping
  rewrite is not justified by this evidence. Receipt: prefetch-worker-memory-maps.json;
  this adds sampling overhead and is not latency or Windows evidence.
- The complete dual-prefetch comparison passes runtime/input stability at four workers.
  Method/field/fuzzy/concurrent first-result medians are 2.5609/2.2221/2.3374/2.5068 seconds
  versus 2.6577/2.3222/2.4512/2.5546; the concurrent difference is small, not robust universal
  superiority. Open RSS remains about 105 versus 100 MB. Receipt:
  optimization-dual-prefetch-workers4.json. It precedes the following input-registration change.
- SDK input-model construction can now be deferred using packaged source/SDK/Pydantic-bound
  input schemas. Public SDK metadata delegates argument validation and JSON-string pre-parsing
  to the original SDK model, built on first use; Context injection/call/output conversion remain
  SDK-owned. All 18 schemas and metadata match ordinary SDK registration; stale/malformed/missing
  assets fall back safely. A before-change regression observes 18 eager model constructions and
  now observes zero. Fresh-process diagnostics save about 0.6 MB and 40 ms in registration, not
  the full approximately 10-MB end-to-end host startup increment. Skipping site initialization
  shows no meaningful import-memory benefit and was not adopted.
- The first real stdio/HTTP selection for deferred inputs passes 140 cases and exposes one
  cancellation-test race: a complete tiny index can atomically publish before cancellation,
  so its subsequent reuse is legitimate. No worker/temp cleanup assertion failed. The test
  retains those checks and exact result recovery, and now verifies index.reused=false on first build in
  a separately fresh session rather than assuming cancellation won the publication race.
  Failing evidence remains lazy-input-real-mcp.xml; the repaired real-transport selection and
  fresh matched comparisons must pass before accepting this revision. Package-presence checks
  include the new cache/module/compiler; CI now checks both independently generated schema assets.
- The repaired deferred-input real-transport/preparation selection passes 142 cases without
  skips (lazy-input-real-mcp-fixed.xml), including both connected investigation transports,
  strict contracts, cache fallbacks, original JSON-string argument parsing and archived 041.
  Final accuracy/performance/package/Linux/Windows gates are still pending, not implied by this
  targeted run. The cancellation regression explicitly disables unrelated durable caches.
- Deferred-input runtime comparisons now pass three alternating rounds at both four and two
  workers, with unchanged source/input hashes. Four-worker method/field/fuzzy/concurrent
  first-result medians are 2.3956/2.1568/2.3777/2.2879 seconds versus
  2.3612/2.1871/2.5247/2.9905. Method still trails by 34 ms and field's 30-ms lead is small.
  At two workers they are 2.5329/2.1790/2.3696/2.4615 versus
  3.1399/2.8634/3.1878/3.5417. Cold batches are lower for all four scenarios at both budgets;
  warm batches are lower too, but the two-worker field difference is only 0.5 ms. Open RSS
  still trails at roughly 104.4-104.7 versus 100.2 MB. Receipts:
  optimization-lazy-input-workers4.json and optimization-lazy-input-workers2.json. These
  close the previously missing two-worker measurement, not the memory deficit or all release
  gates. Additional APK/large-graph and fresh independent full-result accuracy remain pending.
- The initial expanded-input pilots are invalid performance comparisons: the harness requested
  a 512-MiB expansion cap with only a 4-GiB session disk budget. The existing conservative 041
  reservation (seven expansion caps plus metadata/index allowances) correctly rejected these
  sessions before querying. Original failed receipts lazy-input-{wechat-pilot,douyin-pilot,
  large-graph}-workers*.json remain intact. The harness now records an explicit independently
  configurable session disk cap; configured reruns must retain the same 4-GiB process-tree RSS
  cap. Product defaults and enforcement are unchanged. The competitor's graph paths independently fail
  at both worker budgets with 'list' object has no attribute 'get_class_name'; failed graph
  times cannot be treated as successful speed baselines.
- Configured expanded-input pilots now genuinely execute both implementations, with a recorded
  8-GiB session disk allowance and unchanged 4-GiB aggregate RSS cap. Both WeChat and Douyin
  method/field/fuzzy/concurrent trials pass source/input stability and per-implementation repeated
  result checks, but these are single-round diagnostics, not frozen superiority receipts.
  WeChat method/field first-result times trail (8.7627/6.2915 versus 5.9672/4.7897 seconds),
  fuzzy is effectively tied and concurrent also trails. Douyin field first-result trails
  (6.9282 versus 6.2479); its other three first-result values lead in this pilot. All eight
  cold query batches are faster, but validation/preparation still dominates some complete paths.
  Open RSS is roughly 109 versus 107 MB on WeChat and 163 versus 134 MB on Douyin, revealing
  a materially larger metadata-heavy startup deficit than the Taobao-only comparison.
  Receipts: lazy-input-{wechat,douyin}-configured-workers4.json. Do not call these gaps closed.
- Configured large-graph trials genuinely complete on our implementation at both budgets:
  177 nodes/178 call sites, explicit output truncation, a 491,614,208-byte call-only index,
  roughly 339 MB peak process RSS, and 73.9088/52.1244-second cold batches at four/two workers.
  Warm batches are 0.1021/0.0739 seconds. The competitor again fails with the same list/method
  exception, at roughly 2.85 GB peak RSS; no successful graph speedup ratio exists. The graph
  trials' overall failed status is preserved rather than relabeled as passed. Index bytes are
  separate from RSS: the benchmark's /tmp is tmpfs, so those bytes consume real system RAM.
  Receipts: lazy-input-large-graph-configured-workers{4,2}.json. These one-round results also
  show why a bounded frontier scan, instead of building a whole-APK call index for a shallow
  graph, is worth investigating before freezing; accuracy must match the independent full index.
- Remaining preparation work must profile complete-archive hashing/decompression and large ZIP
  inventory allocation, not extrapolate small-APK measurements. The installed standard ZIP
  parser reads the whole central directory into bytes/BytesIO and retains every ZipInfo; the
  resource-heavy APK amplifies this path. A bounded ZIP metadata/reader reconstruction is
  explicitly within the authorized scope if a measured prototype confirms this allocation
  bottleneck. Preserve full unsafe-name/duplicate/CRC/ZIP64/overlap checks, source provenance,
  041 behavior and shared budget accounting; do not silently narrow container support.
- Framework reconstruction is explicitly authorized when a measured bottleneck cannot be
  removed locally. The latest Douyin worker memory map localizes the peak to snapshotting:
  about 87.5 MB versus 33.6 MB in class-directory construction, with roughly 49.2 MB anonymous
  pages and 25.0 MB heap at the peak. This supports investigating ZIP inventory allocation,
  not attributing the peak to the final DEX mapping. Direct preparation profiles are 2.17 s
  on WeChat and 5.04 s on Douyin under cProfile; these are diagnostics, not MCP timing receipts.
  Evidence: lazy-input-{wechat,douyin}-preparation-profile.json and
  lazy-input-douyin-memory-maps.json. No ZIP reader replacement is accepted yet.
- A bounded native frontier graph is now implemented as a candidate instead of automatically
  materializing every APK call site. It shares BFS/output-budget semantics with the full-index
  path; each scan validates all methods/instructions while only selected callers/incoming hits
  cross into Python. Dense frontiers exceeding their bounded record budget fall back to the
  existing atomic disk-bounded index, never an incomplete graph. Existing indexes remain usable;
  native frontier results do not falsely advertise index creation/reuse. Fixture full-index
  differential checks, real transports and large-input accuracy/performance reruns are required
  before accepting this reconstruction or closing the graph gap.
- The batched frontier revision passes 323 targeted cases without skips, including exact
  full/call-only index parity across directions/depths/budgets, cycles, external/no-code roots,
  dynamic sites, Python fallback, adaptive dense-batch splitting, atomic fallback/reuse,
  corruption in unreachable code and both real MCP investigation/graph transports.
  Receipt: frontier-graph-batched-zero-skips.xml. This is not the unified release suite.
- A fresh Taobao full call index and the frontier backend match every graph field in all nine
  direction/depth combinations (incoming/outgoing/both; depths 1/3/5), with unchanged input and
  runtime hashes. The both-direction depth-three result remains exactly 177 nodes/178 sites
  and explicitly output-byte-truncated. Receipt: frontier-large-exact-parity.json. Its direct
  worker timings are diagnostics only; matched real-process timing/RSS reruns are separate.
- Matched real-stdio frontier trials now complete three alternating rounds at each worker
  budget with unchanged input/runtime hashes. Two/four-worker median cold graphs are
  5.6871/5.5505 seconds, complete process-start-to-first-result is 7.8104/7.9555 seconds,
  warm graphs are about 0.094/0.091 seconds and peak aggregate RSS is about 139 MiB.
  Every result preserves 177 nodes/178 sites and explicit output-byte truncation, without
  creating a calls index. The prior index path's 52-74-second receipts are historical,
  not a freshly controlled before/after ratio. The competitor fails all six graph trials
  with its same list/method exception; overall report status remains failed and no valid
  graph speedup ratio against the competitor exists. Receipts:
  frontier-large-graph-workers{2,4}.json. These precede the following optional-cache guard.
- Explicit durable-cache opt-in retains the original calls-index build/restore behavior
  rather than silently ignoring an available cross-session cache. The default uncached
  frontier path is unchanged. The resulting selection passes 336 tests without skips,
  including stored/restored graph equality, both transports, full-index/page-cache recovery
  and cancellation publication boundaries (frontier-graph-durable-zero-skips.xml).
  Final frozen runtime accuracy/performance and Windows/package gates remain mandatory;
  none of the development receipts authorize release or close startup/ZIP-memory deficits.
- The resumed implementation adds a compact preparation-only ZIP directory. All 47,676
  Douyin entry names remain validated/inventoried, but only 55 code/container ZipInfos are
  retained. Three fresh-process directory diagnostics match inventory/selected-metadata
  hashes, reducing median directory-process peak RSS from 62.38 to 30.95 MB; directory
  latency is roughly unchanged (0.256 versus 0.262 seconds). Source archive hashes,
  selected member CRC, DEX checksums, nested collision/count budgets and normal resource
  browsing are unchanged. This is not yet a source-frozen startup or Windows/package gate.
- Compact reader compatibility passes 39 cases on each Linux Python 3.10-3.13, covering
  ZIP64 security backports, exact stdlib metadata/member bytes, concatenation/data descriptors,
  malformed extras, omitted-resource safety/duplicates/special files and overlap limits.
  The preparation/container/directory/real stdio/HTTP selection passes 139 cases without
  skips (compact-zip-transports-zero-skips.xml). No core query needs Java/JADX.
- The initial compact-ZIP real-stdio pilot finishes three alternating rounds for all four
  non-graph scenarios, with stable input/runtime hashes and open RSS about 132 versus
  134 MB. A harness audit finds full report I/O inside old ready/batch measurements;
  preserve compact-zip-douyin-workers4.json, but do not use those timings as clean latency
  authority. Timing version 2 records direct response-arrival boundaries and moves report
  persistence outside measured calls, with four regression cases. Fresh matched reruns,
  remaining first-result gaps and all final acceptance/release work are still required.
- The corrected timing-version-2 Douyin/four-worker comparison passes all 24 real-stdio
  trials (three alternating rounds, four scenarios, two implementations), with unchanged
  runtime/input hashes. Median full first results, ours/competitor: method 7.3610/6.5940 s,
  field 6.1838/4.7044 s, fuzzy 6.7110/6.3583 s, concurrent 6.8529/7.3353 s. All cold query
  batches lead, but three complete startup paths still trail. Open RSS is roughly
  132.2/133.7-133.8 MB. Receipt: compact-zip-douyin-timing-v2-workers4.json; no blanket
  superiority or release approval follows. Earlier version-1 graph/other aggregate
  ready/batch receipts also require the report-I/O caveat, not silent numeric relabeling.
- Next priority is measured snapshot/hash and class-directory publication latency, not
  dropping checks or returning early ready. Any pipelining/reconstruction must preserve
  complete input/DEX/member integrity, duplicate detection, failure/cancellation cleanup,
  bounded resource accounting and Windows compatibility before adoption. Workflow closure,
  final two/four-worker multi-input/graph/accuracy receipts and release gates remain open.
- The final combined compact-ZIP, timing-harness, container/archive/directory and selected
  real-transport regression passes 143 tests without skips (54 unrelated integration cases
  deselected), receipt compact-zip-and-timing-zero-skips.xml. Ruff checks/formatting,
  generated input/output schema checks and git diff whitespace checks pass. HEAD/main,
  tags and releases are unchanged; no frozen candidate, CI branch push or publication occurs.
- The maintainer has now replaced the actual component objective. get_goal confirms active
  status and the full six-part objective, rather than the previous blocked performance-only
  summary. No goal-status workaround or false completion was used.
- A new preparation pipeline scans each closed/flushed stored DEX member, releases all
  mappings before file growth, and overlaps bounded ownership insertion with the next
  snapshot. SQLite opens/writes/closes on one owner thread; the current candidate joins the
  previous insertion before allocating the next class directory. A private pending database
  is only renamed after every member and the outer source's final hash validate. Errors join
  the writer and cannot emit readiness. Pure Python and mapped C paths retain exact names.
- The first three-round pipeline report passes all 24 trials with stable input/runtime:
  pipelined-directory-douyin-timing-v2-workers4.json. Its method/field/fuzzy/concurrent full
  first-result medians are 5.8402/6.0016/6.7023/6.4075 s versus
  6.5664/5.3279/7.2904/9.3965 s. Startup RSS regresses to about 138 versus 134 MB, so this
  is not a completed startup-memory fix. This predates the one-directory handoff revision.
- The bounded revision also moves identical C0/backslash name validation into a compiled
  character-class search, preserving path-segment/drive/Unicode rules. Its 257-case targeted
  selection passes with zero skips, including real stdio/HTTP investigation/fuzzy/graph,
  041 normalization, duplicate/integrity/metadata failures and session cleanup. Receipt:
  pipelined-directory-and-path-zero-skips.xml; 52 other integration cases were deselected.
- Corrected timing-version-2 measurements now sample temporary regular-file logical and
  allocated bytes outside response callbacks; both implementations share a sampled external
  temporary-byte cap. The nine harness cases cover persistence boundaries, both implementations'
  simulated command flows, concurrent replies, symlink exclusion and resource-cap failure.
  Receipt: temporary-usage-harness-v3.xml. This is a stdio harness; mocked tool flows are
  not an HTTP performance measurement. File peaks are sampled lower bounds, not exact maxima.
- The updated Douyin/four-worker three-round receipt passes 24 trials with stable input/runtime
  and no storage sampling errors: bounded-directory-douyin-timing-v2-workers4.json. Full first
  results are 5.7023/5.6383/5.8082/6.0512 s versus 5.8173/4.5365/6.1478/7.1816 s. Method's
  small margin is not robust superiority; field first-result still trails by 1.1018 s and open
  RSS is about 137.6-138.1 versus 133.8-134.0 MB. Field warm batches are about 0.037/0.038 s.
- Crucially, /tmp is tmpfs on this host (findmnt verified). Our sampled temporary peak is
  about 500.36 MB logical/500.37 MB allocated, versus no competitor trial files. The retained
  Douyin snapshot/database are 457.06/43.27 MB, before small envelopes. A roughly 79-MB warm
  product process is not a 79-MB total memory footprint. Retained RAM-backed storage is an
  open resource gap; do not hide it, move it outside measured roots, or claim total-memory
  victory using process RSS alone. Any storage redesign must preserve immutable inputs,
  exact results, bounded accounting, cleanup and same-condition filesystem comparisons.
- A new full ownership verifier decodes original APK DEX classes with the pure Python
  cursor, compares every ordered identity/owner and common field, and hashes every snapshot
  DEX against its original bytes. All three large inputs pass with unchanged source/runtime:
  Douyin 53 DEX/551,538 classes, WeChat 16/233,555, Taobao 12/99,712. Receipts:
  pipelined-directory-{douyin,wechat,taobao}-full-ownership.json. Fixture damage tests reject
  missing owners, incorrect ownership and snapshot corruption; these are accuracy receipts,
  not latency/memory comparisons or final call-site/graph completeness gates.
- The live SQLite-writer timeout/cancellation tests now exercise the actual worker bootstrap,
  process supervision and owner thread. Both observe a pending database before termination,
  require session-directory deletion and a stopped worker, then successfully reopen fresh input.
  The first injection incorrectly used python -c with a module-only bootstrap; that failing
  harness receipt was retained and the fixture now uses a real module, not a production bypass.
- Class-directory format 1 uses internal CESU-8 byte keys instead of fixed UTF-16BE keys.
  Byte order still exactly follows UTF-16 units, including supplementary characters and lone
  surrogates. Old format-0 directories remain read-only compatible; unknown versions fail closed.
  Deterministic Unicode ordering/roundtrip/prefix cases and the full original-input oracle pass.
  Douyin retains the same 551,538 exact class/owner pairs and identical ordered-owner digest;
  owners.sqlite shrinks from 43,270,144 to 27,541,504 bytes (36.35%). The immutable DEX bytes
  remain identical at 457,060,748 bytes. Receipt: compact-keys-douyin-full-ownership.json.
- The matched three-round/four-worker field receipt passes all six trials with unchanged
  product runtime/input: compact-keys-douyin-field-v2-workers4-with-competitor.json. Median
  cold calls are 1.0310 versus 2.7145 seconds; complete first results are 4.7377 versus 3.9161.
  The remaining first-result gap is 0.8216 seconds in this receipt, not a closed gate. Sampled
  temporary logical/allocated peaks are 484,628,602/484,642,816 bytes versus zero competitor
  files; the approximately 15.73-MB real storage saving does not solve retained-snapshot RAM.
  Open process-tree RSS remains roughly 137-139 versus 134 MB. These historical-before/new-after
  receipts are not a randomized optimization speedup ratio. The earlier same-name report
  without '-with-competitor' failed because asc_mcp was absent from that interpreter and is
  invalid as a competitor comparison; it remains preserved rather than overwritten.
- The benchmark now fails before trials if asc_mcp is absent or its installed Python source
  tree differs from the pinned clean checkout, and records the interpreter path, actual package
  origin and every competitor Python-source hash. It checks the installed/source match again
  after trials. Twenty harness regressions pass, including missing/changed/extra installed files
  and comparison of complete cold/warm structured responses (not just result item counts).
  Receipt: installed-competitor-identity-harness.xml.
- The compact-directory/live-writer targeted selection passes 281 cases, zero skips, with
  52 other integration cases deliberately deselected: compact-directory-targeted-zero-skips.xml.
  Source tests on Linux Python 3.10, 3.11, 3.12 and 3.13 each pass 168 cases with zero skips:
  compact-directory-py3.{10,11,12,13}.xml. They use the existing shared source extension and
  are not fresh canonical-wheel/Windows acceptance. The later five package-identity harness
  cases have their separate 20-case receipt above; no final version freeze is asserted.
- The final compact-key selection, including all 20 harness cases, passes 286 tests with
  zero skips and 52 deselections: compact-directory-final-targeted-zero-skips.xml.
- The new four-worker Taobao graph/concurrent receipt checks actual installed competitor
  source identity before/after and keeps the full combined status failed:
  compact-keys-taobao-graph-concurrent-v2-workers4.json. All six concurrent trials pass;
  median cold-batch/full-first times are 0.5062/2.3574 seconds versus 1.7488/2.7251.
  Product temporary data peaks at 118.88 MB, separately from sampled process RSS.
  Our three graphs return identical complete structured cold/warm responses (177 nodes,
  178 sites, explicit output_bytes truncation). Competitor graphs fail three times with
  list/get_class_name in the pinned cached graph builder, just as at two workers. There
  is no completed competitor graph timing and therefore no valid graph speedup ratio.
- A further lifetime regression shows APK/AAR preparation retains all validated resource
  names while DEX/class buffers grow. Once capability selection, every safety/duplicate/
  provenance collision and inventory budget check have finished, preparation now clears
  only that no-longer-used root name inventory. Actual selected ZipInfos/readers, resource
  operations' ordinary ZipFile path, full CRC and final original-input identity/hash remain.
  Both regressions fail before this change (released-inventory-before.xml); 98 selected
  container/preparation/ZIP cases pass afterward without skips
  (released-inventory-after-zero-skips.xml). Matched measurement is still required; this
  edit does not by itself prove a startup memory or latency win.
- After inventory lifetime shortening, all three full original-input ownership/snapshot
  verifiers pass with unchanged runtime/input and the same ordered-owner hashes:
  released-inventory-{douyin,wechat,taobao}-full-ownership.json. New owner databases are
  27,541,504/11,255,808/5,955,584 bytes respectively; immutable DEX snapshots remain exact.
- The latest matched field report passes all six trials, including installed competitor
  source checks: released-inventory-douyin-field-v2-workers4.json. Median cold calls are
  1.4206/3.9502 seconds; full first results 7.2970/5.8193 seconds, still a 1.4777-second gap.
  Open RSS is approximately 135.9-136.5/133.8-133.9 MB and retained files remain 484.63 MB.
  Both implementations slow substantially versus the prior receipt. Host load after the run
  was 6.88/5.77/4.01, not evidence establishing the cause. Do not select the earlier best
  first-result gap or turn separate historical runs into a controlled optimization ratio.
  No unrelated process or host performance setting was changed to improve the comparison.
- The current released-inventory selection passes 288 cases, zero skips, with 52 integration
  deselections: released-inventory-targeted-zero-skips.xml. Linux source tests on Python
  3.10/3.11/3.12/3.13 each pass 214 cases without skips, including all container routing,
  preparation cancellation, compact Unicode keys and the 20 benchmark harness cases:
  released-inventory-py3.{10,11,12,13}.xml. Input/output schema checks and Ruff pass. These
  are still development-source receipts, not the deferred Windows/canonical-package gate.
- The retained-snapshot bottleneck is structural: original selected DEX compressed payloads
  occupy 169,239,193 bytes for Douyin, 68,875,841 for WeChat and 43,386,976 for Taobao, while
  current stored raw DEX payloads occupy 457,055,340/173,181,908/112,915,728 bytes. These
  standard ZipInfo inventory sums are only a storage-feasibility diagnostic, excluding ZIP
  framing, ownership metadata, normalization and query decompression costs. No compressed
  snapshot implementation or memory/performance benefit has been accepted from those sums.
  Any redesign must measure those costs and preserve immutable snapshots/integrity/budgets;
  moving storage outside accounting or dropping input checks is not an accepted solution.
- The checked native directory now validates ASCII identities/duplicates in C and hands only
  deferred Unicode indices to Python. No full ASCII row reconstruction or second set walk is
  needed. Strict MUTF8, canonical duplicates, full mapped CRC and the older/pure-Python paths
  remain covered. The focused native/graph/structure/index selection passes 377 cases without
  skips: checked-directory-native-zero-skips.xml. After this change, the complete original-input
  owner/snapshot oracles pass on all three large APKs with the same exact ordered-owner hashes:
  checked-directory-{douyin,wechat,taobao}-full-ownership.json. The real stdio/HTTP investigation,
  fuzzy/graph, preparation/container and benchmark selection passes 320 cases, zero skips,
  52 deliberate integration deselections: checked-directory-targeted-zero-skips.xml.
- Competitor source shows nested pools: runtime.py starts the outer request pool, server.py
  propagates its worker_count, and artifact_handler.py:_for_each_findrefs creates another pool.
  Old same-worker reports therefore match configuration, not an aggregate CPU ceiling. The
  common benchmark_cpu_wrapper.py now configures and reads back exact inherited CPU affinity
  before either product imports, including its overhead in both timings/RSS. The monitor checks
  every sampled owned descendant after transport initialization and fails/stops the trial for
  empty, escaped or unreadable masks. Exited-process races do not count as successful samples.
  Unsupported affinity/budgets fail closed rather than changing the budget. Thirty-nine wrapper/
  harness cases pass without skips: cpu-budget-monitor-zero-skips.xml. Do not silently upgrade
  old receipts to cpu_budget_version=1 or compare different budget methods as a causal speedup.
- Fresh timing-version-2/CPU-budget-version-1 Douyin field receipts alternate three rounds at
  each two/four-worker budget: checked-directory-douyin-affinity{2,4}-field.json. All twelve
  trials pass with unchanged input/product/installed competitor source and complete structured
  cold/warm equality within each implementation. At two logical CPUs, median cold calls are
  1.7970/10.7506 seconds (ours/competitor), and complete first results 10.0072/13.1193. At four,
  they are 1.4025/4.8802 and 7.2794/6.7757 respectively. Thus this workload wins first use at
  two CPUs but still trails by 0.5037 seconds at four, not a universal startup victory. Sampled
  process counts reach 2/5 and 2/7, while every observed mask stays inside its CPU budget.
  Open RSS stays close and retained product files still occupy 484,628,602 bytes on tmpfs versus
  zero competitor trial files. No total-system-memory win or closed storage requirement follows.
- A further candidate replaces per-class clearing of the selector's 16-KiB duplicate bitmap
  with a bounded per-directory generation table (at most 524,292 bytes), freed on every exit.
  The single-class API keeps the independent bitmap path. Per-kind/per-group duplicates,
  highest 16-bit IDs, repeated classes/calls and error paths have twenty additional regressions;
  the native/directory/graph/structure/index selection now passes 397 cases, zero skips:
  duplicate-stamps-native-zero-skips.xml. The first diagnostic profile reports C selection
  0.660/0.533 seconds before/after, but separate profile runs are not a controlled MCP speedup
  ratio. New real-MCP measurements, original-input accuracy and cross-version source checks must
  identify this changed C runtime rather than reuse the preceding checked-directory receipts.
- The duplicate-stamp candidate's latest real-stdio four-CPU field receipt passes six trials
  with unchanged input/product/installed competitor sources:
  duplicate-stamps-douyin-affinity4-field.json. Median cold calls are 1.2955/5.1013 seconds,
  opens 5.1692/0.8466, and complete first results 7.7164/7.0332 (ours/competitor). The current
  first-result gap is 0.6832 seconds; the earlier 0.5037 must not be selected as a current
  best-case claim. Changes in preparation timing are not evidence of a selector regression
  or a controlled before/after speedup. Startup/storage and multi-input budget gates remain open.
- Full direct-backend accuracy is refreshed against the frozen v0.4.0 JVM oracle:
  duplicate-stamps-full-reference-parity.json. All twelve alternating comparisons pass across
  three rounds for both operations: 24,461 exact method sites, 332 field sites, all 12,495,817
  instruction counts and full diagnostics/digests, with unchanged input/oracle/runtime hashes.
  Java/JADX jars are acceptance-only here, not a core runtime dependency. The three original-APK
  owner/snapshot checks also pass again on this C runtime, with the same complete digests:
  duplicate-stamps-{douyin,wechat,taobao}-full-ownership.json.
- Linux Python 3.10/3.11/3.12/3.13 source checks each pass 331 cases, zero skips, including
  native differential cursor, duplicate stamps and CPU-monitor failures:
  duplicate-stamps-py3.{10,11,12,13}.xml. The real stdio/HTTP/preparation/container/benchmark
  selection passes 320 cases, zero skips and 52 deliberately deselected integration cases:
  duplicate-stamps-targeted-zero-skips.xml. These existing-interpreter/shared-ABI source
  receipts are not new canonical sdist/native-wheel or Windows acceptance. The full requested
  goal stays active; no candidate commit, main merge, tag deletion or publication has occurred.
- WeChat adds independent multi-input CPU-budget coverage at both two/four logical CPUs:
  duplicate-stamps-wechat-affinity{2,4}-concurrent-fuzzy.json. All 24 real-stdio trials pass
  unchanged input/product/installed competitor hashes and complete cold/warm structured
  equality within each implementation. Median concurrent cold/first-result times at two CPUs
  are 1.0498/5.0411 seconds versus 7.6354/9.0528; at four, 0.7926/4.1341 versus 4.5157/6.0853.
  Fuzzy first results are 4.8450/6.9615 at two CPUs and 4.3395/4.5608 at four. The latter
  0.2213-second lead is a small three-round observation, not a universal win. Actual concurrent
  process counts reach 3/8 and 3/12 while all observed affinities stay inside equal CPU masks.
  Our 184.45-MB retained tmpfs files are still separately reported, not erased by lower RSS.
  Competitor first concurrent repeats remain slow; its per-process LRU/unspecialized pool is a
  source-backed candidate explanation, not a traced worker-routing proof. Full results and
  repeat timings are retained rather than selecting only the faster second repeats.
- Taobao's completed two/four-CPU graph/concurrency reports preserve all failures:
  duplicate-stamps-taobao-affinity{2,4}-graph-concurrent.json. Each has three passing product
  graphs, three competitor graph failures (`list` has no `get_class_name`) and six passing
  concurrent trials; both reports remain failed overall. Concurrent first-result medians
  are 3.5750/7.6370 seconds at two CPUs and 3.1922/4.7943 at four (ours/competitor).
  Product graphs return 177 nodes/178 sites with explicit output-byte truncation, so neither
  competitor failures nor successful bounded responses prove unlimited graph completeness.
- A fresh full-index traversal comparison passes all nine direction/depth combinations:
  duplicate-stamps-frontier-full-index-parity.json. This receipt precedes the next graph-only
  filter change. Its 491.61-MB/82.78-second index build is accuracy-oracle work, not hidden
  preprocessing in normal frontier latency. Independent decoder/site checks remain separate.
- Graph profiling disproves the initial repeated-type-table hypothesis as the main hotspot.
  Incoming traversal was emitting irrelevant operands into Python after the checked C pass.
  It now uses the existing exact-frontier scanner for incoming callers and the full scanner
  only for outgoing frontier methods. Every instruction and selected caller descriptor is
  still validated; no early cap shortcut or dropped metadata check is used. The current
  native/graph/structure/real-script selection passes 374 tests, zero skips:
  frontier-filter-native-transport-zero-skips.xml. Six regressions failed before the change.
- The graph script is updated from obsolete always-full-index assumptions to actual artifact
  preparation/frontiers and bounded host-cache repeats. It binds input/runtime/verifier hashes,
  includes preparation in end-to-end time, requires temporary cleanup and preserves canonical
  DEX-to-original-entry mapping, including polymorphic call-site prototypes in the independent
  decoder check. The first artifact pilot exposed an undersized reservation and remains failed
  as frontier-filter-real-mcp-graphs.json; corrected reservations pass 128/512/2048-MiB script
  regressions. The real APK pilot, frontier-filter-real-mcp-graphs-fixed.json, passes stdio
  with Java deliberately invalid and independently verifies all 260 emitted unique call sites.
  This is not full-corpus graph completeness or a matched competitor performance comparison.
- A six-trial, alternating four-CPU product-revision comparison passes complete cross-revision
  graph equality and unchanged input/source identities: frontier-filter-matched-revision-affinity4.json.
  The before snapshot matches every byte of the preceding measured 56-file runtime; only the
  incoming graph filter differs. Cold medians are 8.7214/7.2001 seconds before/after, but one
  pair regresses and first-result medians are close (11.8991/11.5809), with two individual
  first-result regressions. Report this noisy observation, not a robust startup win or a
  competitor speedup. Peak process RSS is essentially unchanged. Startup/retained-storage,
  frozen independent accuracy, full workflow and final OS/package/release gates stay open.
