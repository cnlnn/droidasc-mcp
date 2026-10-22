# 0.2.x incremental completion goal

Status: active. On 2026-10-23 the maintainer superseded the replacement-v0.3.0 release
plan: withdraw the old releases now, then publish accepted increments as v0.2.3, v0.2.4
and subsequent 0.2.x versions. The full performance, workflow/source-comparison, accuracy
and cross-platform canonical-package objectives remain open across those increments.
This checklist mirrors the full requested completion objective; workflow
completeness and ergonomics are mandatory criteria, not follow-up work.
The four authorized old releases/tags were withdrawn after backup verification. No new
release, tag or main merge is allowed before that increment's complete acceptance passes.

## Competitor workflow closure

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
  The next unused version is 0.2.3. Remaining performance/workflow deficits stay explicit
  in this overall goal; a patch release does not mean comprehensive competitor superiority.
- [ ] All Linux/Windows Python 3.10-3.13 suites pass without skipped tests; real stdio/HTTP,
  signing, Rust and stability acceptance pass on the exact final commit.
- [ ] Clean source and native-wheel acceptance pass on Linux and Windows, using the exact
  same canonical release sdist; inspect installed and archive versions as the selected 0.2.x.
- [x] Back up existing v0.3.0, v0.4.0, v0.4.1 and v0.5.0 release metadata/assets and Git refs.
  Local backup: artifacts/release-renumber-20261022/backup; all asset digests verified.
- [x] Withdraw the four old releases/tags now, preserving v0.2.2 and earlier versions.
  Completed 2026-10-23; GitHub readback confirms v0.2.2 is latest and the four tags are absent.
- [ ] Only after an increment's acceptance: fast-forward main and publish its next 0.2.x tag
  using exact successful CI artifacts. Never reuse a published patch version or roll back code.
- [ ] Read back main/tag/release target, latest flag, asset versions and server/local SHA-256;
  verify withdrawn versions are absent and the worktree is clean before marking complete.

The active goal and this checklist must not be marked complete merely because a subset of
performance tests passes. Priority: large-APK startup/ZIP memory, workflow
closure and matched accuracy/performance receipts. Each selected increment then requires
unified cross-platform packaging and release acceptance. Candidate branch commits are allowed
for CI, not main/tag/release publication before that increment's gates pass. The original
all-gap completion goal stays active after an intermediate patch is published.

## In-progress evidence, 2026-10-22

Update, 2026-10-23:

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
