# aimardcr/asc-mcp: source-backed comparison

## Current increment, 2026-10-31

W2 corrects a measurement bias before another cache rewrite. Timing-v2 performed
two synchronous RSS process-tree walks per page, excluded from individual call
durations but included between pages in whole-batch timing. The default-flat
product needs 73 pages per batch versus 12 comparator pages. Timing-v3 removes
only these redundant diagnostic walks, retaining periodic resource enforcement,
external call deadlines and cleanup. Old receipts remain historical, not
arithmetically adjusted.

With the unchanged W1 `b325c012` runtime and fixed comparator `848c711`, a fresh
six-server/36-complete-collection v3 run passes sealed original-byte truth and
current provenance/continuation replay. Second-warm medians are 4.2771/5.0342 s
(product/comparator): this cell now favors the product by about 15.0%. The old
8.31% result is not evidence that the product is still behind on this cell.
This refresh changes the observer, not product performance. The first startup/open
window partially overlaps a disclosed preparation probe; all query/warm batches
start after it finishes. No startup causal improvement is inferred.

An independent one-source byte-sizing candidate passes the preset prototype
screen, with 1314 equal page attempts and second-warm median 4.7029 -> 4.3041 s.
Its final committed-runtime A/B fails the original screen: second warm regresses
12.34%, first complete 3.84%, despite complete data equality. This does not isolate
a causal code regression, but it does not justify adoption. The sizing change is
withdrawn at `99d51aa`, restoring every W1 runtime byte. Only the corrected v3
harness and compatibility regressions remain. Final CI 41176309158 passes all
25 jobs and 24 source/package suites of 2167 tests without failures, errors or
skips. Prototype and final within-product times are not combined with either
old or fresh competitor ratios. Evidence is under
`artifacts/competitor-gap-w2-20261031/`. W1 observations below retain timing-v2
scope; published v0.2.5 is unchanged.

A single bounded prepare-only diagnostic completes with unchanged input/runtime
identities and clean owned processes/temporary files. Its profiled preparation
takes 4.5953 s; several cumulative entries exceed that wall time and include
background-thread frames. This is not an additive cost budget or a measured
SQLite share. The source audit finds the useful streaming, hash/copy fusion and
bounded prefetch already present; no new safely removable full-input pass or
high-yield drop-in competitor function is established. Startup/storage remains
a scoped tradeoff, not a reason to weaken identity, CRC or ownership checks.

v0.2.5 is published at 87b3630; subsequent development is separate. G7's compact
artifact inventory is accepted at eb8159a with CI 40787653294, all 25 jobs and 1975
tests per source/canonical-sdist/exact-wheel suite, plus final real stdio/HTTP checks.
The pinned comparator remains 848c711f1d80a1c2577283f1fa5f475ff734aa40 for these
comparisons. See GOAL_02X.md and VALIDATION.md for the current ledger; sections below
retain historical runtimes, measurements and pre-reuse statements.

Accepted W1 candidate `b325c012` addresses the diagnosed per-row client schema-reference
cost without another cache, weaker validation or a format-default change. It
locally expands two nonrecursive leaves; all definitions, input records and
business output fields remain. Final revision A/B warm median is
5.97930 -> 5.48055 s (-8.3413%), with 36 complete collections and 1314 equal
page attempts. The separate fresh pinned comparison checks another 36 complete
collections against sealed original-byte truth: preset aggregate warm median is
5.47315/6.20615 s (-11.8109%). This replaces the historical G8 +6.86% aggregate
result for this cell, not every workload or warm phase. In the second warm repeat
the comparator wins all three rounds: product/competitor medians 5.5301/5.1056 s
(product +8.3144%). Open is slower (3.2393/0.556 s), while process-to-first-complete
favors the product (11.068/21.1063 s). Private temporary storage remains about
478 MB versus zero observed, despite lower sampled server RSS.

