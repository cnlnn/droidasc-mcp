# 0.2.x incremental completion goal

## Current implementation plan, 2026-10-27

Status: B1/B2 accepted with measured residuals; B3 baseline and scoped reuse
assessment complete. On 2026-10-29 the maintainer requested small, independently
accepted goals, highest benefit first. G1/G2 and the B3 batch gates are complete;
G3 is active with fresh preparation profiling;
the previously paused goal-controller status remains separate from this scoped work.
This section is the
single current execution ledger and ordered backlog. Older sections below retain
historical decisions and receipts; their candidate/release statuses do not override
this section. The cross-platform/package requirements and invariants below still apply.
The maintainer requested continuous goal-mode execution on 2026-10-27: finish each
batch's gates and automatically advance to the next without repeated confirmation.
Publication is separate; this instruction does not approve another release.

The maintainer subsequently challenged independent reimplementation when the comparator
already has working code. Subsequent work is reuse-first: identify the exact upstream
function, port it directly where possible, and adapt only its interface/lifetime/bounds
or demonstrated defects. Record source revision and notices for copied/adapted code.
The checked comparator and this repository both declare Apache-2.0; the comparator
contains `LICENSE` and no separate `NOTICE` in the pinned tree. Preserve upstream
attribution and mark modifications when incorporating code; no comparator code has yet
been incorporated by the cache-read fix.

B2's first reuse target is `AscHandler.findrefs_structured` in
`artifacts/aimard-asc-mcp/asc_mcp/analysis/asc_handler.py`: group by caller, accumulate
targets and retain every evidence entry. `ReferenceHit`/`ReferencePage` in `models.py`
provide the existing grouped shape. Port this behavior into the current session adapter
before considering a new identity-table representation. Keep original row identities,
ordering and duplicate evidence reconstructible, splitting a large caller across bounded
pages as necessary. The comparator's demonstrated instruction-location defect is confined
to that locator; it is not a reason to reject reuse of its grouping or workflow logic.

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
| B1 | Operand-only type scan, selected-set reuse, string cache and accurate API mapping | P0 | accepted at b64f85c; cold type/startup residuals retained for B4 |
| B2 | Compact reference output and resumable full-result collection | B1 accepted | accepted at aca6b27; opt-in large-member benefit, not universal speedup |
| B3 | Unified artifact workflow and smaller tool contracts | B2 accepted | accepted at 631fcbc with schema/latency residuals; default stays legacy |
| B4 | Measured preparation reuse/cost reduction | B3 accepted | G3 active; fresh cold-cost attribution |
| B5 | Explicit multi-module AAB analysis | B4 accepted or closed with measured residuals | deferred |
| B6 | Native DEX 041 logical views and query coverage | B5 accepted | deferred |

Execution order changes need an evidence-backed entry here, not a silent expansion of B1.
A failed optimization does not block unrelated later capabilities indefinitely: retain its
failure and residual gap, then record the revised order. Never call the overall gap closed
because a batch or patch release passed.

### Small goals, highest benefit first, 2026-10-29

| Goal | Independently usable result | Acceptance boundary | State |
| --- | --- | --- | --- |
| G1 (B3.1) | One immutable artifact handle for metadata and lazy code queries | Metadata does not prepare DEX; first code query prepares once; real stdio/HTTP, original hash, lifecycle/quotas and legacy compatibility; frozen real-model inventory/navigation/resource tasks | locally accepted; 1807 source tests, four successful model workflows and clean sdist/wheel checks |
| G2 (B3.2) | Focused DEX tools and final artifact profile | All 24 DEX operations reachable with smaller focused contracts; full 3-round model comparison and batch distribution gates | accepted at 631fcbc; 12/12 model tasks, 25/25 CI jobs; aggregate schema/latency residuals |
| G3 (B4) | Remove one measured dominant cold-preparation cost | Matched cold/first-use/repeat measurements with correctness and mutation/cleanup checks; retain unsuccessful candidates | active; three-input preparation/first-query profiles and low-overhead phase attribution |
| G4 (B5) | Explicit multi/all-module AAB selection | Cross-module inventory/references, duplicate identities and manifest/resource routing with module provenance | pending |
| G5 (B6.1) | Validated DEX 041 physical/logical views without Java for inventory/instructions | Shared-data and malformed fixtures, independent original-byte oracle and every logical header | pending |
| G6 (B6.2) | DEX 041 source handoff and combined acceptance | Decompiler/reference coverage, compatibility, full Linux/Windows/package gates | pending |

G1 has the broadest immediate reach across common tasks and reuses the upstream
session/handle workflow already ported. Ship no changed default yet: opt-in
`DROIDASC_MCP_TOOL_PROFILE=artifact_preview` advertises seven handle tools and the
existing status/DEX-query/diff/secret bridges. It is deliberately not the final
`artifact` surface. All old tools remain callable and `legacy` still advertises the
same 18 names. G2 replaces the giant DEX selector in the final advertised profile;
it is not required to use or separately evaluate G1. Small-goal local acceptance
does not waive the batch's cross-platform/package gates or approve publication.

Execution adjustment following the maintainer's reuse-first correction: freeze the B1
cache-read candidate and its evidence, then implement the upstream grouping adaptation
while final B1 parity/package checks remain explicitly open against that frozen candidate.
This avoids holding an independent output improvement behind another full timing matrix.
B1 is not marked accepted by this scheduling change; its missing gates remain required
before combined acceptance, and B3 still depends on accepted B1/B2 behavior. Do not modify
the frozen B1 runtime or relabel its timings as measurements of later B2 code.

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

G2 implementation started on 2026-10-29 after the maintainer resumed the goal.
Adapt the pinned upstream `asc_mcp/server.py` handle-oriented DEX wrappers in a
dedicated `focused_tools.py`; preserve existing session ownership, native query
execution and cached-schema registration. Standard upstream names and discovery
arguments are retained where semantics agree. Exact method/field references keep
our full identities and overload errors; fuzzy/partial selectors move to the
focused `apk_search_references` adapter. String literals are passed unchanged,
not escaped for the upstream regex locator. Every legacy operation, including
bundle info/manifest, legacy regex and broad type/index scopes, gets a focused route.
The final opt-in `artifact` advertisement hides the giant selector without removing
its registration; `legacy` and `artifact_preview` advertisements stay unchanged.
No default/profile switch or release is accepted by this implementation entry.
Fresh evidence: `artifacts/competitor-gap-b3-g2-20261029/`; the two new contract tests
first fail because the profile is absent (`contracts-red.xml`).

| Item | Current record |
| --- | --- |
| Current task | G2/B3 accepted with residuals; G3 cold-preparation profiling active |
| Next action | Attribute read/hash/inflate/directory/worker costs, select one bounded reuse/removal candidate, then run matched correctness/first-use/repeat gates |
| Product changes | Opt-in artifact advertises 24 focused DEX adapters covering all 24 operations, plus the seven handle metadata tools and status/diff/secret bridges; legacy and artifact_preview advertisements remain unchanged; eight narrower typed output contracts retain extra diagnostics |
| Planning checks | Corrected G2 source: 1816 passed, zero skips; Linux/Windows Python 3.10-3.13 source and canonical-sdist/exact-wheel gates all pass; real native-only model matrix 12/12 |
| Open dependencies | B3 aggregate schema/observed model-latency residuals; B4 cold costs; B5 module selection/routing beyond upstream all-entry scanning; B6 native physical-view integration and shared-data correctness |
| Fixed architecture decisions | Backward-compatible broad type scope; explicit operand scope; bounded existing selected-set cache; original-input provenance; no resident full-APK pool |
| Release state | No new release/version selected; development completion and publication approval remain distinct |

G2 contract-size investigation: initially reusing `DexResult` on every wrapper
inflated the full canonical tool surface to 77131 o200k_base tokens. Eight focused
output types reduce it to 47018 without dropping extra diagnostics or changing the
legacy result type. The final surface has 34 advertised tools and at most 13 input
parameters per tool, versus legacy's 18 and 28. Input-contract tokens are 7414 versus
6762; full-surface tokens remain above legacy's 32795. Thus this is narrower
per-operation selection, not an aggregate schema-size improvement. Keep that
residual visible in the real-model call/error/time comparison and leave the default
unchanged. These counts are canonical surface measurements, not billed model usage.
The G2 model harness changes only profile selection and explicit native-only backend
isolation; frozen task text, model/provider settings and the original baseline stay
unchanged. Model trials run serially after correctness work, with every failed
attempt retained. Development-branch CI builds do not publish a version/tag/release.

G2 first frozen candidate `5b5d220f09ee3e4935c394e81c82475ad8746175`:
1814 source tests pass; clean sdist and installed wheel each pass all 1814 tests,
with canonical-source and installed-byte identity verified. The frozen model matrix
passes all 12 cells (three rounds per unchanged task), with zero product errors.
Median product calls drop from 6/6/7/5 to 4/4/6/4 for F-Droid inventory, Douyin
inventory, manifest-to-code and resources respectively. Observed model times are
slower, not a speedup claim. Raw responses/oracles/receipts and the offline judge
are bound in `model-review.json`; every trial uses explicit native-only isolation.

CI `40734273495` fails the eight Windows source/distribution cells (the Linux
cells pass). Windows short-form temp roots are copied into private worker requests
without canonicalization, while input validation resolves the same paths to long
form; this incorrectly rejects the private snapshot. Resolve the private parent
at the two request construction sites, retaining the single-directory allowlist
and original content-hash checks. The same defect is reproduced on Linux using
an equivalent noncanonical parent (`private-root-red.xml`). A separate new ZIP
fixture was normalized by the Windows writer; assign both on-wire names directly
and assert their bytes, following the existing archive tests. The first green
attempt retains an assertion error about the direct archive runner's legacy
`apk_sha256` field; no wire-field rename is part of this fix.
G2 is not accepted until the corrected candidate's gates pass. Preserve the first
candidate and model matrix separately rather than relabeling their runtime hashes.