Eight actual baseline/final stdio/HTTP fixture cells retain strict SDK validation,
complete pagination, provenance and cleanup. The schema tradeoff is explicit:
legacy tool metadata +10260 bytes, artifact +22572 compact decoded JSON bytes;
some invalid-result SDK schema-context dumps also grow. Validation constraints,
rejection reasons/paths and product error fields remain, not identical schema
representations or full SDK dump strings. The common comparison environment is
verified zero-install path composition, not ordinary-pip acceptance. Existing CI
40922087963 passes 25/25 jobs, eight source and sixteen canonical-sdist/exact-wheel
suites, each 2162 tests without failures/errors/skips. The 12 CI ZIP digests and
package identities pass. Combined closure is
`artifacts/competitor-gap-warm-residual-20261030/W1-acceptance.json`, SHA-256
`5be9b0cf2600cb29bd7a356371204b14cb323f0350c3c6cf480ee4c9e86ec8e7`.
This finite batch is accepted development, not a new release or elimination of
every observed comparator advantage. VALIDATION.md records component hashes.

G17 closes the selected larger-APK application-member handoff without a new runtime
change: 102 complete public calls over stdio/HTTP, 36 complete paginated collections,
and independent scans of 69 original DEX files/73,977,365 instructions agree on all
selected outgoing, incoming and field sites. Twelve exact Smali collections cover
six distinct methods with matching flags/opcodes/member operands. This is bounded
workflow evidence, not universal correctness or a new latency claim. D1 now accepts
normal development dependency adoption of the verified annotation/raw-type fixes,
separate from published v0.2.5. No further corpus goal is implied by this acceptance.

The dependency is `0.1.2.post3+sourcefixes.2` at immutable source
`a6f96b864cc317116cd38af143c63fe82b149099`, subdirectory
`third_party/droidasc_sourcefixes`. Candidate `cdb4f35` passes CI 40908697104:
25 successful jobs and 24 Linux/Windows Python 3.10-3.13 locked source/package
suites, each with 2030 tests and zero failures/errors/skips. Separate Linux Python
3.13 CI 40915579504 (`05c5088`) proves ordinary pip's complete resolver in two fresh
venvs, using those exact canonical sdist/native-wheel artifacts without seeds,
`--no-deps` or overlays. Both PEP 610 identities match the pinned SHA/subdirectory;
80 engine/23 original dadguard/69 MCP source identities and five regressions per
consumer pass. This ordinary-pip claim is Linux-only, not a Windows pip claim.

The normal locked-uv clean-clone path also passes with its existing ordinary cache,
not a cold cache. Eight real stdio/HTTP plain/metadata collections preserve the G15
source bytes, all 656 ordered metadata links and both original Throws annotations.
Evidence is under `artifacts/competitor-gap-g17-20261029/`: `adoption-ci/ci-acceptance.json`,
`adoption-pip-ci/acceptance.json`, `adoption-uv-normal-cache/receipt.json` and
`adoption-uv-workflows/verification.json`. The independent combined closure is
`artifacts/competitor-gap-g17-20261029/D1-acceptance.json`, SHA-256
`c4eb9eafa0a2409b5ef180ad91638ab9f68375b8e512ee0b9c3ac4d57e13b63f`.
Local TLS/download failures remain retained;
the accepted remote pip result does not rewrite them. Published v0.2.5 assets remain
unchanged and the development increment is unreleased. The checkpoint-specific
G10-G16 integration statuses below are historical, superseded by D1 for default
dependency adoption only; no public-upstream-PR or overall parity claim is added.

Historically, G8 checks 24 serial trials / 144 complete original-byte-validated collections.
Its Douyin default-flat repeated concurrent batches are about 6.86% slower (7.0980 versus
6.6423 s median); the already adopted upstream-derived grouped option wins its matched
cell (5.9162 versus 6.6485 s). First complete batches favor the product in both formats.
WeChat repeated medians are 3.6886/3.9304 s flat and 3.7225/3.8728 s grouped.
Separate format cells, current-host thermal override and two APKs do not establish
universal parity, causal format speedup or a before/after G7 optimization ratio.

G9's cached-page diagnosis points to client validation/pagination rather than a
missing scan cache; no further cache rewrite is adopted. G10's manifest-to-source
probe identifies a genuine current source-output gap: two original Throws annotations
are omitted by the installed ASC/dadguard path but shown by the comparator. Original
DEX bytes independently confirm them. A two-line isolated upstream lazy-directory fix
passes focused tests, public CLI and complete real-MCP metadata/token-span verification.
It is not integrated into the installed dependency or published release. The unequal-
source pilot cannot be used as an equal-correctness latency comparison. Receipts live
under artifacts/competitor-gap-g{7,8,9,10}-20261029.

G11 reuses the existing bounded public-CLI complete-source snapshot across session
pages. This removes repeated plain-source rendering without adopting another scanner,
decompiler or resident APK worker. Its final runtime passes 12 paired stdio trials,
24 complete collections equal to original-APK public CLI and two complete HTTP
readbacks. F-Droid five-page first/repeated medians change from 1.0565/1.0717 to
0.2530/0.0349 seconds on the current host. Commit 3709bf2 passes all 25 jobs in CI
40796945147, with 1992 tests per source/canonical-sdist/exact-wheel suite. Closure
under artifacts/competitor-gap-g11-20261029 explicitly records the later oversized-
line error's two extra optional provenance fields; G12 restores exact worker errors.

G12 reuses the existing ASC metadata renderer and ordered token-link results, not a
new decompiler. Its isolated runtime passes 12 paired real-MCP trials, 24 complete
stdio collections and two complete HTTP readbacks, preserving all source bytes,
page diagnostics and global Unicode token spans. F-Droid's five-page first/repeated
medians change from 0.7985/0.7781 to 0.2413/0.0779 seconds; WeChat's one-page first
call is slightly slower (0.1299/0.1328), while repeated access is 0.1060/0.0089.
This is a paired current-host adapter optimization, not an equal-correctness
competitor comparison. Unpaged original-byte ASC output verifies pagination, not
independent decompiler correctness. Commit 5a96ea6 passes all 2013 local tests and
CI 40801161988, all 25 jobs: 2013 tests per source/canonical-sdist/exact-wheel suite,
with exact package/runtime identities checked. Four further adopted-runtime stdio
collections match the prototype bytes and complete pages. g12-acceptance.json
records development acceptance and unchanged published assets. G10's distributable
annotation integration and other residuals remain open. Its two-line upstream
contribution and generated-fixture tests are prepared locally as G13; the installed
dependency is unchanged. Neither increment establishes overall competitor parity.

G13 also builds an isolated `0.1.2.post3+annotations.1` dependency from the official
lock-pinned sdist rather than the Git tree, preserving all released dadguard bytes.
The official sdist, wheel and installed dependency match across all 80 Python files;
the local wheel changes only the two lazy-directory lines. Normal wheel installations
with the accepted G12 native wheel pass 16 complete plain/metadata collections over
stdio/HTTP, restoring exactly the two annotations and all 660 ordered token links
with shifted global spans. Engine-bound input IDs are independently reconstructed
before cross-version comparison. Installed generated-fixture tests fail 2/4 before
and pass 4/4 after. This is Linux Python 3.13 package-integration evidence, not default
dependency adoption, cross-platform changed-dependency acceptance or a new release.
Fresh main/dev/open-PR source review finds no corresponding annotation fix in those
checked sources. The public contribution awaits permission; other catch-up work
continues. Receipts: artifacts/competitor-gap-g13-20261029/package-integration/
integration-verification.json and source-review/review.json.