G2 final acceptance, corrected commit `631fcbcdf9438e22fab676007e6bdb877c96c14b`:
CI [40739854382](https://github.com/cnlnn/droidasc-mcp/actions/runs/40739854382)
passes all 25 jobs. Every Linux/Windows Python 3.10-3.13 source cell passes 1816
tests with no errors/failures/skips; all eight distribution cells independently pass
1816 tests from the same canonical sdist and another 1816 from the exact native wheel.
The downloaded four platform/Python package pairs match the accepted runtime sources;
eight signing receipts, real transports, Rust and stability gates pass. Failed network
downloads/log fetches and freeze-helper assertion corrections remain separately retained.

`g2-acceptance.json` binds source/tests/harnesses, downloaded packages, JUnit/signing
receipts, complete CI logs, original inputs/oracle and final model results. The unchanged
four tasks pass all three rounds on the corrected runtime, 57 product calls total,
zero product errors/retries and verified handle/process cleanup. Each navigation report
also matches all 40 original-byte operands after presentation-only normalization.
Final median calls are 4/4/6/4 versus frozen legacy's 6/6/7/5 and comparator's 6/6/8/4.
Observed final median seconds are 67.16/82.43/86.31/69.59 versus legacy's
56.24/66.41/67.37/57.75. These historical, non-interleaved model timings do not establish
a controlled performance ratio; they certainly do not support a speedup claim.
Accept the focused workflow/selection change, not aggregate-schema reduction or general
competitor superiority. `artifact` remains opt-in, `legacy` remains default, B4-B6 remain
open and no publication/version/tag is approved.

G3 starts under `artifacts/competitor-gap-b4-20261029/` with fresh Taobao, WeChat and
Douyin preparation/first-query profiles and a reused low-overhead phase diagnostic.
Cross-thread cProfile cumulative times are not additive phase budgets. Profile evidence
alone is not performance acceptance; retain original hashes, mutation checks, first-use
costs, quotas and cleanup while evaluating any bounded reuse candidate.

G1 verification receipts are under `artifacts/competitor-gap-b3-20261029/`:

- `g1-profile-red.xml` preserves the initially missing profile regression.
  `g1-profile-first-green.xml` and `g1-focused.xml` preserve test-development failures
  (legacy close returns session_not_found, and legacy APK resources use apk_sha256).
  Those legacy wire semantics were retained; the assertions were corrected.
- `g1-focused-green.xml`: 83 passing profile/config/lifetime/registry/stdio/HTTP checks.
  `g1-source-full.xml`: all 1807 source tests pass in 242.02 seconds, zero skips, using
  the configured public/complex fixtures, JDK 17, JADX, dexlib2 and Rust backend.
- Both schema caches and Ruff check/format pass. Input contract size in the preview
  is 3328 o200k_base tokens versus the frozen legacy baseline's 6762; instructions
  are 479 versus 1347. These are canonical contract counts, not provider-billed tokens
  or proof of higher model success/faster execution.
- Real-model smoke uses the frozen four task prompts and same gpt-6.1-sol/medium
  provider settings, with only an explicit tool-profile selector added to the harness.
  F-Droid inventory passes (one handle, four product calls, zero errors); launcher
  navigation passes (one handle, eight calls, zero errors, exact 40 opcode/offset pairs).
  The navigation response's 40 operands and disabled launcher were independently
  checked against the existing original-byte oracle. `review_g1.py` and the initial
  review JSON files bind raw responses, receipts and oracle hashes.
- Douyin's first trial timed out before any product call; preserve its raw events,
  stderr and receipt. The navigation trial subsequently reported workspace-routing
  discovery retries but recovered. Model time includes these provider delays and
  source-suite overlap, so G1 smoke timings are not controlled performance ratios.
- The current local wheel/sdist are development acceptance artifacts still labelled
  0.2.4; they are not a publication or a replacement for the published package.
- Final G1 smoke: four successful workflows in five attempts, with the first Douyin
  provider timeout retained. Successful attempts use 21 product calls and zero product
  errors. Douyin retry passes with four calls; resource reading passes with five,
  including decoded and original-byte XML reads. Every successful run explicitly
  closes its one handle and verifies owned-process cleanup. `g1-model-review.json`
  preserves all five attempts, not only successful timings.
- `g1-package.log` verifies canonical sdist/wheel source/data equality, a clean sdist
  suite (1807 passed, 294.76 seconds), exact installed wheel byte identity and its
  full suite (1807 passed, 267.44 seconds). Runtime/tests in those packages match this
  checkpoint; final ledger and Chinese preview documentation were updated after the
  package snapshot. `g1-local-acceptance.json`, generated by `freeze_g1.py`, binds
  current runtime/tests, package bytes and original model/oracle evidence.
- This accepts G1's opt-in local workflow only. New Windows/Python matrix, the final
  focused DEX profile, three-round candidate comparison and controlled performance
  measurements remain open. The legacy default, version and release state are unchanged.

Reproduce an individual G1 model cell with a fresh output directory:

```sh
uv run --offline --no-sync --with ./artifacts/aimard-asc-mcp --with tiktoken python scripts/benchmark_model_workflows.py --task fdroid_inventory --implementation ours --tool-profile artifact_preview --round 0 --output artifacts/g1-new-trial
```

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
- `taobao-final-revisions-cpu2.json` passes 40 fresh-server trials and 20 alternating
  baseline/candidate pairs. All 100 complete collections preserve exact result/diagnostic
  digests, including duplicates and ordering; original, imported runtime and helper hashes
  remain unchanged. This old/new equality is separate from the original-byte operand oracle.
  First/repeated complete-query medians (baseline/candidate, seconds) are strings
  7.1629/1.1386 and 1.7751/0.3518; methods 5.5796/5.6088 and 5.0073/4.7714; fields
  0.5274/0.4999 and 0.0685/0.0670; method/field concurrency 5.9610/5.3779 and
  4.4398/4.6008. Startup-to-complete medians are respectively 10.0530/3.9529,
  8.5184/8.5546, 3.4258/3.4005 and 8.9238/7.9805. No median crosses both regression
  thresholds. Concurrent repeats are nevertheless 0.1610 s (3.63%) slower in aggregate,
  with paired deltas -0.1309 to +0.3118 s; method repeat deltas range -0.4606 to
  +0.4853 s. Preserve this noise rather than claiming every legacy query improved.
  All five paired string rounds improve first/repeated/startup completion; first-query
  savings range 4.8120-7.4731 s and repeated savings 1.1649-1.6108 s. No p95 claim.
- The same revision receipt's checksum-verified operation sidecars give first useful-page
  medians (baseline/candidate, seconds): string 4.8454/3.6048, method 4.0640/4.0322,
  field 3.4258/3.4005 and concurrent 3.7559/3.3312. Across ten complete collections per
  single-query scenario, string page/retry totals fall from 90/20 to 40/0; method pages
  remain 360, field pages 10 and concurrent pages 370, with zero legacy-query retries.
  String speedup includes removed response-limit retries and fewer byte-bounded pages,
  not only selected-set scan reuse. Peak retained temporary logical bytes for concurrent
  legacy work are 125404628/118209317; these remain separate from descendant RSS.
- Commit 046045b adds the revision wrapper and its distribution inclusion checks;
  CI `40468194811` passes all 25 jobs. All eight downloaded source JUnit files contain
  1649 tests with zero failures/errors/skips; canonical-sdist/exact-wheel, Rust, signing
  and stability jobs pass as well. This accepts the wrapper's final code commit, not B1
  performance completeness or a release. Subsequent ledger-only edits do not change runtime.
- `taobao-final-operands-cpu4.json` passes 30 trials with five alternating rounds, two
  complete repeats and unchanged per-call/trial/RSS/disk budgets. Independent
  `taobao-final-operands-cpu4-verified.json` accepts all 80 complete collections against
  original DEX bytes (2163 string sites, 56791 type sites); full diagnostics, input,
  runtime, helper/sidecar identities and oracle cleanup pass. First/repeated complete-query
  medians (ours/comparator, seconds) are strings 0.9337/2.0783 and 0.3176/0.5310;
  types 12.1646/14.2156 and 6.6850/11.3457; concurrent 12.1548/18.4767 and
  6.9438/12.4987. Startup-to-complete medians are 2.8724/3.1821, 14.0950/15.3609
  and 14.0514/19.5508. Every paired first/repeated complete query favors ours, but
  string startup savings span -0.1133 to +0.3423 s: one round is slower, so no robust
  string startup-win claim. Type/concurrent startup savings span 0.3634-1.2958 s and
  4.5264-5.7343 s. Four-CPU old/new regression timing is the next running cell.
- Four-CPU first useful-page medians expose a remaining tradeoff: string 2.5686/3.0934 s,
  type 7.5881/4.2066 s, concurrent 2.6199/4.6624 s (ours/comparator). Our type first page
  is slower despite faster complete collection; total counts/complete scan and selected-set
  publication occur before that page. Concurrent first useful result can be a string page,
  not evidence that its type page is ready. Page totals remain 40/20, 610/400 and 650/420,
  zero retries. Concurrent descendant RSS peaks at 160595968/1338667008 bytes, while ours
  retains up to 119199188 temporary logical bytes versus zero comparator trial files.
  This is not universal latency or total-memory superiority; preserve first-page and
  preparation costs for subsequent measured work instead of hiding them in full-result ratios.
- Two-CPU checksum-verified first useful-page medians likewise separate this tradeoff:
  strings 3.4362/5.1860 s, types 9.2727/7.0332 s and concurrent 3.5501/7.4841 s.
  Thus the slower standalone type first-page path appears in both CPU cells, not just
  one four-CPU sample; the accepted improvement is complete collection and repeat reuse.
- `taobao-final-revisions-cpu4.json` passes another 40 fresh-server trials, 20 alternating
  pairs and 100 complete collections with exact old/new result/diagnostic digests and
  unchanged original/runtime/helper identities. First/repeated complete medians
  (baseline/candidate, seconds) are string 5.5113/0.9147 and 1.4342/0.2914; method
  4.4877/4.4756 and 3.8720/3.7813; field 0.4014/0.3894 and 0.0624/0.0620; concurrent
  4.5881/4.4602 and 3.9280/3.8409. Startup-to-complete medians are 7.5504/2.8975,
  6.4420/6.5053, 2.3763/2.3816 and 6.6332/6.4099. No median crosses both regression
  thresholds. Method startup paired deltas nevertheless range -0.0252 to +0.3572 s;
  field startup ranges -0.3230 to +0.3012 s. Preserve these rather than declaring all
  starts faster. All paired string first/repeat/startup completions improve; first-query
  savings range 4.3050-4.7076 s, repeated savings 1.0741-1.3563 s. Taobao's two/four-CPU
  cells are now complete on the frozen runtime, not the full multi-input B1 matrix.
- Frozen F-Droid holdout `holdout-final-operands-cpu{2,4}.json` each passes 30 fresh
  trials. Each corresponding `-verified.json` independently accepts all 80 complete
  collections (62 strings, 1772 type sites), diagnostics, source/sidecar identities and
  oracle cleanup. The frozen holdout and product runtime were not tuned after observation.
  Medians in seconds, ours/comparator:

  | CPU | Complete query | First complete | Repeated complete | Startup to complete |
  | --- | --- | --- | --- | --- |
  | 2 | string | 0.1965/0.6569 | 0.0347/0.0344 | 1.3948/1.6568 |
  | 2 | type | 1.4369/1.1196 | 0.1961/0.3497 | 2.6452/2.1005 |
  | 2 | concurrent | 1.4768/2.1499 | 0.2343/0.5740 | 2.7066/3.1605 |
  | 4 | string | 0.2022/0.5143 | 0.0339/0.0424 | 1.3699/1.4702 |
  | 4 | type | 1.4002/0.8939 | 0.1971/0.3698 | 2.6116/1.9010 |
  | 4 | concurrent | 1.4000/1.4807 | 0.2310/0.4844 | 2.5648/2.4265 |

  Every paired holdout type first/startup completion is slower: first-query deltas
  +0.2457 to +0.3665 s at two CPUs and +0.4891 to +0.6058 s at four. Conversely every
  paired type repeat is faster, by 0.1237-0.1593 s and 0.1428-0.1891 s. Four-CPU
  concurrent startup is also consistently slower by 0.0959-0.2002 s despite faster
  complete-query execution; retain preparation in the end-to-end result. One-page string
  repeats are approximately tied, not a demonstrated holdout warm-string speedup.
  Type first useful-page medians are 2.4951/2.0328 s (two CPUs) and 2.4623/1.8281 s
  (four); concurrent first useful-page medians are 1.5477/2.1495 and 1.4115/1.6725 s.
  Page totals at either budget are string 10/10, type 30/20 and concurrent 40/30, no
  retries. Concurrent descendant RSS peaks are 146423808/603648000 bytes (two CPUs)
  and 145096704/753905664 (four); ours additionally retains 19400357 temporary bytes.
  These are measured residual gaps for B2/B4, not grounds to change holdout selectors,
  skip slow pairs or advertise unconditional parity. Old/new holdout gates follow next.
- `holdout-final-revisions-cpu{2,4}.json` each passes 40 trials, 20 alternating pairs,
  100 full collections and exact old/new result/diagnostic equality; all bound identities
  remain unchanged. Neither CPU cell crosses both existing-workflow regression thresholds.
  Complete-query medians in seconds, baseline/candidate:

  | CPU | Query | First complete | Repeated complete | Startup to complete |
  | --- | --- | --- | --- | --- |
  | 2 | string | 0.1942/0.2056 | 0.0342/0.0347 | 1.4011/1.4421 |
  | 2 | method | 0.3532/0.3335 | 0.1468/0.1464 | 1.5870/1.5853 |
  | 2 | field | 0.1739/0.1783 | 0.0288/0.0248 | 1.4015/1.3777 |
  | 2 | concurrent | 0.4034/0.4078 | 0.1790/0.1730 | 1.6083/1.6344 |
  | 4 | string | 0.1976/0.1988 | 0.0316/0.0291 | 1.3356/1.3556 |
  | 4 | method | 0.3290/0.3332 | 0.1469/0.1511 | 1.5085/1.4886 |
  | 4 | field | 0.1830/0.1799 | 0.0278/0.0318 | 1.3412/1.3335 |
  | 4 | concurrent | 0.3439/0.3444 | 0.1706/0.1664 | 1.4887/1.5124 |

  Two-CPU string first complete is 5.87% slower but only 11.4 ms, with all five pairs
  +1.5 to +31.7 ms; four-CPU field repeat is 14.39% slower but only 4.0 ms. Report
  absolute and relative changes together, not percentages alone. Four-CPU method startup
  paired deltas span -0.0625 to +0.2266 s despite a slightly better median. Both revisions
  use 10/20/10/30 pages across string/method/field/concurrent repeats, with zero retries.
  Concurrent retained temporary bytes are 19685760/19370367 at both budgets; descendant
  RSS peaks are 144973824/143818752 (two CPUs), 145612800/146010112 (four).
- Remaining first-useful-page medians were extracted from checksum-verified operation
  sidecars, separately from full completion: four-CPU Taobao string 3.5414/2.5903 s,
  method 2.8332/2.8443, field 2.3763/2.3816 and concurrent 2.4456/2.4432
  (baseline/candidate). Held-out method first pages are 1.5254/1.5231 s at two CPUs
  and 1.4443/1.4227 at four; concurrent first pages are 1.4681/1.4983 and
  1.3604/1.3786. One-page string/field first-use times equal their complete times above.
  No product or harness edits occurred during these frozen measurements. Next run the
  identical five-round matrices for WeChat and Douyin; no B1/B2 transition or release yet.
- WeChat `wechat-final-operands-cpu{2,4}.json` each passes 30 fresh-server trials,
  five alternating rounds and two complete repeats. Each corresponding `-verified.json`
  independently accepts all 80 complete collections: 738 string sites and 44002 type
  sites, zero missing/extra, all diagnostics (865327 methods, 21430036 instructions,
  41085 methods without code), source/sidecar identities and oracle cleanup checked.
  Complete-query medians in seconds, ours/comparator:

  | CPU | Query | First complete | Repeated complete | Startup to complete |
  | --- | --- | --- | --- | --- |
  | 2 | string | 0.7639/3.9464 | 0.1321/0.2239 | 3.8718/5.2028 |
  | 2 | type | 12.6511/12.4559 | 5.0406/7.3298 | 15.9441/13.7062 |
  | 2 | concurrent | 12.7732/20.8444 | 4.9439/8.7880 | 15.8802/22.1218 |
  | 4 | string | 0.8717/2.8934 | 0.1582/0.2867 | 4.4134/4.4672 |
  | 4 | type | 14.1040/11.8395 | 5.2331/7.8975 | 17.8205/13.2176 |
  | 4 | concurrent | 13.0560/15.9160 | 5.3227/8.6917 | 15.9782/17.3129 |

  Every paired type repeat improves (2.2663-2.6990 s at two CPUs, 2.4415-3.1448 s
  at four), but type startup is consistently slower by 1.7273-2.4740 s and
  2.8982-5.4985 s respectively. Four-CPU type first-query execution is also slower in
  every pair by 1.4595-3.5045 s. All paired concurrent complete first/repeated/startup
  timings improve; startup savings span 5.7609-7.0391 s (two CPUs) and 1.3347-4.0862 s
  (four). String first/repeat improves in every pair, but four-CPU string startup savings
  range -0.0637 to +0.9127 s. No universal startup win or CPU-scaling claim follows.
  Type first useful-page medians are 11.1395/6.6669 s (two CPUs), 12.4648/5.3019 s
  (four); string first pages are 3.7839/5.2028 and 4.2989/4.4672; concurrent first
  pages are 4.4236/9.0382 and 3.7086/6.3392. First-page evidence is taken from
  checksum-verified operation sidecars, not inferred from full completion.
- WeChat page totals at both budgets are string 20/10, type 460/220 and concurrent
  480/230, with zero retries. Concurrent descendant RSS peaks are
  167116800/1067143168 bytes (two CPUs) and 162824192/1581793280 (four); ours also
  retains up to 182581790 temporary logical bytes, versus zero comparator trial files.
  These remain B2 output-repetition and B4 preparation/first-scan gaps. Measurements
  use the same shared host, not a dedicated performance machine; retain all alternating
  pairs and do not turn the comparison into an isolated microbenchmark claim.
- `wechat-final-revisions-cpu{2,4}.json` each passes 40 real-MCP trials, 20 paired
  comparisons and 100 exact full-result/diagnostic comparisons with unchanged bound
  identities. However, the four-CPU method first-complete median is 4.8732/5.1461 s
  (baseline/candidate): +0.2729 s, +5.60%, exceeding both regression thresholds.
  The receipt's `passed` status proves functional equality, not this performance gate.
  Its paired deltas span -0.1033 to +0.5017 s; repeated medians 4.2223/4.2475 s and
  startup-to-complete 7.9416/7.9203 s do not cross the gate. The two-CPU method first
  medians are 4.9252/4.8097 s, also not a regression. Preserve the four-CPU first
  failure and investigate phases before accepting the WeChat revision cell.
  Next predeclared repetition: ten alternating full-method rounds at four CPUs, two
  complete repeats, identical frozen input/runtime/helpers and resource budgets,
  `wechat-method-regression-repeat-cpu4.json`. Retain all ten rounds and aggregate
  with the original five rather than choosing a favorable subset. No source fix yet.
- Ranked diagnosis hypotheses and falsifiers: (1) host/transport scheduling variation,
  which predicts no consistent regression in the declared larger alternating sample;
  (2) block-read/decompression overhead, which predicts slower cached-page aggregates in
  both first and repeated collections; (3) initial compression/publication, which predicts
  consistently slower first pages. Existing sidecars show 37 successful method pages for
  each collection, no retries, and retained selected sets of 7631024/475311 bytes
  (baseline/candidate). Candidate first-page call times are lower in three of five pairs;
  warm totals are close, so neither compression hypothesis is yet established. The first
  failing round combines +0.2443 s first-page time and +0.2226 s subsequent-page sum;
  the last combines only +0.0210 s first-page time with +0.2763 s subsequent-page sum.
  Do not patch the codec based solely on a whole-workflow median.
- `wechat-method-regression-repeat-cpu4.json` passes all 20 fresh-server trials,
  ten alternating pairs, 40 full result/diagnostic comparisons and unchanged bound
  identities. Predeclared ten-round medians (baseline/candidate, seconds) are first
  4.83095/4.80580, repeated 4.00250/3.98390 and startup 7.58580/7.62095. Combining
  every original and added round, fifteen-pair medians are first 4.8448/4.8564
  (+0.0116 s, +0.24%), repeated 4.0380/4.0223 and startup 7.6199/7.7090
  (+0.0891 s, +1.17%). Neither added nor combined sample crosses both thresholds.
  All-fifteen first-query paired deltas span -0.4462 to +0.5017 s, median +0.0595 s,
  with ten slower pairs; this is not a method speedup claim. Repeated paired deltas
  span -0.4433 to +0.1730 s; startup spans -0.4140 to +0.4579 s. No p95 estimate.
  The added sample's first-page call medians are 1.01615/0.99540 s, later-page sums
  2.94895/2.95630 s and warm-page sums 3.10590/3.10945 s. A sustained codec or
  publication regression is not reproduced; host/transport variation is consistent
  with these measurements but not independently proven as the cause. Keep the original
  gate failure, accept the expanded no-material-regression cell, and make no speculative
  runtime change. Small residual differences remain visible.
- Original five-round WeChat revision medians in seconds, baseline/candidate (the
  four-CPU method first-query row is the preserved initial failure, superseded only for
  gate assessment by the full fifteen-pair analysis above):

  | CPU | Query | First complete | Repeated complete | Startup to complete |
  | --- | --- | --- | --- | --- |
  | 2 | string | 5.5049/0.7785 | 2.0547/0.1293 | 8.7432/4.1084 |
  | 2 | method | 4.9252/4.8097 | 4.0439/4.1405 | 8.2060/8.0350 |
  | 2 | field | 0.5278/0.5227 | 0.0389/0.0386 | 3.8146/3.7575 |
  | 2 | concurrent | 5.1806/5.1588 | 4.0492/4.0802 | 8.4122/8.4143 |
  | 4 | string | 5.4430/0.7841 | 2.0537/0.1287 | 8.3799/3.6241 |
  | 4 | method | 4.8732/5.1461 | 4.2223/4.2475 | 7.9416/7.9203 |
  | 4 | field | 0.5168/0.5159 | 0.0403/0.0375 | 3.4223/3.3886 |
  | 4 | concurrent | 4.9602/4.9493 | 4.0895/4.1151 | 7.7218/7.8352 |

  No other original median crosses both thresholds. All string paired first/repeat/startup
  completions improve; first-query savings span 4.5165-5.4843 s (two CPUs) and
  4.4922-5.2918 s (four), repeated savings 1.8482-2.0812 and 1.8270-2.0225 s.
  Concurrent first-query deltas span -0.1523 to +0.2996 s and -0.2057 to +0.1388 s;
  its startup deltas span -0.1466 to +0.4144 and -0.2014 to +0.4188 s. Do not call
  every legacy workflow faster. String pages/retries fall from 60/30 to 20/0 at both
  budgets, while method/field/concurrent pages stay 370/10/380, with zero retries.
  Concurrent retained temporary bytes fall from at most 189176366 to 181978353;
  descendant RSS peaks are 159428608/157757440 (two CPUs), 158507008/157650944 (four).
  Checksum-verified first useful-page medians are strings 5.6757/4.0040 and
  5.4091/3.5344, methods 4.3064/4.2346 and 4.0889/4.0405, concurrent 4.1071/4.1472
  and 3.4061/3.4815 (two then four CPUs); one-page field results equal full completion.
  B1 remains open for Douyin and final evidence consolidation; no new publication.
- `douyin-final-operands-cpu2.json` completes 30 fresh-server trials at unchanged
  two-CPU/per-call/trial/RSS/disk budgets. Independent
  `douyin-final-operands-cpu2-verified.json` deliberately remains **failed**: all 40
  product collections pass, with 4778 string sites and 115306 type sites; all 20
  comparator type collections pass; all 20 comparator string collections contain one
  extra site and no missing sites. Diagnostics cover 2708565 methods, 52547329
  instructions and 213254 methods without code. Input/runtime/helper/sidecar identities
  and oracle cleanup pass. Timing-receipt `passed` does not override this accuracy failure.
  The extra site is identical in every failing collection: `classes9.dex`,
  `PushVerifyLoginPadFragment.onViewCreated`, reported `const-string` at byte offset 600.
  The preserved independent `douyin-comparator-extra-string.json` uses the same original
  APK SHA256 c2b49cb5f85b8432e9c73a259c9eb9b8dd8d891e853177df2ce5a14ee4f3f5b9;
  this method has only 598 instruction bytes. Fresh expected/actual site digests match
  the original false-positive diagnosis. Do not remove the extra row, weaken the oracle,
  or publish an equal-correctness string/concurrent speed ratio.
- The independently correct standalone Douyin type cell has first/repeated/startup-to-
  complete medians 38.5059/33.5523, 14.5910/19.6587 and 44.6215/35.0845 s
  (ours/comparator). Every paired cold execution/startup is slower: +2.0502 to +7.4640 s
  and +6.1718 to +11.8115 s respectively. Every repeat improves by 3.3018-5.7237 s.
  Type first useful-page medians are 29.8478/15.5341 s, with 1310/610 pages across
  both repeats, zero retries. Descendant RSS peaks at 134410240/860991488 bytes,
  but ours additionally retains 479995139 temporary logical bytes. Cold scan, startup,
  output repetition and tmpfs costs remain explicit residual gaps, not an overall win.
  Product-only string first/repeated/startup medians are 2.4139/0.6170/8.4566 s;
  concurrent medians are 38.2469/14.6575/44.0187 s. Their complete results are correct,
  but comparator accuracy rejects those matched comparison cells. Product string/concurrent
  pages total 80/1390; concurrent temporary bytes peak at 480254510 and descendant RSS
  at 165658624. All raw comparator timings remain in the original receipt, not a ratio.
- Source inspection identifies a B4 profiling candidate, not a measured causal finding:
  `native_types._types` visits every method's declaration metadata in Python before
  invoking the checked instruction scanner; `native_strings._strings` can instead use
  `class_selector`/`select_directory` for a checked native directory pass. The existing
  bulk selector does not yet expose the new type mode. Profile this difference alongside
  preparation/transport before changing it; do not weaken instruction/declaration checks
  or modify the frozen runtime during the remaining B1 measurements.
- `douyin-final-revisions-cpu2.json` passes 40 trials, 20 alternating pairs and 100
  complete result/diagnostic equality checks with unchanged input/runtime/helpers.
  Its functional `passed` does not close performance: method first-complete median
  9.9752/10.5069 s (baseline/candidate) is +0.5317 s, +5.33%, crossing both thresholds.
  Paired deltas span -0.2047 to +0.5317 s. Repeated medians 7.9911/8.0657 s and
  startup 16.1990/16.5108 s remain below the combined gate; concurrent first/repeated
  medians improve. Preserve this first failure independently of the earlier WeChat signal.
  Predeclare ten additional alternating full-method rounds at two CPUs with unchanged
  input/runtime/helpers, two complete repeats and identical budgets:
  `douyin-method-regression-repeat-cpu2.json`. Examine first-page versus subsequent cached
  pages under the same host/transport, block-read and first-publication hypotheses; combine
  all fifteen pairs for assessment rather than choosing a favorable repetition. No fix yet.
- `douyin-method-regression-repeat-cpu2.json` passes 20 fresh-server trials, ten
  alternating pairs, 40 complete result/diagnostic checks and unchanged bound identities.
  Ten-round first/repeated/startup medians (baseline/candidate, seconds) are
  10.95955/9.85130, 8.19195/7.74465 and 17.62675/16.20085. All fifteen pairs combined
  give 10.8336/9.9505, 8.1177/7.9730 and 17.3601/16.3757; neither expanded sample
  crosses both regression thresholds. Preserve the initial +5.33% gate failure rather
  than relabeling its receipt. No sustained material regression is reproduced, but noise
  is substantial: all-fifteen first-query paired deltas span -3.9790 to +2.4678 s,
  median -0.1485 s; repeated deltas -1.2012 to +2.5567 s, median -0.1088 s; startup
  deltas -5.0969 to +1.0835 s, median +0.1734 s (eight of fifteen slower). Thus the
  improved unpaired startup medians do not establish a robust paired startup win.
  Added-sample first-page medians are 2.40625/2.09465 s, later-page sums
  6.65935/6.04830 s and warm-page sums 6.38025/6.05450 s. The proposed compression/
  block-read regressions are not supported by a consistent phase slowdown; host/transport
  variation remains a plausible, unproven explanation. Accept the expanded engineering
  no-material-regression gate, not a method speedup claim; no runtime patch was made.
- Original five-round two-CPU Douyin revision medians, baseline/candidate, seconds:

  | Query | First complete | Repeated complete | Startup to complete |
  | --- | --- | --- | --- |
  | string | 18.5561/2.8500 | 2.2662/0.6713 | 25.2790/10.2496 |
  | method | 9.9752/10.5069 | 7.9911/8.0657 | 16.1990/16.5108 |
  | field | 1.3436/1.3628 | 0.0741/0.0857 | 7.8059/7.7039 |
  | concurrent | 11.5380/10.6766 | 8.1773/7.9746 | 18.3650/17.0273 |

  The method first-query row remains the initial failure addressed above. No other median
  crosses both thresholds: field repeat is +15.65% but only +11.6 ms. Every paired string
  first/repeat/startup improves, with first savings 14.7368-20.7916 s and repeated savings
  1.5949-2.1109 s. Concurrent paired deltas remain mixed: first -2.3499 to +0.0713 s,
  repeated -0.9627 to +0.3101 s, startup -2.4215 to +0.2677 s. Original first useful-page
  medians from checksum-verified sidecars are string 10.1157/9.4739, method
  8.6397/8.4130, field 7.8059/7.7039 and concurrent 8.8122/8.5713 s. String page/retry
  totals fall from 100/10 to 80/0; method/field/concurrent remain 720/10/730 pages,
  zero retries. Concurrent retained temporary bytes are 491715311/477977347 and
  descendant RSS 152223744/152952832, with storage separately reported. Method selected
  cache files are 14442673/848047 bytes, both within unchanged 16/32-MiB quotas.
  Next is the four-CPU Douyin matrix; all current original receipts and runtime hashes
  remain intact, B1 is not complete, and nothing is published.
- Before starting four-CPU Douyin revision timing, predeclare a larger method sample:
  the standard five-round four-scenario matrix plus ten additional alternating method-only
  rounds, regardless of the first five's result. Earlier WeChat/Douyin first-five method
  gates were noisy; all fifteen pairs will be assessed together, while preserving both
  original receipts. Other scenarios retain five paired rounds. This is additional
  sampling under unchanged correctness/budget/regression criteria, not a relaxed threshold.
- Completion-audit gap identified before B1 closure: large-input cached MCP collections
  have original-byte site/diagnostic oracles, and fixture tests cover cache-disabled
  pagination, but there is not yet a dedicated current-runtime receipt comparing the
  full uncached backend result (all fields, ordered rows and duplicates) with the cached
  large-input collections. Add that acceptance check using original-byte canonical bundles
  and the existing recorded-page replay, for all four inputs. An uncached direct scan
  may use the existing verifier-only large page limit to collect its complete reference
  set; this is an offline semantic oracle, not evidence of unbounded MCP responses or
  uncached production latency. Keep real capped MCP and fallback fixture evidence separate.
  Do not rerun independent decoders unnecessarily or substitute a count-only comparison.
- Four-CPU Douyin `douyin-final-operands-cpu4-verified.json` retains the same accuracy
  verdict after all 30 timing trials: all 40 product collections and all 20 comparator
  type collections pass; all 20 comparator string collections contain the same one
  out-of-instruction-range extra site, with identical expected/actual site digests to the
  two-CPU report. Full original-byte diagnostics, bound identities and cleanup pass;
  the combined verifier correctly remains failed. Standalone type first/repeated/startup
  medians (ours/comparator, seconds) are 38.0230/28.5369, 14.8837/21.2285 and
  43.1341/30.2138. Every paired first/startup is slower by 7.8970-9.5980 s and
  11.0671-13.4558 s; every repeat improves by 4.8781-7.4860 s. Type first-page
  medians are 27.9078/10.1811 s, pages 1310/610, no retries. Descendant RSS peaks
  at 134651904/1206304768 bytes; ours also retains 479996463 temporary logical bytes.
  Product-only string first/repeated/startup medians are 2.4088/0.6658/7.5485 s,
  concurrent 35.9111/14.4295/40.6201 s; the comparator string accuracy failure prevents
  equal-correctness string/concurrent performance ratios. Product concurrent pages total
  1390, peak descendant RSS 163618816 and temporary logical bytes 480254686.
- `douyin-final-revisions-cpu4.json` passes 40 trials, 20 alternating pairs, 100 exact
  full-result/diagnostic comparisons and unchanged identities. None of its single-query
  medians crosses both regression thresholds, but the concurrent repeated-complete median
  is 6.4142/6.8368 s (baseline/candidate): +0.4226 s, +6.59%. All five paired deltas
  are positive, +0.0191 to +0.5427 s, so do not discard this as noise or substitute the
  method-only expanded sample. First/startup concurrent medians are 8.0481/8.0999 and
  12.1802/12.2169 s. Preserve this gate failure and predeclare ten additional alternating
  concurrent-only rounds, two complete repeats, unchanged runtime/input/helpers/budgets:
  `douyin-concurrent-regression-repeat-cpu4.json`. Assess all fifteen concurrent pairs;
  inspect method/field page timings and cache/transport phases if the signal persists.
  The independently predeclared method-only expansion is currently running and cannot
  close this separate concurrent gate. B1 remains open.
- Predeclared `douyin-method-expanded-cpu4.json` passes 20 fresh-server trials, ten
  pairs, 40 complete result/diagnostic comparisons and unchanged identities. Its added
  first/repeated/startup medians are 9.41525/8.92100, 7.20930/7.32425 and
  14.36495/13.34850 s (baseline/candidate). All fifteen method pairs give
  8.7621/8.6774, 7.0695/6.9979 and 13.2291/13.0875 s; neither sample crosses both
  regression thresholds. Full paired deltas span -1.8352 to +1.0996 s (first),
  -0.7141 to +1.1198 s (repeat), -2.1141 to +1.8144 s (startup); paired medians
  are -0.0620, -0.0589 and +0.0379 s. Nine of fifteen startup pairs are slower,
  so the favorable unpaired median is not a robust startup speedup. This closes only
  the expanded method regression gate, not the independently failing concurrent gate.
- `douyin-concurrent-regression-repeat-cpu4.json` passes 20 fresh-server trials, ten
  pairs, 80 full result/diagnostic comparisons and unchanged bound identities, but the
  expanded performance gate **still fails**. Added-ten first/repeated/startup medians
  (baseline/candidate, seconds) are 7.48050/7.61090, 5.94580/6.14340 and
  11.41330/11.56085. All-fifteen medians are 7.5539/7.6686, 5.9765/6.3877 and
  11.5074/11.5917. Repeated completion regresses +0.4112 s, +6.88%, with every one
  of fifteen paired deltas positive (+0.0191 to +0.6471 s, median +0.2438 s).
  Added-ten alone is below the percentage threshold, but cannot replace the combined
  sample; do not select that subset as a pass. First/startup paired deltas span
  -0.1147 to +1.1709 s and -0.2013 to +1.5528 s. The directionally consistent repeat
  slowdown is now actionable; profile cached-page processing, lock waiting and transport
  before a minimal fix. Further repetitions are not a substitute for diagnosis.
- The diagnostic helper `profile_cached_collections.py` (artifact directory) isolates
  concurrent cached service collections without MCP transport. The first attempt used
  simultaneous CPython 3.13 cProfile tools and failed with `Another profiling tool is
  already active`; preserve `profile-concurrent-baseline/report.json` and the original
  `profile_cached_collections-thread-profilers-failed.py`. The corrected helper profiles
  one collection while the other still runs concurrently. Its valid baseline/candidate
  receipts are `profile-concurrent-{baseline,candidate}-single/report.json`. Callbacks
  from the concurrent thread may appear in a profile; these are not MCP timing gates.
  The pre-fix cache encoded every restored row again solely for byte accounting:
  approximately 113211 JSON encoder calls versus 47065 in the published baseline.
  Bounded block decoding accounted for about 0.15 s, with zlib inflation about 0.025 s;
  these profiles do not support blaming decompression or lock waiting for the regression.
- Freeze the exact pre-fix runtime in `read-budget-before/droidasc_mcp` before changing
  runtime source. `read-budget-red.xml` fails on the redundant compact row encoding,
  while row order and final byte bounds already pass. The fix reads validated block
  byte counts instead: allow only the skipped leading block prefix plus one final
  bounded block. Decompressed read bytes stay at most `maximum + 2 * MAX_BLOCK_BYTES`;
  final target resolution and `reference_page` still enforce the response prefix/cap.
  No schema, compression format, storage quota, scanner or public contract changes.
  `read-budget-green.xml` passes and `read-budget-focused.xml` passes 140 tests,
  including 15 offset/output-budget comparisons with the exact full-list page formatter.
  A subsequent cancellation test also passes and proves completed cache reuse survives
  an interrupted read. The current source needs fresh full-suite/CI acceptance.
- `profile-concurrent-read-budget/report.json` verifies identical ordered hashes for
  47005 method and 489 field sites, unchanged runtime/input/helper identities and cleanup.
  Method collections remain 72 pages; the profile now records 47064-47065 JSON encoder
  calls, matching the old baseline rather than the pre-fix double encoding. Unprofiled
  warm service completion is 1.1408 s in this diagnostic, not a real-MCP speed claim.
  Predeclare five alternating real-MCP concurrent rounds against the frozen pre-fix
  snapshot (`douyin-read-budget-isolation-cpu4.json`), then five against published
  v0.2.4. Preserve every result and use full row/diagnostic equality in both comparisons.
  The older corpus receipts remain bound to their pre-fix runtime; they do not prove
  current-runtime performance or cache parity.
- `douyin-read-budget-isolation-cpu4.json` passes ten fresh-server trials, five pairs
  and forty complete collection comparisons, with input/runtime/helper identities
  unchanged. The frozen baseline hashes equal the preceding 046045b candidate hashes;
  only `reference_cache.py` differs in the new runtime. Pre-fix/fixed medians (seconds)
  are 8.1477/7.5613 first, 6.5677/6.0571 repeat and 12.2152/11.5711 startup.
  All five paired first/repeat/startup deltas are negative; repeat deltas span
  -0.7284 to -0.3897 s. This isolates a real-MCP improvement from the bounded-read fix,
  not comparator parity. The separately predeclared published-baseline test remains next.
- Add `scripts/verify_selected_set_parity.py` to reconstruct a hash/size/inventory-checked
  original-byte bundle and compare complete uncached string/type backend responses with
  recorded MCP collections. Ordered rows, duplicate multiplicity and all backend fields
  must match; extra response context must match session-open metadata. Replay checks
  actual requests, continuations, diagnostics and provenance. Receipt/runtime/helper/
  sidecar identities remain bound, cache scopes are counted, and failed attempts are saved.
  This oracle is cache equivalence, not an independent instruction decoder or timing.
  `selected-parity-initial.xml` records two fixture-assumption failures (a one-site string
  selector and an expansion budget above the fixture limit); `selected-parity-fixed-fixture.xml`
  records the overly strict assumption that every repeated page uses the selected-set
  layer rather than the existing exact-page layer. Corrected fixture and scope assertions
  pass all 27 tests in `selected-parity-cache-scopes.xml`, including real service/direct
  backend comparison, altered row order/duplicates/metadata/context and receipt identities.
  Both cache layers remain distinguished; large-input verification is still pending.
  Include the verifier, its replay dependencies and tests in canonical-sdist required files.
- The separately declared `douyin-read-budget-baseline-cpu4.json` passes ten fresh-server
  trials/five pairs/forty complete collection comparisons and unchanged identities.
  Published v0.2.4/fixed medians are 15.7213/9.6300 s first, 11.0441/8.4417 s repeat
  and 22.1976/20.9054 s startup. None crosses both regression thresholds, but these
  timings are noisy: paired first deltas span -7.9324 to +9.1860 s, repeat -19.8463 to
  +1.4689 s and startup -12.5420 to +42.6574 s. Do not advertise a percentage speedup
  from this sample. The cleaner isolated before/after result above supports the fix;
  this five-pair check preserves semantic compatibility but not a stable baseline ratio.
  A later host snapshot shows load averages 8.98/11.76/7.02 while the subsequent source
  suite is running; that snapshot is not evidence establishing the earlier timing cause.
- `read-budget-source-full.xml` is an interrupted local run, not a passing full suite:
  after 794.16 s, 454 tests had passed without reported failures. Interrupt the owned
  pytest process with SIGINT rather than keep spending the implementation turn on the
  unusually slow local run; observed pytest/server/resource-tracker PIDs then all exit.
  Preserve the partial XML and require the new commit's complete remote source/package
  matrix. No required gate is waived, and the older 1649-test/CI result is not relabeled
  as covering these changes. Focused cache/page tests and the 27 parity-verifier tests
  remain the completed local evidence; remaining large-input parity is still open.
- Freeze B1 at `b64f85c5e555ea27e9dc5eed6b058008a777d07c`, pushed only to the
  development branch. CI `40498703094` completed successfully in all 25 jobs, verified
  against the exact head SHA; this does not cover subsequent dirty B2 changes. The detached
  worktree `artifacts/competitor-gap-b1-20261027/b1-read-budget-frozen` contains this
  exact tracked commit plus the measured `_dexscan.abi3.so`; runtime hashes match the
  candidate in `douyin-read-budget-isolation-cpu4.json`. Use this worktree for pending
  B1 acceptance while B2 changes the primary checkout. The initial attempted copy used
  a nonexistent interpreter-specific extension filename; the actual ABI3 extension was
  then copied and its identity verified. No release, version change or main update.
- B2 starts with an actual upstream adaptation in `reference_groups.py`, not another
  output-format design exercise. Preserve `findrefs_structured`'s target-set/evidence-list
  accumulation, using canonical caller/DEX identities and contiguous caller runs so flat
  ordering and duplicate sites survive page boundaries. `NOTICE` records upstream revision,
  original function and modifications; package license files and required sdist members
  include this attribution. Six regressions in `grouping-port-red.xml` first fail for the
  missing capability, then pass in `grouping-port-green.xml`: all four target kinds,
  duplicate sites, repeated/noncontiguous callers, cross-DEX identity, original metadata,
  empty string targets and a single caller split across chunks. This helper is not wired
  to MCP yet and proves no page-count/latency improvement. Next wire the grouped collector,
  bounded continuations and opt-in public contract; retain the existing flat default.
- B2 now exposes grouped references through the actual session query tool, reusing bounded
  flat pages and existing caches. HMAC cursors bind the session, selector and immutable
  preparation/runtime identity; active queries pin the session, and cancellation/deadline
  checks retain normal cleanup. Existing optional index creation does not invalidate cursors.
  Evidence: `grouping-focused.xml` (211 passing), `grouping-cursor-and-harness.xml` (101),
  and `grouping-identity-transports.xml` (34, including real stdio and HTTP). These receipts
  live in the B1 candidate directory but test B2; they are not frozen B1 acceptance.
- Preserve the first B2 performance smoke, `artifacts/competitor-gap-b2-20261027/holdout-grouped-smoke.json`:
  four fresh servers, one alternating round, two repeats, 16 full collections, unchanged
  identities and exact flat/grouped rows/diagnostics. F-Droid operands used 8/6 pages and
  1,291,212/1,394,982 tool-text bytes (flat/grouped). Concurrent member queries used 6/6
  pages and 964,100/952,538 bytes; repeated collection latency was 0.6049/0.7789 s.
  Fewer pages alone is not success: payload grew for operands and the repeated member
  workflow slowed. This is exploratory evidence, not five-round acceptance or a fresh
  B2 holdout. Tool-text bytes are not the encoded structured-response cap or wire framing.
- Freeze that initial B2 runtime/helpers in `grouped-before-target-table/{src,scripts}`
  under the B2 artifact directory. Keep upstream grouping, replace repeated full targets
  with indices into its matches table, and lift shared offset units into each group header.
  First-appearance target order makes indices stable; changes of target kind or unit split
  groups. Every original row/field/duplicate must reconstruct exactly. Four target-kind
  tests first fail in `target-table-red.xml`; implementation and transport retest are underway.
  `target-table-green.xml` preserves 113 passing tests plus an HTTP readiness timeout before
  any HTTP query; do not report this run as fully passing. No B2 acceptance or release yet.
- The target-table change now round-trips all four target kinds and passes exact incremental
  byte-budget checks, mixed/absent/null offset units, index-width changes and rejected-row
  immutability. Benchmark replay independently checks target index bounds/types, first-use
  order, complete table use and header collisions. The initial HTTP startup log was empty;
  the unchanged 10-second readiness check is retained, and a separate fresh stdio/HTTP
  retry passes both transports in 47.40 s (`target-table-transports-rerun.xml`). This retry
  does not erase the initial timeout. Input schemas, Ruff lint/format and diff whitespace
  checks pass; output schema regenerated.
- `fdroid-target-table-smoke.json` completes the same four fresh-server smoke trials with
  exact complete-result equality, unchanged inputs/runtime/helpers and no retry responses.
  Operand text is now 1,291,212/1,319,304 bytes across 8/6 pages (flat/grouped), still 2.18%
  larger than flat despite reducing the original grouping-only payload. Member collections
  are 964,100/824,864 bytes across 6/6 pages (14.44% smaller). First/repeat batch times:
  operands 13.7299/2.6042 versus 13.5532/2.5555 s; members 4.0932/1.7840 versus
  5.9164/1.8662 s. Keep the member cold/repeat regressions; this one-round result does not
  establish a speedup. No input-specific thresholds were added. Next check the same
  representation on Douyin before deciding whether further compacting is justified.
- `douyin-target-table-smoke.json` preserves a failed first flat trial: artifact open took
  66.9427 s, the string collection completed eight pages, and the first concurrent operand
  type request exceeded the unchanged 180-second external deadline. No grouped trial ran,
  so this provides no Douyin grouped performance/equality conclusion. Source and receipt
  files are retained, including the partial collection and failure log. Host load and
  exhausted swap were observed afterwards, but are not a proven cause of this request's
  timeout. Diagnose the flat timeout before rerunning a comparable full-operand pair;
  do not raise the acceptance timeout or select the completed string subset as success.
- Final focused target-table/cursor/replay regression run passes 112 tests in 42.26 s,
  zero skips (`target-table-focused-final.xml`), in addition to the separate two-transport
  retry. Both generated schemas check cleanly; Ruff lint/format and git diff checks pass.
  Offline sdist/native-wheel build succeeds in `target-table-dist`, with build log retained;
  archive reads verify NOTICE byte-for-byte against the repository in both artifacts.
  This is build/attribution evidence, not the pending clean-install, Windows, full-suite
  or real-workflow performance acceptance. The version remains 0.2.4 and nothing is released.
- Timeout diagnosis preserves a second unchanged full-operand failure in
  `douyin-target-table-repro.json` (first flat type call: 180.396 s) and a standalone-type
  failure in `douyin-type-timeout-stacks.json`. A diagnostic-only `timeout-probe/sitecustomize.py`
  overlay records periodic stacks outside product code: the worker remains in native type
  scanning/declaration decoding, not a blocked MCP response or concurrent string lock.
  GDB attachment was unavailable under the current ptrace restriction; its failed attempt
  is preserved, with no permission/configuration changes. The native extension hashes match
  frozen B1 exactly. One contemporaneous CPU0 frequency read was 399243 kHz; this is a
  single host observation, not a proven throttle cause. On 2026-10-28 the same read reports
  3928669 kHz before recheck and 3629661-3820306 kHz during it. Rerun the original pair with
  unchanged runtime, selectors and 180-second bound, without the diagnostic overlay.
  No query optimization or timeout relaxation is justified by the prior timeout alone.
- `douyin-target-table-frequency-recheck.json` passes the unchanged pair, all eight full
  collections and exact row/diagnostic equality; input/runtime/helper hashes stay unchanged.
  CPU0 frequency samples during the run are 3.63-3.82 GHz. This supports an environmental
  contribution to the previous timeouts, not a controlled proof of their sole cause.
  Across two queries and two repeats, flat/grouped text totals are 83,933,361/77,640,300 bytes
  and page totals 278/216, with no retries. Cold/repeat batches are 25.8178/10.8819 versus
  30.4898/15.3044 s: grouping improves payload/page count but remains slower. Keep this
  performance residual; one successful pair does not close the five-round gate.
- B2 implementation and attribution are frozen at `f44fe8d72098d67fe7dc54f3cfe18ac1bc2447dd`,
  pushed only to the development branch. CI `40581715566` is running; do not reuse B1's
  successful CI as B2 evidence. Additional public-service member/outgoing/fuzzy/empty-group
  and benchmark retry-byte accounting coverage is being checked separately before a follow-up.
- Frozen B1 fresh cache parity: `b64-{douyin,wechat,taobao}-selected-parity-input.json`
  each records one complete real-MCP operand pair with the pinned comparator, two repeats,
  four CPUs and unchanged input/runtime/helper identities. They are correctness inputs,
  not new five-round performance evidence or independently accepted comparator string sites.
  The corresponding `b64-*-selected-parity.json` files replay every product page against
  complete uncached scans of original APK bytes and compare every backend semantic field,
  row order and duplicate multiplicity. All three pass, with temporary oracle cleanup:
  Douyin 4,778 strings/115,306 type sites; WeChat 738/44,002; Taobao 2,163/56,791.
  F-Droid completes the fourth required cache-parity input in `b64-fdroid-selected-parity.json`:
  62 string and 1,772 type sites, unchanged identities, full semantic equality and verified
  cleanup. All 16 cold/repeated product collections across the four inputs now pass this
  dedicated gate. This closes the missing cache-equivalence evidence, not the overall goal.
- Downloaded the exact B1 CI source/signing artifacts into `b64-ci-source-results` and
  preserved `b64-ci-run.json`. All eight Linux/Windows Python 3.10-3.13 JUnit files each
  report 1,693 tests, zero failures/errors/skips. The bound run is b64f85c, 25 successful
  jobs including canonical distribution, Rust and stability gates, not the B2 candidate.
- CI `40581715566` is terminal failure, with one failed Windows Python 3.11 job.
  Its original JUnit is retained at `f44-ci-first-failed-win311/test-results.xml` in the
  B2 artifact directory. The owner-writer termination assertion observed a running process
  immediately before its representation reported termination. The observer now waits at
  most two seconds for exit, without killing it or relaxing production deadlines/cleanup;
  a still-live process fails. Red observer evidence: `windows-exit-observer-red.xml`
  (2 failures, 6 passes). Fresh full preparation/group/member/benchmark tests pass 137
  cases, zero skips: `exit-observer-and-member-workflows-green.xml`. The earlier
  `member-workflows-and-retry-accounting.xml` retains one incorrect test-fixture descriptor;
  corrected against the actual Smali fixture, not by changing product behavior.
- `douyin-grouped-service-profile/report.json` is diagnostic, not MCP timing acceptance.
  Full-row digests agree and identities/cleanup pass. Profiled flat/grouped type collection
  makes 139/215 cache reads and 109,877/291,453 JSON encodes respectively (concurrent strings
  may contribute counts). Grouping still calls the flat formatter on every internal chunk.
  Next reuse the same validated bounded cache-block reader before final grouped formatting;
  retain integrity/quota/cancellation checks and the unchanged public flat path. No new
  persistent cache or replacement grouping algorithm is justified by this profile.
- Follow-up `92c721f` contains only tests/ledger, not runtime changes. The first push
  received GitHub Internal Server Error; authoritative remote readback still showed f44.
  Retrying the unchanged push succeeded and started CI `40584948495`. This CI covers the
  bounded exit observer but not the subsequent grouped cache-chunk change.
- Grouped collection now reuses `ReferenceCache.read_chunk`, the existing checked reader
  before flat formatting. Decode budget, file/input identity checks, cancellation, quotas
  and spool publication stay shared with `read`; public flat `read` still formats normally.
  Internal chunks bypass the exact flat-page cache to avoid storing oversized internal
  data as public responses. Cache misses/overflow keep the existing bounded worker fallback;
  grouped responses retain their final exact byte cap. No cache schema or quota changed.
  `bounded-group-chunks-red.xml` records 15 missing-chunk failures and one test setup error
  (flat service call omitted its required offset); the setup-only retry is retained as
  `bounded-group-service-red.xml`. Adding offset=0 gives the intended flat-cache failure
  in `bounded-group-service-contract-red.xml`. First green: 175 tests. Expanded integrity,
  corruption, cancellation, duplicate/context, cache-fit/overflow and real stdio/HTTP checks:
  `bounded-group-chunks-integrity-green.xml`, 265 passes, zero skips. Both schema checks pass.
- `douyin-bounded-chunks-five-rounds.json` passes all 20 fresh-server trials, ten alternating
  pairs and 80 complete collections, with exact reconstructed rows/diagnostics and unchanged
  input/runtime/helper hashes. Four inherited CPUs, two full repeats, no retries. Medians
  in seconds, flat/grouped:

  | Workflow | First complete | Repeated complete | Startup to complete |
  | --- | --- | --- | --- |
  | string/type operands | 28.3991/28.8200 | 12.0796/13.3939 | 32.0293/32.5154 |
  | method/field concurrent | 6.9786/6.5090 | 5.7391/4.9990 | 10.7018/10.5061 |

  Per trial across both queries/repeats, operand pages fall 278/216 and text bytes
  83,933,361/77,640,300; member pages 146/86 and text bytes 44,124,280/30,710,858.
  These are tool-text bytes, not JSON-RPC wire bytes or structured-response caps. Every
  member first/repeat pair improves (first deltas -0.8782 to -0.4696 s; repeats -0.8818 to
  -0.4136). Every operand repeat is slower (+1.3143 to +2.3345 s); do not call reduced page
  count an operand speedup. Grouping remains opt-in, with this residual explicitly open.
  Peak descendant RSS is 164,147,200/164,474,880 bytes for operands and
  155,033,600/153,276,416 for members; retained temporary logical bytes remain identical
  per workflow (480,253,362 and 477,975,984). No storage or total-memory win follows.
  This is a format comparison on one changed runtime, not an isolated before/after patch
  speed ratio or a replacement for held-out/cross-platform/package acceptance.
- `douyin-bounded-chunks-service-profile/report.json` confirms the redundant flat formatter
  is absent from warm grouped collection. Grouped JSON encoder calls fall from 291,453
  in the preserved pre-change diagnostic to 125,556, and cache reads from 215 to 197;
  full ordered row digests still agree with flat, identities stay unchanged and cleanup
  succeeds. These are profiler observations, not acceptance speed ratios. Remaining
  grouped costs include per-site grouping and more cache reads than flat (139), so the
  measured operand latency residual has not been waved away by a lower encode count.
- The same changed runtime is committed/pushed only to the development branch as
  `aca6b27` (`perf: group validated cache chunks without flat formatting`). Repository-wide
  Ruff/format and diff checks pass. New CI must cover this runtime rather than borrowing
  `92c721f` results; current `aca6b27` CI `40586951801` is running. Earlier CI `40584948495`
  is now terminal success in all 25 jobs, including the previously failing Windows source
  cell; it covers the exit observer fix, not the later cache-chunk runtime change.
- Held-out `fdroid-bounded-chunks-five-rounds.json` passes 20 fresh-server trials, ten pairs
  and 80 full collections, unchanged identities, four CPUs and no retries. Flat/grouped
  operand first/repeat/startup medians are 0.9448/0.9600, 0.1647/0.2156, 1.7957/1.8239 s;
  member medians are 0.2528/0.2673, 0.1280/0.1519, 1.1026/1.1096 s. Every first/repeat pair
  is slower here (operand repeats +30.8 to +58.2 ms, members +19.5 to +27.2 ms).
  Operand pages drop 8/6 but text bytes increase 1,291,212/1,319,304; member pages stay 6/6
  and text bytes drop 964,100/824,864. This preserves the small-input grouping overhead and
  payload regression rather than selecting only the favorable large-member workload.
  B2 has a verified useful opt-in case, not universal speed/size superiority; final
  cross-platform/package acceptance and the explicit residual assessment remain open.
- `candidate/b64-source-bridge.json` binds 210 evidence/input/helper files using
  `audit_b64_source_bridge.py` in the B1 artifact directory. All four original-byte decoder
  reports differ from frozen b64 in exactly `reference_cache.py`; all scanners, schemas,
  native binary and worker paths are byte-identical. Their 160 product decoder collections
  pass. Fresh b64 cache-parity reports match that exact runtime and pass all 16 collections.
  The Douyin comparator's 20 failed string collections remain failed. The bridge also checks
  b64 CI's exact commit/25 successful jobs and all eight 1,693-test source JUnit files with
  zero failures/errors/skips. This establishes source/evidence continuity for unchanged
  decoding plus separately retested caching; it does not relabel old timings as current
  or mark B1 accepted. Original evidence and helper hashes are actually rechecked.
- `candidate/b64-holdout-revisions-cpu{2,4}.json` refreshes the published-v0.2.4 versus
  frozen-b64 comparison, with unchanged input/runtime/helper hashes. Each passes 40 fresh
  trials, 20 alternating pairs and 100 full result/diagnostic comparisons. No first,
  repeated or startup median crosses both existing regression thresholds. Seconds,
  baseline/candidate:

  | CPU | Query | First complete | Repeated complete | Startup to complete |
  | --- | --- | --- | --- | --- |
  | 2 | string | 0.1409/0.1448 | 0.0239/0.0224 | 1.0324/1.0023 |
  | 2 | method | 0.2476/0.2454 | 0.1145/0.1138 | 1.1064/1.1142 |
  | 2 | field | 0.1343/0.1366 | 0.0206/0.0212 | 0.9792/0.9941 |
  | 2 | concurrent | 0.2818/0.2786 | 0.1291/0.1274 | 1.1184/1.1344 |
  | 4 | string | 0.1417/0.1468 | 0.0244/0.0232 | 0.9820/0.9808 |
  | 4 | method | 0.2453/0.2480 | 0.1147/0.1144 | 1.0997/1.0886 |
  | 4 | field | 0.1356/0.1355 | 0.0221/0.0205 | 0.9786/0.9707 |
  | 4 | concurrent | 0.2577/0.2487 | 0.1308/0.1249 | 1.0924/1.1033 |

  These small holdout deltas are compatibility/regression evidence, not an unconditional
  performance win. The current large-input refresh uses the same four scenarios, five
  alternating pairs, two repeats and original budgets; no runtime edits during timing.
- `candidate/b64-taobao-revisions-cpu{2,4}.json` each passes 40 fresh-server trials,
  20 alternating pairs and 100 complete result/diagnostic comparisons, with unchanged
  identities. No first/repeat/startup median crosses both regression thresholds. Seconds,
  published baseline/frozen b64:

  | CPU | Query | First complete | Repeated complete | Startup to complete |
  | --- | --- | --- | --- | --- |
  | 2 | string | 3.7971/0.6430 | 1.0204/0.2268 | 5.3964/2.2222 |
  | 2 | method | 3.2121/3.2704 | 2.7569/2.8656 | 4.7458/4.9003 |
  | 2 | field | 0.3063/0.3027 | 0.0452/0.0451 | 1.9105/1.8498 |
  | 2 | concurrent | 3.4987/3.4142 | 2.9248/2.8432 | 5.0556/5.0170 |
  | 4 | string | 3.8462/0.6669 | 1.0108/0.2330 | 5.3210/2.1055 |
  | 4 | method | 3.3336/3.1902 | 2.8301/2.7259 | 4.7972/4.6740 |
  | 4 | field | 0.3063/0.3069 | 0.0428/0.0446 | 1.7244/1.7521 |
  | 4 | concurrent | 3.4413/3.2237 | 3.0731/2.7860 | 4.9019/4.6793 |

  Every string first/repeat pair improves at both budgets. Four-CPU concurrent first/repeat
  pairs also all improve; two-CPU method/concurrent deltas are mixed, so do not generalize
  that win. Remaining refresh is predeclared unchanged: WeChat then Douyin, two then four
  CPUs, the same four complete workflows/five alternating rounds/two repeats and budgets.
  All original receipts remain separate, including the earlier noisy Douyin post-fix sample.
- The four predeclared WeChat/Douyin revision matrices also pass on frozen b64:
  `candidate/b64-{wechat,douyin}-revisions-cpu{2,4}.json`. Each has 40 trials, 20 pairs,
  100 full-result/diagnostic comparisons and unchanged identities. Together with Taobao
  and the holdout, all eight current matrices now cover 320 fresh-server trials, 160 pairs
  and 800 complete collections. `candidate/b64-revision-gate-summary.json`, generated by
  `summarize_b64_revisions.py`, rechecks all 320 operation-sidecar hashes/sizes, original
  APKs, runtime/helpers and paired complete-result digests (464 file bindings total).
  Every one of its 32 input/CPU/workflow cells passes the >5% AND >100-ms median regression
  gate for first/repeated/startup completion; first-useful-page checks also pass. The summary
  preserves every paired delta, first-page time, page/retry count, peak process RSS and
  retained temporary bytes separately. This is the published-baseline regression gate,
  not current comparator parity or the entire B1 acceptance.
  Current frozen-b64 repeated string medians versus published v0.2.4 are 0.1100/1.4799 s
  (WeChat two CPUs), 0.1151/1.4601 (four), 0.4902/1.6928 (Douyin two), and 0.4909/1.6642
  (four). Every paired large-input string first/repeat improves; no holdout speedup claim.
  The original noisy post-fix Douyin receipt and the failed pre-fix fifteen-pair concurrent
  sample remain preserved, not overwritten or pooled across different runtimes.
- B2 CI `40586951801` is now terminal success, all 25 jobs bound to exact commit
  `aca6b2740a318f90894feb34f74b78bc711180b6`. Saved `aca-ci-run.json`, full logs and all eight
  source/signing artifact directories under the B2 evidence root. Each Linux/Windows
  Python 3.10-3.13 JUnit reports 1,777 tests, zero failures/errors/skips. Full logs confirm
  both canonical-sdist and exact installed-wheel suites pass in every distribution cell;
  no skip is permitted by fixture acceptance. All eight cells use canonical sdist SHA-256
  `06cddf938f514e10c053e83495b443a5298af86e0cea5f6576bc9cca0942b645`.
  `aca-ci-package-readback.json` hashes all eight downloaded build artifacts and checks
  NOTICE byte-for-byte in every sdist/wheel. Rust, signing and stability jobs also succeed.
  This closes current B2 cross-platform/package gates, not its documented performance
  tradeoffs or the remaining B1 comparator-refresh dependency; nothing was published.
- Remaining B1 measurement is explicitly frozen: use b64 helpers/runtime and the pinned
  comparator on holdout, Taobao, WeChat and Douyin at two/four CPUs, five alternating
  rounds and two complete repeats, scenarios full_string/full_type/full_operands and
  unchanged 768-MiB expansion/8192-MiB session limits. Write fresh
  `candidate/b64-<input>-operands-cpu<2|4>.json` receipts. Keep the independently established
  Douyin comparator string failure excluded from equal-correctness ratios; do not repair
  comparator data or silently omit its failed semantic cell. B1's current baseline gate
  is closed, while this current-runtime comparator refresh and final batch summary stay open.

### B1/B2 final acceptance, 2026-10-28

`candidate/b1-b2-final-acceptance.json` under the B1 evidence root supersedes the
pending batch verdicts above, without replacing their receipts. Generated by
`close_b1_b2.py --output <fresh-path>`, it rehashes 1,102 evidence/source/package files,
rechecks all eight comparator matrices and both B2 format matrices, and binds B1
`b64f85c5e555ea27e9dc5eed6b058008a777d07c` and B2
`aca6b2740a318f90894feb34f74b78bc711180b6` separately. Verdict:
`accepted_with_documented_residuals`; overall goal remains incomplete.

- Fresh comparator matrices: four inputs, two/four CPUs, five alternating rounds,
  three workflows, two repeats; 240 fresh-server trials and 640 independently decoded
  complete collections. All 320 product collections pass. Comparator type collections
  pass; all 40 Douyin string collections retain the same one-extra-site failure.
  Douyin string and combined operands are excluded from equal-accuracy performance claims.
- Every one of the 40 paired type repeats improves. Four-CPU repeat medians in seconds
  (product/comparator): F-Droid 0.1484/0.2672, Taobao 4.5012/8.6518, WeChat
  3.6129/5.8488, Douyin 9.5528/15.0514. First type/startup costs still trail on some
  inputs; these remain B4 work, not hidden by repeat timings. The summary retains
  first useful page, first/repeated/startup completion, paired deltas, pages/retries,
  process/client RSS and temporary logical/allocated bytes separately. No p95 claim.
- B1.1-B1.5 are covered by the frozen source suites (operand/string semantics,
  native/fallback equivalence, no-index routing instrumentation, cache lifecycle and
  byte paging), real stdio/HTTP tests, original-byte oracle collections and fresh
  cached/uncached parity. B1.6 binds the API scope audit, all 32 baseline regression
  cells and exact-commit Linux/Windows source/distribution/signing/Rust/stability CI.
- B2 preserves flat defaults and complete evidence; its signed cursor, bounded pages,
  resume/mismatch/expiry, cancellation and transport tests pass on its own final runtime.
  Large member-reference collection improves bytes, pages and latency together.
  Grouped operand repeats and small inputs can be slower; grouping remains opt-in.
  These are accepted tradeoffs, not a blanket performance-parity claim.
- Source CI is 25/25 successful jobs for each frozen commit. B1 source cells have
  1,693 tests each; B2 has 1,777 each, with zero failures/errors/skips. Exact-package
  and attribution readbacks remain linked in the source bridge and B2 package receipt.
  Earlier failed CI, concurrency regressions and comparator errors remain preserved.

### B3 pre-implementation decision, 2026-10-28

Reuse `asc_mcp/sessions.py::AnalysisSession/SessionRegistry` and
`server.py::load_artifact/close_artifact` at pinned upstream `848c711f` as the port
source. Keep one artifact handle for archive metadata and lazy DEX preparation. Adapt
the registry into the existing `DexSessions` ownership, reservation, pin/close/expiry
and cancellation mechanism; do not create a second independently expiring registry.
Keep verified immutable content identity rather than upstream's size/mtime-only get.
Record the actual copied functions and modifications in NOTICE as they are incorporated.

Advertised surface decision: the new artifact profile exposes `load_artifact`,
`close_artifact`, status and focused handle-based metadata/discovery/reference/source
tools. Port upstream tool signatures where semantics agree; exact descriptors, broad
versus operand type scopes, bounded continuations and optional Java stay explicit.
Each of the current 24 DEX operations remains reachable through a focused tool;
do not drop uncommon capabilities merely to reduce the tool count. Separate member,
string and type reference contracts instead of repeating the current giant selector.

Migration: retain all existing path/session tool names and argument/default semantics
as callable adapters. `DROIDASC_MCP_TOOL_PROFILE=legacy` advertises the existing tool
surface; `artifact` advertises the new focused surface and omits legacy duplicates
from tools/list. The artifact profile becomes the new default only after B3 model and
compatibility gates pass. Existing resource/prompt URIs remain valid; add handle links
and update advertised guidance consistently with the selected profile. Never advertise
both complete surfaces together by default.

Before any B3 runtime changes, freeze baseline model tasks for artifact inventory,
manifest-to-code navigation and resource reads on real APKs. Run the unchanged B2
runtime and pinned comparator, then the candidate with identical provider/model
settings and task prompts. Retain failures and report task success, actual calls,
tool errors/retries, schema token measurement method and end-to-end time. Offline
judges receive expected values; model prompts receive only user requests and paths.

B3 baseline execution setup:

- `scripts/model_workflow_tasks.json` freezes four tasks and three rounds per product:
  F-Droid and Douyin identity/manifest/DEX/ABI/signing inventory, F-Droid launcher-to-DEX
  navigation, and complete asset inventory plus one XML asset read. Resource preflight
  found no `res/xml/` directory in the optimized F-Droid APK, so that unexecuted task
  was replaced with a real asset read before the frozen baseline. No expected values
  or oracle output enter any task prompt.
- `scripts/benchmark_model_workflows.py` uses existing Codex authentication and real
  stdio MCP, not a scripted provider. It disables shell/web/apps/plugins/memory and
  multi-agent tools, uses an empty temporary working directory, suppresses project
  documents, and configures only the product under test. Raw JSONL, stderr, source/input
  hashes, tool-call/error/retry counts, usage and cleanup are saved per trial. Three
  focused harness tests pass. `turn.completed` remains `pending_offline_judge`, not success.
- Provider preflight is preserved in `artifacts/competitor-gap-b3-20261028/provider-preflight.json`:
  inherited local proxy refused connection; current configured Claude upstream returned
  HTTP 403 `SUBSCRIPTION_NOT_FOUND`. Codex's existing ChatGPT login successfully ran
  `gpt-6.1-sol`; use that model with medium reasoning for every baseline/candidate cell.
  No credential or global provider configuration was changed.
- Two inventory pilot trials under `baseline/` completed actual MCP workflows and
  cleaned up. Both used six product calls; they establish access, not final task grades
  or latency superiority. A model-catalog refresh timeout remains in stderr even though
  model execution succeeded. Formal paired runs live separately under `frozen-baseline/`;
  the final task/harness files are copied byte-for-byte to `frozen-harness/`.
- Token methodology: full MCP surface includes output schemas and is not a model billing
  estimate. Separately tokenizing only tool names/descriptions/input schemas with the
  same `o200k_base` encoding gives 6,762 product versus 4,852 comparator tokens; server
  instructions add 1,347 versus 273. Actual Codex cumulative usage stays in raw events.
  Do not present the larger full-surface count as tokens necessarily sent to the model.
- Offline oracle generation uses original ZIP metadata, Android build-tools 35.0.0
  `aapt2`/`apksigner`, and Androguard 4.1.4 original-byte DEX decoding, with original-input
  and oracle tool hashes. It runs outside timed model tasks and is never an MCP tool.

Reproduce one frozen baseline cell (fresh output required; repeat all four tasks at
rounds 0-2, alternating product order each round):

```sh
uv run --offline --no-sync --with ./artifacts/aimard-asc-mcp --with tiktoken python scripts/benchmark_model_workflows.py --task fdroid_inventory --implementation ours --round 0 --output artifacts/competitor-gap-b3-20261028/fresh-fdroid-ours
```

### B3 baseline result, 2026-10-28

All 24 declared real-model trials are now terminal and independently reviewed:
four tasks, three rounds, two products, alternating order in round 1. Both products
complete all 12 tasks correctly. `artifacts/competitor-gap-b3-20261028/baseline-review.json`
binds 212 files and records each response, tool count, error, usage and paired timing.
The original `round0-review.json` remains separate. Original inputs, runtime and
task/harness hashes stayed unchanged; every trial left no surviving owned processes.

| Task | Product/comparator median seconds | Product calls by round | Comparator calls by round |
| --- | --- | --- | --- |
| F-Droid inventory | 56.2429 / 59.1521 | 7, 5, 6 | 4, 6, 6 |
| Douyin inventory | 66.4095 / 57.1263 | 4, 8, 6 | 4, 6, 6 |
| Manifest to exact method instructions | 67.3654 / 85.1539 | 7, 9, 7 | 8, 8, 8 |
| Asset inventory and full XML read | 57.7487 / 56.0006 | 6, 5, 4 | 4, 4, 4 |

This baseline does not show a universal capability or latency deficit. Product has
74 product calls versus 68, two recovered tool errors versus zero, and a larger input
contract/instruction surface. Product is faster in every paired launcher-to-code trial;
comparator is faster in every paired Douyin inventory trial. Asset timing is mixed.
Keep all three samples and provider/catalog latency warnings; no p95 or population-wide
speed claim follows from these small task samples.

The two product errors give concrete B3 routing targets, not reasons to weaken limits:
the model supplied a 1-MiB max_bytes value to a 128-KiB-bounded entry reader, then corrected
it; another inventory run chose full manifest component validation, encountered duplicate
activity names in Douyin, then recovered metadata from XML. Port the competitor's unified
summary workflow and narrower input contracts; retain byte bounds and explicit duplicate
component diagnostics. The task prompts and offline expected answers remain unchanged.

Offline review checked complete DEX/ABI/certificate sets, all 40 method opcodes/offsets
and operands, enabled versus disabled launcher declarations, and exact original XML asset
text. Android apksigner was run at default, maximum SDK 27 and maximum SDK 23 to cover
both rotation-era certificate fingerprints; these offline verification results were not
fed to the model or confused with either product's inventory-only claims. Preserve the
first oracle parser failure (`offline-oracle.json`, aapt2 emits minSdkVersion rather than
sdkVersion) and the corrected successful `offline-oracle-sdk-label-fixed.json`.

Preserve accepted B2 in the clean detached worktree
`artifacts/competitor-gap-b3-20261028/b2-baseline-frozen` at `aca6b27`, including the
byte-identical native binary. Its runtime files match all 12 product trial fingerprints.
The evaluator/tasks are separately frozen under `frozen-harness/`; installed measurement
dependencies were tiktoken 0.14.0, MCP 2.2.0, Pydantic 2.13.5 and psutil 7.2.2.
The next work is product implementation, not another baseline expansion. B3 is not
accepted until the port, compatibility/lifetime tests and same-task candidate comparison
pass; B4-B6 and publication remain outside this completion claim.

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