G14 follows actual source tokens into method Smali and complete incoming/outgoing/
field references over both transports. All 343 method/field tokens match independent
original DEX pools/definitions, 57 declarations round-trip through the outline and
all nine selected query sites match complete sequential decoding of 1,692,420 original
instructions. However, 25 additional class tokens use abbreviated display names or
`super` as identities (`LString;`, `Lsuper;`, etc.). This is an open source-navigation
quality gap in our installed ASC path, not evidence that the comparator implements
these extra class-token categories. G15's separate candidate below reuses original
upstream type data. Evidence: artifacts/competitor-gap-
g14-20261029/g14-probe.json. No product/default/release change is made by the probe.

G15 accepts that separate local upstream adaptation at `140b05c`, based on G13's
annotation contribution. Field/return/argument types reuse neighboring original
tokens; the existing ASC Writer-extension pattern now also retains raw new-array/
filled-array types without changing released dadguard files. The final normal wheel
`0.1.2.post3+sourcefixes.2` corrects 21 original class identities and removes four
keyword links, leaving 635 other links/global spans and all source bytes unchanged.
The first sourcefixes.1 candidate missed one array link; its rejected oracle run and
correction are retained. An independent original DEX type/member/selected-array-operand
check finds no invalid remaining class links on the selected F-Droid class. Eight
complete stdio/HTTP collections and 16 installed-fixture cases pass; the earlier
normal annotation-only wheel fails eight of those cases. These results do not adopt
the dependency or claim competitor/performance parity. Receipt:
artifacts/competitor-gap-g15-20261029/g15-acceptance.json. G16 extends the same normal-
package path to manifest-discovered application classes in the larger APK corpus.

G16 completes that scoped check on WeChat and Douyin: 32 complete ordinary/metadata
source collections over both transports, unchanged official-engine source bytes,
460 independently valid member identities and 356 class identities. The adaptation
corrects eight more types and removes 42 keyword links, preserving every member/string
link and the other class links/spans. Original DEX hashes use the explicit logical
`dex_entry` to physical `container_entry` mapping. Evidence:
artifacts/competitor-gap-g16-20261029/g16-acceptance-final.json. This is two selected
application classes and normal installed Linux wheels, not default dependency adoption,
all-class source semantics or performance/competitor parity. G17 next follows selected
source members into full exact-reference workflows on this corpus.

## v0.4.1 cold-query investigation, 2026-10-22

The competitor's main was rechecked at `848c711f1d80a1c2577283f1fa5f475ff734aa40`.
Its [code-item scanner](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/core/findrefs/scan/code_item_scan.py)
resolves member IDs before scanning. Dense cases combine translated opcode and high-ID byte
masks as integers, then verify candidate IDs. The
[instruction locator](https://github.com/aimardcr/asc-mcp/blob/848c711f1d80a1c2577283f1fa5f475ff734aa40/asc_mcp/core/findrefs/locator/insn_locator.py)
maps candidates into code items and verifies byte patterns. This avoids constructing every
instruction object, but byte-pattern candidates are not equivalent to exact instruction
boundaries. The independently confirmed 97 extra field sites below remain a correctness
reason not to adopt that implementation verbatim.

Our optimized scanner uses the pinned decoder's DEX-version-specific opcode/format table
to walk every exact instruction boundary, including switch/array payloads. Fixed instructions
need no object allocation until an operand is emitted; member-ID decisions and decoded pool
strings/types/prototypes are cached only inside that isolated query. Method sorting lazily
constructs complete descriptors while retaining exact order and duplicate detection. Ordered
class identities are reused rather than decoded again. Every definition's prototype is still
validated even when its name is unique and no reference matches. No worker is retained, no persistent
compiled-code cache is introduced, and no competitor implementation is copied.

The frozen v0.4.0 source was retained for alternating fresh-JVM comparisons with
`scripts/benchmark_reference_scan.py`. Every reference row, ordering, resolution diagnostic
and scan counter must match, not merely a first page or total. The Taobao input is the same
12-DEX APK and SHA-256 recorded below: 606,974 methods and 12,495,817 instructions, with
24,461 exact method sites and 332 exact field sites. A separate Java oracle compares our
cursor and cached member descriptors with dexlib2's unfiltered public iterator/pools.

JFR identified repeated UTF decoding and instruction iteration as useful optimization
targets. The suspected duplicate ZIP-entry loading was rejected: the pinned container already
caches its entries. An alternating two-round `-XX:TieredStopAtLevel=1` experiment also failed
to establish a method-query improvement and was not enabled in production. Limiting the JVM
to two active processors also regressed both method rounds and was rejected. These rejected
approaches are not represented as performance wins.

Fresh stdio trials alternate our server and the unchanged pinned competitor, exclude server
initialization and the separate artifact/session-open call, and exclude RSS-sampler shutdown
from both query timings. Each first query starts a fresh worker/JVM; OS caches are not dropped.
The comparison is operation-specific: the competitor returns caller groups whereas we return
instruction sites with complete scanning diagnostics. This is not a claim that all operations
or machines are faster. Local load varies, so ranges and medians must accompany speed claims.
The final release notes link the successful candidate CI gate; historical evidence below
does not authorize the v0.4.1 release.

## Current source audit: 2026-10-22

The v0.4.0 implementation maps all 25 tools, two resource templates, three prompts and
87 non-context parameters at the pinned commit to equivalent workflows. See the exhaustive
[source audit](COMPETITOR_API_AUDIT.md) and its AST inventory guard. New structural views,
decoded-body search/disassembly, source-token links, DEX 041 imports, JVM inventory/diffs,
resource byte paging and opt-in candidate values close the remaining functional categories.
This is workflow parity, not identical tool names, universal speed superiority or release
acceptance. The measurements and development receipts below are historical; only the fresh
v0.4.0 feature-frozen gates in VALIDATION.md authorize its release.

Reviewed: 2026-10-21. Competitor commit:
[`848c711f1d80a1c2577283f1fa5f475ff734aa40`](https://github.com/aimardcr/asc-mcp/tree/848c711f1d80a1c2577283f1fa5f475ff734aa40).
Our original baseline was `8cab43f4159ddc7252322f12a831dd98146d88d6`; the measured
index, type relationships, optional Rust backend and workflow-guidance changes
are now committed in `a96ea4c`, discovery/page-cache changes in `88de70b`, and
opt-in cross-restart index persistence in `9712467`.
This report is not a claim of complete parity, a performance victory, or a release gate.
No competitor implementation was copied into our package.

## Decision snapshot: 2026-10-22

The live GitHub commits API still resolves the competitor's latest commit to the
pinned `848c711f1d80a1c2577283f1fa5f475ff734aa40`. Feature implementation does not
establish universal superiority. The current decision is **partial, evidence-backed
advantages; implemented workflow parity awaiting final acceptance**:

| Dimension | Current evidence / remaining gap |
| --- | --- |
| Exact field-reference correctness | Our complete hit set matches the independent decoder for the measured operand; the pinned competitor has 97 extra instruction hits. This is a specific correctness advantage, not an oracle for all methods or operands. |
| Static relationships and bounded graph | Our type relationships cover additional declaration/annotation categories, and graph node/edge/byte budgets are explicit. Taobao graph cold/warm execution passed, and all 260 unique emitted sites matched an independent sequential decoder. This checks emitted-site soundness, not full-corpus graph completeness. |
| Query latency | Historical method/field cold measurements were 6.8328 / 5.3987 seconds versus the pinned competitor's 4.5192 / 3.5706 seconds. A resident exact-page cache now avoids repeated worker startup, and full-index secondary indexes are bulk-built. Cold queries and initial full-index cost still require measurement, not a universal speed claim. |
| Container scope | Generic ZIP, arbitrary directly embedded DEX paths, exact AAB modules and combined outer/AAR classes.jar DEX are implemented, including case-insensitive `.dex` suffixes. JVM and nested APK entries remain inventory-only; neither product's format list implies nested split reconstruction. |
| MCP output contracts | All 18 public tools now expose typed nested output schemas, strict wire-type validation and preserved optional diagnostics/extension fields. Public input descriptions and state-aware annotations are present. |
| Signing/revision/candidate strings | Candidate implementations exist; signing metadata is not cryptographic verification, revision comparison covers identities rather than behavior, and secret patterns produce redacted candidates rather than validated credentials. |
| Batch acceptance | The first combined run had 372 passes and two legacy offset-contract failures. After fixing the runtime contract, the six affected integration/server checks passed. Independent apksigner acceptance then exposed a real v2 parsing defect; the optional empty AOSP signed-data field is now handled, with 13 signing tests and seven independent signed/unsigned/tampered variants passing. A fresh complete fixed-candidate run, clean-package checks and the new Windows batch are still pending. |

Independent signing evidence is retained locally in
`artifacts/validation/batch-signing-oracle.json`; the original APK hash was unchanged.
The v1-only validity oracle is scoped to API 24-27. Metadata remains explicitly
unverified even when the external oracle accepts the APK. The v2 compatibility
fix follows the empty fourth signed-data field emitted by
[AOSP apksig](https://android.googlesource.com/platform/tools/apksig/+/refs/heads/main/src/main/java/com/android/apksig/internal/apk/v2/V2SchemeSigner.java).

The extended development gate passed 98 checks. The next Taobao interactive run
preserved all four discovery/reference page hashes and complete instruction counters;
exact-page repeats hit the new resident cache. Its reported 65-86 ms included a
50-ms RSS-sampler join, now excluded from subsequent latency measurements. Under
the loaded host, cold method/field scans took 11.2826 / 9.7120 seconds; these must
not be represented as a speed improvement or compared as a controlled competitor trial.
Receipt: `artifacts/validation/gap-interactive.json`. Final Linux/Windows and clean
distribution gates apply to the v0.3.0 candidate, not the older receipts below.

The large-APK graph gate passed on all 12 DEX files: cold graph including the full
2,238,009,344-byte index took 406.8324 seconds; the first indexed repeat took
0.2727 seconds, then resident exact-page hits took 0.0172 / 0.0184 seconds.
Depth-5 bidirectional exploration respected node, edge and output-byte bounds.
Androguard 4.1.4 independently decoded all 260 unique emitted call sites, with
callee, opcode and code-unit offset equality. Input SHA-256 remained unchanged.
Receipt: `artifacts/validation/gap-large-graph.json`. Host load and workload differ
from earlier timings; this does not establish a controlled 460-to-407-second gain.

The fresh local batch found four failures (392 passes): the typed DEX schema
omitted the existing `cli-text-best-effort` reference format. The schema now
accepts that wire value without changing or weakening the underlying reference
semantics, with a dedicated wire-roundtrip regression. Full gates are rerun on
the corrected candidate rather than reusing the earlier partial success.

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

The 2026-10-22 follow-up removes temporary DEX recompression and memoizes decoded
member-ID comparisons without skipping instruction decoding. A fresh stdio rerun on
the same sample reduced immutable session preparation from **13.2285 to 0.8306 s**,
method references from **8.1295 to 6.8328 s**, and field references from **6.9239 to
5.3987 s**. A separate three-trial old/new engine comparison verified every method/field
row and diagnostic; the saved independent field oracle still matches. See
[measurement details and storage trade-off](VALIDATION.md#snapshot-and-exact-reference-latency-follow-up-2026-10-22).
This materially reduces our end-to-end wait, but does not establish faster cold queries
than the pinned competitor measurements above. Resident-cache repeat latency remains
another gap; their field-count correctness discrepancy also remains relevant.

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
bounded graph exploration now has a candidate implementation in
[call_graph.py](../src/droidasc_mcp/call_graph.py), exercised against public
multi-DEX Smali call-site fixtures and real stdio/HTTP transport tests.

| Area | What the pinned implementation actually does | Our status / next action |
| --- | --- | --- |
| Agent routing | Server instructions distinguish declarations, string-pool matches, const-string use sites and type operands; each parameter has a description; read-only tools have MCP annotations. | Candidate has initialization instructions, an analysis-guide resource, two prompts, per-parameter descriptions, typed nested output schemas and annotations distinguishing read-only queries from session state. |
| Target discovery | `search_members` searches method/field declarations and returns full descriptors; `search_strings` searches the DEX pool with DEX name and string index. | Candidate now has declaration-only method/field discovery and DEX string-pool search, with explicit case-sensitive literal semantics and provenance. Neither scans instructions or builds the full index. |
| Query reuse | Resident workers cache parsed DEX and complete reference result sets by path/size/mtime; the reference cache has an eight-key LRU. | Candidate has a disk exact-page cache charged to the index reservation and a separate bounded resident serialized-page cache (32 pages / 4 MiB per session). Different pages may rescan; no resident workers or parsed APK objects. Warm speed requires fresh controlled comparison. |
| APK contents | Sorted entry inventory, asset/resource reads, binary XML decoding and native-library ABI inventory. | Candidate adds bounded inventory/entry reads, native ABI paths, binary XML decoding, SHA-256 and distinct decoding/truncation/CRC status. Real stdio/HTTP and independent large-APK ZIP/aapt2 checks are documented in ARCHIVE_WORKFLOW.md. Resource-table resolution and ELF analysis remain outside this slice. |
| Manifest analysis | Package/SDK/component structure, inherited application permission, and separate effective provider read/write permissions. | Candidate adds structured declarations, filters, metadata, provider read/write/path/URI-grant rules and permission provenance. Unlike the pinned implementation's general application fallback, an alias with no permission reports no requirement. Absent exported/resource-dependent values remain unresolved. Large-APK component kind/name order matches aapt2; this is not runtime exposure validation. |
| Calls and hierarchy | Source implements full method prototype selection, overload rejection, cached adjacency and depth 1-3 exploration, but real call-graph execution failed as documented above. Direct interfaces/subclasses and superclass chain are also implemented. | Candidate `get_call_graph` reuses our index: incoming/outgoing/both, depth 1-5, independent node/edge/byte caps, individual call-site provenance, external roots and dynamic diagnostics. First use still pays full-index cost; no general speed claim. |
| Signing | Androguard signing-scheme presence and certificate metadata/fingerprints. | Candidate inventories v1/v2/v3 certificate metadata and v3.1 presence. Seven independently signed/unsigned/tampered variants now pass; v3.1 extraction, rotation and cryptographic verification remain unsupported. |
| Formats | APK/raw DEX; directly embedded DEX in JAR/AAB/APKS/XAPK/ZIP; JVM `.class` inventory, including embedded JARs such as AAR `classes.jar`. | Candidate supports arbitrary direct DEX paths in APK/JAR/ZIP/AAR/APKS/XAPK, exact AAB modules and AAR classes.jar under one expansion budget. JVM and nested APK entries are inventory-only. |
| Version comparison | Class inventory added/removed sets and common count. | Candidate compares hash-bound class/method/field identities with pre-pagination filters. This is broader identity coverage, not a method-body, manifest or behavior diff. |

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
The inventory/content and structured-manifest slices now have candidate implementations
and independent acceptance in [ARCHIVE_WORKFLOW.md](ARCHIVE_WORKFLOW.md); the rows below
retain their original criteria, not a claim that all later slices are complete.
The indexed graph slice also has a candidate implementation and reproducible public
fixtures in [test_call_graph.py](../tests/test_call_graph.py), including cycles,
self-recursion, overloads, external roots, invoke-custom/polymorphic diagnostics,
exact-budget completion and bounded responses. Cross-platform/package gates remain
the acceptance authority for each commit, not the presence of an implementation.
The remaining signing, capability-container, revision-inventory and redacted-candidate
slices now have candidate implementations in [REVERSE_WORKFLOW.md](REVERSE_WORKFLOW.md).
All slices are being accepted together; no new row is implicitly marked passed here.

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
