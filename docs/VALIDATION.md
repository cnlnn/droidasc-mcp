# Local acceptance checks

Current completion scope: [GOAL_02X.md](GOAL_02X.md). Competitor workflow closure,
ergonomics, performance and independent accuracy remain the overall completion criteria.

## Flat schema warm path, 2026-10-30

Accepted W1 candidate `b325c012` expands only the nonrecursive `DexRow` leaf at
`DexResult.properties.items.items` and `DexReferencePage.properties.items.items`.
Definitions, all other schema paths, strict server/client validation, response
fields and the default flat format remain. The output cache format becomes 2;
all 49 input records remain identical, with their source hash refreshed. Only
three of 69 runtime files change. The a6f96b8 engine and dependency metadata do not.

Formal production A/B: six alternating fresh stdio servers, 36 complete
collections and 1314 page attempts on the existing Douyin concurrent method/field
cell. Every complete result and page agrees with the original baseline after
checked session/cache-state normalization; input identity and provenance remain.
Warm batch median is 5.97930 -> 5.48055 s (-8.3413%), cold 7.3437 -> 6.9929 s,
and process-to-first-complete 11.3237 -> 10.9462 s. The registered compiled
schemas are actually used and equal all 20 measured prototype schema dictionaries.

A separate fresh pinned-competitor comparison uses the same interpreter,
dependencies, original APK, four CPUs and resource limits. It reuses existing
cached dependency files through a verified shared test path, not a new consumer
installation. Its 36 new complete collections match the sealed G8 original-byte
truth; current source mappings and engine-dependent input IDs are independently
checked, with complete pagination replayed. No new oracle scan is claimed.

| Batch metric | Product seconds | Competitor seconds |
| --- | --- | --- |
| First complete concurrent batch | 7.0884 | 19.7914 |
| First warm batch | 5.4421 | 7.7288 |
| Second warm batch | 5.5301 | 5.1056 |
| Preset aggregate warm median | 5.47315 | 6.20615 |

The aggregate improves by 11.8109%, replacing G8's historical +6.86% result for
this refreshed cell only. The second warm batch still favors the comparator in
all three rounds (+8.3144% product median); this is not every-repeat or universal
parity. Open remains 3.2393/0.556 s, whereas process-to-first-complete is
11.068/21.1063 s. Sampled peak server RSS is 164,282,368/1,999,163,392 bytes;
private temporary logical storage is 477,976,012/0 observed bytes. Different
resources and different output shapes are not interchangeable performance claims.

Eight small existing-fixture baseline/final stdio/HTTP cells also pass: eight
complete collections, 16 full pages, eight warm-first pages and 48 tool calls.
Both advertised contract profiles keep the default strict SDK validator, all
payload/provenance fields and clean close/storage/children. Decoded compact tool
metadata grows 146416 -> 156676 bytes for legacy and 230098 -> 252670 for artifact.
This is a measured listing-size cost, not a listing-latency or model-success win.
Some invalid-result SDK schema-context dumps grow; constraints, rejection reasons
and paths remain equivalent, not byte-identical dump strings.

Existing source/package CI 40922087963 passes all 25 jobs: eight source and
sixteen canonical-sdist/exact-wheel suites across Linux/Windows Python 3.10-3.13,
each 2162 tests with zero failures/errors/skips. All 12 downloaded ZIPs match
server digests; package sources, dependencies, four native wheels, signing,
Rust and stability gates pass. No new ordinary-pip campaign was added.
Independent combined closure is
`artifacts/competitor-gap-warm-residual-20261030/W1-acceptance.json`, SHA-256
`5be9b0cf2600cb29bd7a356371204b14cb323f0350c3c6cf480ee4c9e86ec8e7`.
It rechecks existing receipt bindings and ZIP member bytes, not another benchmark
or oracle run. Component evidence:
`artifacts/competitor-gap-warm-residual-20261030/final-performance/acceptance.json`
(`ddc918f41a5b21767d669e5f7bc1dd7b3058430275f4860b378a52cfcd6e353c`),
`fresh-comparator/acceptance.json`
(`129c0de5a1ce5f93cd9f2d9e7ac4167fb20090073f4a8a3b8248237579ef8299`)
and `transport-smoke/attempt2/verification.json`
(`37551fbd277c5fdc56ba8ed10d4124c1797c2afd5acdddab13fb96f08f307641`).
The source dependency, preserved D1 ordinary-pip proof and published v0.2.5 are
unchanged. W1 is accepted development, not a new release. The finite batch's
agreed gates are complete; thermal-start waiver and all existing coverage limits
remain explicit rather than new unbounded requirements.

## Default dependency adoption, 2026-10-30

D1 is accepted for the development dependency `0.1.2.post3+sourcefixes.2`, pinned to
Git source `a6f96b864cc317116cd38af143c63fe82b149099` and subdirectory
`third_party/droidasc_sourcefixes`. The candidate is `cdb4f35`; the independently
accepted gates have deliberately different scopes:

| Gate | Verified scope | Evidence under artifacts/competitor-gap-g17-20261029 |
| --- | --- | --- |
| Existing changed-dependency matrix | CI 40908697104, 25 successful jobs; eight source and sixteen installed-package suites across Linux/Windows Python 3.10-3.13, each 2030 tests with zero failures/errors/skips | adoption-ci/ci-acceptance.json |
| Ordinary pip consumers | Linux Python 3.13 CI 40915579504, helper commit 05c5088; two fresh venvs install the canonical sdist/native wheel with the complete resolver and no seeds, --no-deps or overlays; each passes four real-worker regressions plus one installed-identity case with zero skips | adoption-pip-ci/acceptance.json |
| Normal locked uv | Clean HTTPS clone at cdb4f35, ordinary existing uv cache and verified Git dependency identity; no cold-cache claim | adoption-uv-normal-cache/receipt.json |
| Normal uv MCP workflows | Eight complete plain/metadata collections over stdio/HTTP, all source bytes/page fields match G15 after checked session mapping, 656 ordered links per metadata collection and both original Throws annotations preserved | adoption-uv-workflows/verification.json |

Independent combined closure:
`artifacts/competitor-gap-g17-20261029/D1-acceptance.json`, SHA-256
`c4eb9eafa0a2409b5ef180ad91638ab9f68375b8e512ee0b9c3ac4d57e13b63f`.
It rechecks the CI ZIP/download bindings, ordinary-pip evidence, normal-uv install
and workflow bindings, and the preserved G17 navigation receipt. The original local
main-environment engine's 80 files remain unchanged; default adoption is verified
through the development dependency definition and the separately proven clean installs.

The ordinary-pip job reuses the exact already-accepted matrix artifacts, not a local
replacement build. Canonical sdist SHA-256 is
`cc4f8011dff1f2834a090bcaf54ce39225c4dc18edbd646cf8b2064b90ef0326`;
Linux cp311-abi3 native-wheel SHA-256 is
`e194ecb95cceee0efe855c074b575fbc2f9793afbf9789ee5ecbd6e9efa6689f`.
Both fresh consumers verify PEP 610 URL/SHA/subdirectory, all 80 engine Python files,
all 23 original dadguard files, all 69 MCP runtime sources and matching
`Requires-Dist`. Their ten targeted test executions are separate from the 24 full
matrix suites; neither is counted as a replacement for the other.

The local direct-network/TLS failures, cold-cache attempts and interrupted consumers
remain preserved under the adoption evidence directories. They are not relabeled as
successful installs; the remote ordinary-pip gate now supplies the missing proof.
The Linux/Windows locked source/package matrix does not establish Windows ordinary
pip acceptance, and the eight MCP collections use the verified uv environment rather
than the pip consumers. Published v0.2.5 assets are unchanged; this accepted development
increment is not released. At the D1 checkpoint the approximately 6.86% default-flat
Douyin warm residual remained; W1 above refreshes that cell separately. D1 itself
establishes neither a latency improvement nor overall competitor parity.
Uncached source-dependency installation still requires Git and GitHub HTTPS; no public
upstream PR or new package release is claimed by this downstream adoption.
Earlier sections below retain their original checkpoint-specific scope and failures.

## Selected member navigation, 2026-10-30

G17 completes four real stdio/HTTP sessions on the manifest-discovered WeChat and
Douyin application classes: 102 calls, 94 response pages, 36 complete paginated
collections and 12 exact Smali collections (six distinct methods). Independent
Androguard scans consume all instructions in 69 original DEX files, 73,977,365
instructions in total. All selected outgoing/incoming/field multisets match with
no missing or extra sites; exact method flags/opcodes/member operands and the
logical-to-original-physical DEX mappings agree. Full public responses are compared
after checking and normalizing only per-session handles; engine and input identity
remain checked. The first Douyin oracle hits its 300-second window; the separate
600-second full attempt passes in 526.21 seconds. Both attempts are retained.

Evidence: artifacts/competitor-gap-g17-20261029/g17-acceptance.json, SHA-256
130392e03f2bbfab69c82e4933e2f1e2636aa478956a1c62b77f00d5fc09ea0e;
independent/verify_acceptance.py replays the sealed checks without another APK scan.
Scope is the selected source-member navigation chain, not all classes, dynamic
dispatch resolution or a performance claim. D1 above now accepts default development
dependency adoption of these verified fixes through separate installation/package
gates, without adding another corpus expansion or a performance claim to G17.

## Original type-link package check, 2026-10-29

G14 independently verifies all 343 method/field tokens and nine selected complete
reference-site sets against original DEX identities/instructions, but finds 25
additional class links with invalid identities on the manifest-discovered F-Droid
application class. G15 reuses adjacent original field/return/argument tokens and
the existing ASC Writer-extension pattern for raw array types, without modifying
bundled dadguard or introducing an MCP-private import. The first candidate misses
one array-component identity and is not accepted; attempts.md retains that run.

The final local dependency wheel `0.1.2.post3+sourcefixes.2`, local upstream commit
140b05c, changes only the ASC decompiler file among 80 Python files. All 23 released
dadguard files, accepted G12 MCP sources/native wheel, license and main environment
remain unchanged. Normal installed-wheel fixtures fail 8/16 before and pass 16/16
after; selected upstream tests pass 48 cases plus four subtests. Eight complete
plain/metadata stdio/HTTP collections preserve all source bytes, correct 21 raw
class identities, remove four keyword links and retain the other 635 ordered links
and global Unicode spans. The independent oracle checks original type/member tables
and the selected onCreate new-array operand. G14's nine instruction sites are reused
only for byte-identical member links, not described as freshly rerun. Input-ID
version-bound derivation is checked before normalizing cross-version pages.

Evidence: artifacts/competitor-gap-g15-20261029/g15-acceptance.json. Scope is an
isolated Linux Python 3.13 package candidate for this selected class, not default
dependency adoption, a portable changed-dependency gate, a release or a performance
claim.

G16 completes 32 additional complete ordinary/metadata source collections over both
transports on WeChat/Douyin manifest application classes. All source bytes match the
official engine. Original owning-DEX type/member tables and encoded class definitions
validate 460 member and 356 class tokens; all 69 original DEX hashes are checked using
reported logical-to-container entry mappings. Eight class identities are corrected,
42 keyword links removed and all other ordered links/spans preserved. The first
verifier confused a logical DEX label with its original ZIP entry; the recorded
provenance is correct and the verifier is corrected without rerunning workflows.
The final receipt separately seals a formerly live output-log digest after process
exit. Original failed verifier/log receipts are retained. Evidence:
artifacts/competitor-gap-g16-20261029/g16-acceptance-final.json. Scope is two selected
application classes in the same normal installed Linux environments, not all classes,
fresh full instruction-site revalidation, portable adoption or a performance claim.

## Annotation dependency package integration, 2026-10-29

G13's local dependency build starts from the lock-pinned official droidasc sdist,
whose 80 Python files equal the official wheel and installed dependency. The local
`0.1.2.post3+annotations.1` wheel changes only the two lazy annotation-directory
resolution lines; all 23 bundled dadguard files are unchanged. Wheel RECORD, sdist/
wheel equality, license retention and the local modification notice are checked.
Two clean environments install normal official/local dependency wheels and the same
accepted G12 native MCP wheel, without PYTHONPATH, editable installs or source overlays.
All other distribution versions and all 69 MCP runtime source files are equal.

Four serial real MCP sessions (before/after, stdio/HTTP) collect complete ordinary and
metadata source twice, 16 collections total. The class is discovered from the manifest
and its complete outline is read first. Both transports and warm reads match. The
only source changes are the two original-DEX-confirmed Throws annotations; all 660
ordered links and shifted Unicode spans equal the corrected G10 output. Input IDs
are independently reconstructed from engine version and ordered original DEX hashes,
not silently ignored. Installed generated-fixture tests fail 2/4 on the official
wheel and pass 4/4 on the local wheel. Original APK and 80 main-environment dependency
files remain unchanged; all owned storage/children are removed. Verification retries
and their narrow comparison mistakes are retained in package-integration/attempts.md.

Evidence: artifacts/competitor-gap-g13-20261029/package-integration/
integration-verification.json. This accepts an isolated Linux Python 3.13 installable
candidate, not main dependency adoption, a cross-platform changed-dependency gate,
performance parity or a release. A prepared upstream contribution remains local;
no public fork/PR, upstream push, package publication or installed dependency change
has occurred. Fresh checked main/dev/open-PR diffs contain no corresponding fix;
source-review/review.json binds those read-only checks. Public contribution permission
and portable dependency availability/integration remain open while G14 proceeds.

## Metadata source reuse acceptance, 2026-10-29

G12 extends the same bounded snapshot mechanism to the existing ASC metadata
facade. It retains complete source and serialized ordered token links in one shared
cache budget, preserving Python Unicode line boundaries and global code-point spans.
Source plus reference export bytes share one disk reservation. No new decompiler,
cache database or ASC-private import is added; physical DEX 041 stays on its old path.
An oversized later plain-source line now falls back to the worker's exact error
envelope instead of adding two optional provenance fields, the scoped G11 residual.

Evidence under artifacts/competitor-gap-g12-20261029 binds 12 serial alternating
fresh-server stdio trials, 24 complete collections and two complete HTTP collections.
Every source byte, page diagnostic, ordered token row and global span equals the
baseline. An unpaged ASC facade on separately read original DEX bytes checks the
adapter/pagination, not independent decompiler correctness. F-Droid has 489 lines,
five pages and all 660 token links; WeChat has 62 lines and all 38 links. F-Droid
first/repeated medians change from 0.7985/0.7781 to 0.2413/0.0779 seconds. WeChat's
one-page first call changes from 0.1299 to 0.1328, not an improvement, while its
repeat changes from 0.1060 to 0.0089 seconds. Original APKs and 80 installed
ASC/dadguard Python files remain unchanged. Four CPUs, serial timing and the thermal
start waiver are recorded; this is no comparator, cool-host or general-memory claim.
All 124 focused tests pass, including 21 new cases. Final adopted commit 5a96ea6
passes all 2013 local tests and [CI 40801161988](https://github.com/cnlnn/droidasc-mcp/actions/runs/40801161988),
25/25 jobs. Eight Linux/Windows Python 3.10-3.13 source suites and sixteen installed
canonical-sdist/exact-wheel suites each pass 2013 tests with zero failures/errors/skips.
Twelve artifact ZIPs, canonical sdist/four native wheels and all 69 runtime source
files match the frozen candidate. Four more complete adopted-runtime stdio collections
match the byte-identical prototype. g12-acceptance.json binds these checks, original
input hashes and unchanged main/tag/latest/asset digests. G10 annotation dependency
integration remains separate; a local upstream contribution with generated-fixture
regressions is prepared under artifacts/competitor-gap-g13-20261029, not installed.
Neither G11 nor G12 changes the published v0.2.5 assets.

## Session source reuse acceptance, 2026-10-29

G11 reuses the existing public-CLI complete snapshot rather than decompiling each
plain class-source page. Its decoded text and serialized provenance share the existing
cache budget/TTL/entry count. Prepared/runtime changes invalidate reuse; session close
removes it. Export storage uses the shared disk reservation, with normal-worker fallback
when optional caching cannot be used. Page bounds, complete response limits, original
source records and malformed-query error envelopes are preserved. Metadata/token-link
source and physical DEX 041 normalization are separate. Final runtime evidence under
artifacts/competitor-gap-g11-20261029/final checks 12 serial alternating stdio trials,
24 complete original-byte/public-CLI-checked collections and two complete HTTP
collections, including all page diagnostics and owned cleanup. F-Droid first/repeated
complete-source medians change from 1.0565/1.0717 to 0.2530/0.0349 seconds; WeChat
changes from 0.2746/0.2290 to 0.2556/0.0072. These are scoped current-host measurements,
not comparator or general-memory claims. All 103 final focused tests pass, including
17 new regressions. Earlier 1988/1989-test suites precede final compatibility guards.
Final commit 3709bf2 passes [CI 40796945147](https://github.com/cnlnn/droidasc-mcp/actions/runs/40796945147),
25/25 jobs: eight source and sixteen canonical-sdist/exact-wheel suites each pass
1992 tests with zero failures/errors/skips. All twelve CI ZIPs, four native wheels
and 69 runtime sources match the frozen candidate. g11-acceptance.json binds these
checks and unchanged main/tag/latest/asset digests, with the later oversized-line
error's two extra optional fields explicitly retained as a residual, addressed by
G12. This is development acceptance, not released v0.2.5 code or universal parity.

## Post-release compact handle inventory, 2026-10-29

The development branch reuses PreparationZipFile for the upstream-derived artifact
handle inventory, avoiding retained ZipInfo objects for ordinary resources. Aggregate
expanded bytes and largest DEX size preserve the existing budgets. Original input
copy/hash/identity checks, lazy code preparation and ordinary resource readers remain.
Eight new adopted regressions pass. The isolated prototype passes 1975 local tests,
30 serial alternating real-MCP trials and 60 complete collections independently
checked against original bytes. Production adoption only removes an unused import
and formats the same function bodies. Final development commit
`eb8159a6416dabd231ff074fb1cf3fb27ec0d23e` passes
[CI 40787653294](https://github.com/cnlnn/droidasc-mcp/actions/runs/40787653294),
25/25 jobs. Eight Linux/Windows Python 3.10-3.13 source cells and sixteen installed
canonical-sdist/exact-wheel suites each pass 1975 tests with zero failures/errors/skips.
Twelve original CI ZIP digests, the canonical sdist, four exact native wheels and all
69 frozen runtime source files are checked. Fresh stdio/HTTP covers resource-heavy APK,
multi-module AAB, nested AAR, prefixed ZIP64, deferred DEX, original entry metadata,
aggregate expanded/DEX limits and complete owned cleanup. g7-acceptance.json accepts
development only and freshly checks main/tag/latest/asset digests unchanged.
This is not part of the published v0.2.5 runtime or a final-commit optimization ratio.
Evidence: artifacts/competitor-gap-g7-20261029. Its initial Taobao pilot overlapped
owned tests and is excluded from latency acceptance; clean-matched is separate.

## Complete concurrency reassessment, 2026-10-29

artifacts/competitor-gap-g8-20261029/g8-acceptance.json binds 24 serial alternating
real-MCP trials and 144 independently checked complete collections against original
APK bytes, with pinned comparator source/runtime and original request/cursor replay.
Two APKs, flat/grouped cells, four CPUs and three rounds are checked; no code or
default changes occur. Douyin first complete concurrent batches are 8.6289/22.8832 s
flat and 7.5928/23.7598 s grouped, product/comparator medians. Repeated medians are
7.0980/6.6423 s flat and 5.9162/6.6485 s grouped. WeChat repeated medians are
3.6886/3.9304 s flat and 3.7225/3.8728 s grouped. Douyin default flat retains a
roughly 7% warm residual. Separate format cells do not prove a causal format speedup,
and the explicit temperature-start waiver does not establish cool-host performance.
Historical Taobao comparator failures are not declared fixed by these cells.

The G9 diagnosis under artifacts/competitor-gap-g9-20261029 verifies twelve cached
flat pages equal G8, including cleanup/runtime identity. Client instrumentation shows
substantial jsonschema validation cost; it does not justify another cache or disabling
validation. g9-diagnosis.json records diagnosis only, not a performance fix or release.

## Source navigation probe, 2026-10-29

artifacts/competitor-gap-g10-20261029 retains a full real manifest-to-application-class
source workflow. A separate original-DEX annotation reader confirms two Throws method
annotations missing in current ASC CLI and metadata output but shown by the comparator.
The source outputs differ, so the single pilot pair is not equal-correctness timing
acceptance. Current and historical reference-query correctness gates are separate.

An isolated upstream ASC candidate at 9216fe2 adds lazy annotation-directory loading
for the selected class and reuses existing source rendering. The new focused tests
first fail twice, then 48 tests plus four subtests pass. Fresh public CLI adds only the
two annotation lines; real stdio reconstructs all five metadata pages equal to comparator
text, and all 660 existing token links preserve identity and shifted code-point spans.
The first verifier's invalid plain-CLI/metadata text equality assertion is retained and
documented separately. A final overlay retains the actual installed dadguard wheel
rather than the Git checkout's two differing files, repeating all 52 tests/subtests
and five complete metadata pages. installed-deps-verification.json binds that retest.
upstream-candidate-verification.json accepts an isolated prototype,
not an installed dependency change, MCP product fix, new package gate or publication.

## v0.2.5 published, 2026-10-29

The maintainer approved publication after scoped B1-B6/G1-G6 acceptance. This
candidate changes version metadata and release documentation, retaining the accepted
`ead1a91` runtime sources. The final preservation receipt is
artifacts/competitor-gap-b6-resume-20261029/g6-acceptance.json: 25 successful CI jobs,
1967 tests per source/package cell, fresh raw stdio/HTTP DEX 041 workflows and 60
independently checked complete large-APK collections. Its explicit current-host
temperature override is recorded separately from cool-host performance claims.

Fresh versioned evidence is in artifacts/release-025-20261029. Commit
`87b3630769480b85349ae44c4021c8641b0c155b` passes
[CI 40784077867](https://github.com/cnlnn/droidasc-mcp/actions/runs/40784077867),
all 25 jobs. Linux/Windows Python 3.10-3.13 source, canonical-sdist and exact-wheel
suites each pass 1967 tests with zero skips; signing, Rust and stability checks pass.
All twelve downloaded artifact ZIPs match server digests. The five distributions
contain the same 69 accepted runtime source files. The four wheels and canonical
Ubuntu Python 3.11 sdist are published unchanged, alongside SHA256SUMS.
acceptance.json and published-readback.json bind the CI originals, versions and
downloaded hashes to the [release](https://github.com/cnlnn/droidasc-mcp/releases/tag/v0.2.5).
Main and annotated tag matched that commit at publication; Latest, six server
asset digests and downloaded bytes agree. Older releases and tags are unchanged.
Subsequent development changes have separate receipts and are not release contents.

## v0.2.4 release candidate, 2026-10-27

The current candidate freezes the post-consolidation workflow changes described in
CHANGELOG.md. Its initial full local assessment is preserved in
artifacts/release-assessment-20261027/source-full.xml, including the stale nullable-schema
assertion failure. The corrected assertion validates accepted/rejected JSON values rather
than requiring the older `anyOf` spelling. Release acceptance must bind the frozen commit
to fresh Linux/Windows Python 3.10-3.13 results, the canonical sdist, exact native wheels
and original-input reference checks. New receipts live in artifacts/release-024-20261027;
the release notes identify the final CI and package hashes after those gates pass.
Earlier evidence below retains its original runtime and scope; it is not a substitute for
this candidate's final package acceptance or proof of overall performance completion.

The first candidate 014969b passes all 1490 local Linux source tests with zero skips.
CI 40430197917 passes 17 jobs but fails all eight Windows source/distribution jobs with
a test-fixture lifetime error: the corrupt-reference-count mutation commits its SQLite
transaction without closing the connection before checking file cleanup. Production cache
cleanup correctly retains its reservation when Windows refuses deletion of that open file.
The fixture now explicitly closes the connection, with a closed-handle assertion that also
fails on Linux before the fix. Production runtime sources are unchanged. The failed CI,
packages, local red test and original-oracle timeout/retry are preserved under
artifacts/release-024-20261027; the SQLite-only candidate's local 1490-pass receipt is in
candidate2. Complete downloaded logs also expose a Windows timer-resolution failure in
the full-collection benchmark unit test: a 10-ms sleep can leave successive monotonic
readings equal. That test now advances a module-local deterministic clock per fake response
and asserts exact complete-collection and per-attempt durations, retaining strict last-page
and response-limit recovery checks. Real benchmark timing code is unchanged. Superseded
CI 40431741392 was cancelled; final source/package gates use the candidate3 subdirectory.
The independent Douyin JVM oracle timed out once at 180 seconds and passed a separate
same-parameter retry; this is not a product-query failure or a performance acceptance result.

## Complete concurrency development checks, 2026-10-24

The full_concurrent harness now collects every method and field page concurrently and
independently checks the actual request/cursor/collection inventory. The unchanged
`3bb432d` production runtime passes all 72 complete collections across three APKs,
two/four CPUs, three matched rounds and two repeats. Comparator replay accepts 60 of 72;
12 Taobao field collections each have 97 extra sites, excluding those batch timings from
equal-correct-result comparisons. Four-CPU Douyin complete repeated concurrency still
loses: 7.5007 versus 6.2604 seconds median. First-page wins do not close that deficit.

The initial graph batch exposed an async deadline/cleanup overrun and was stopped, with
its evidence preserved. The harness now has a separate owned-child watchdog, tested with
a blocked event loop and a real sleeping child. The focused harness gate passes 110 tests
with zero skips in artifacts/graph-concurrent-20261024/harness-provenance-fixed.xml.
This is not new Linux/Windows/package acceptance or publication approval. Full details
and timing scope are in STARTUP_STORAGE_EXPERIMENTS.md.

The deadline-fixed large-graph batch additionally accepts 24 measured product graphs
against a fresh full index built from original DEX bytes and independently decodes every
emitted call site. All graphs explicitly reach their 128-KiB output bound. The comparator's
12 trials time out at 30.0350-30.0761 seconds, so there is no equal-success graph timing
ratio. Eleven records show watchdog expiry and one async timeout finishes first. The
interrupted Douyin offline replay is preserved and resumed separately; no timing batch
was repeated. artifacts/graph-concurrent-20261024/summary.json binds the accepted receipts.
This proves bounded output equality and emitted-site validity, not independent full-graph
completeness or broader workflow closure.

## Consolidated v0.2.3, 2026-10-23

The maintainer requested withdrawal of v0.2.3-v0.2.9 and fresh consolidation as v0.2.3.
The original release metadata/assets and tag objects are backed up and hash-verified under
artifacts/reissue-023-20261023/backup. v0.2.2 and earlier remain unchanged. Current runtime
sources are retained from 159a6f39b0764f44e27c05203ab53573cd344dc4; version metadata and
release documentation are updated. Fresh Linux/Windows Python 3.10-3.13, canonical-sdist,
native-wheel, signing, Rust and stability acceptance passed on the consolidated release commit
`12a4fc51ba36a64a54bc3623dc348a499f466ac9`:
[CI 39939932398](https://github.com/cnlnn/droidasc-mcp/actions/runs/39939932398), all 25 jobs.
Each source OS/Python cell passed 1184 tests with zero errors, failures or skips; all eight
distribution cells tested both the canonical sdist and their exact native wheel, each with
1184 passing tests. Four package jobs, two Rust jobs, two stability jobs and the fixture job
also passed. The six release assets were downloaded again and checked against local and
server SHA-256 values; main and the annotated release tag target the same accepted commit.
Release metadata, asset hashes, preserved older releases and withdrawn tags were read back
under artifacts/reissue-0.2.3-ci-39939932398/{acceptance-summary,published-readback}.json.
The [consolidated release](https://github.com/cnlnn/droidasc-mcp/releases/tag/v0.2.3) is published.
These receipts cover that frozen release, not subsequent development-branch changes.

## Workflow candidate, 2026-10-23

Candidate e3f381927c98976d4b2052ec29e0d86136e47c48 remains on
codex/workflow-triage-next, not main or the published tag.
[CI 39967501671](https://github.com/cnlnn/droidasc-mcp/actions/runs/39967501671) passes
all 25 jobs: each of eight Linux/Windows Python 3.10-3.13 source cells passes 1264 tests
without failures/errors/skips; each distribution cell passes the same 1264 tests on both
the canonical sdist and its exact native wheel. Source cells additionally pass seven
independent signing variants; package, Rust, stability and fixture jobs pass.

The initial f144c08 run 39962833696 is not acceptance: Windows pytest setup/teardown
failed because auto-generated test IDs contained full oversized XML payloads and exceeded
the 32767-character environment-variable limit. Fixed short IDs retain every payload and
assertion and explicitly bound the node ID. The failing attempt was cancelled and retained.

Evidence: artifacts/workflow-entry-ci-39967501671/acceptance-summary.json verifies all
12 downloaded artifact ZIP digests, 24 extracted files, canonical-sdist hashes in all
eight distribution logs, packaged runtime source against the commit, four wheel identities
and installed-byte checks. wheel-original-accuracy.json binds the exact Linux CI wheel and
installed native extension to full independent original ownership/snapshot checks for all
884805 classes across Taobao/WeChat/Douyin and complete selected Taobao reference/diagnostic
comparisons (24461 method sites, 332 field sites, 12495817 instructions, three rounds each).
The native oracle driver Path fix has two regressions executing the real child command.

These receipts do not prove all-query/all-APK accuracy, lower total memory, a universal
startup advantage or complete competitor workflow superiority. They do not authorize a
new release; the current startup/storage experiments are separate and remain isolated.

## Complete MCP Reference Pages

The latest adaptive-page increment keeps the 256-KiB DEX-response ceiling and requested
maximum row count, returning a complete prefix with explicit byte-limit hints and exact
continuations instead of requiring a failed oversized attempt. Its focused gate passes
288 tests, zero skips, with 52 deliberate other-integration deselections:
artifacts/adaptive-reference-pages-20261024/targeted-complete.xml. Both real transports
collect all 2000 individual sites from a generated DEX twice without retry; independent
verifier regressions reject false byte hints, oversize and incorrect continuations.
The input/output schema checks and pinned 25-tool/2-resource/3-prompt/87-parameter
inventory audit also pass; inventory is not behavioral acceptance of all parameters.
The new accepted/summary.json under that root binds all 98581 original selected sites
over 148 pages, 36 matched trials and 72 independent collection replays. Every product
collection passes. Six competitor Taobao-field replays retain the 97-extra-site failure;
the other 30 comparator collections pass. All 36 frozen before/after complete responses
also match independent current acceptance, including ordered duplicates and diagnostics.
Paired latency effects are mixed, not a universal improvement. Fresh comparisons still
lose on Taobao/Douyin method repeats, Taobao complete-method startup and WeChat field
startup. See STARTUP_STORAGE_EXPERIMENTS.md for exact medians and separate RSS/tmpfs
costs. Full current-runtime Linux/Windows/canonical-package gates remain outstanding;
the following earlier counts and CI receipts are historical, not approval of this runtime.

The subsequent output-schema-only increment uses Pydantic's equivalent primitive type
unions, retaining strict runtime contracts and all result fields. Its focused gate passes
203 tests, zero skips, with 52 deliberately deselected other integration cases:
artifacts/selected-reference-cache-20261024/schema-types-transport-final.xml.
All generated nullable leaves and retained constrained unions are checked against the
original schemas, including the older-Pydantic fallback. Both real MCP transports cover
references, fuzzy queries, graphs and resource views. See STARTUP_STORAGE_EXPERIMENTS.md
for the separate frozen-source three-APK before/after trial scope. This is not a new
full Linux/Windows or canonical-package gate; the following 196-test cache run is historical.
Fresh current-runtime receipts under schema-types/summary.json independently pass all
98581 selected original sites/200 pages and all 36 product collection replays across
36 matched trials. Six competitor Taobao field replays fail with the same 97 extra
sites each; the other 30 comparator collections pass. The separate frozen before/after
trial's 36 complete collections match accepted current responses, including order,
duplicates and full diagnostics: schema-paired-runtime/accuracy.json. The source,
inputs, benchmark and independent oracle identities are bound and unchanged. All three
method-repeat medians and WeChat field startup still lose in this fresh comparator
batch. See STARTUP_STORAGE_EXPERIMENTS.md for exact timings, resources and batch limits.

Implementation follow-up, 2026-10-24: the development runtime now has a session-accounted
complete-selected-set cache and bounded host paging. It differs from e3f3819. The targeted
suite passes 196 tests, zero skips and 56 intentional other-integration deselections:
artifacts/selected-reference-cache-20261024/focused-transport-bounded-retry-final.xml. It covers real
stdio/HTTP reference/fuzzy pages, full cached response equality, quotas, concurrent fills,
cancelled page waiters, corruption, input changes and lease/file cleanup. Fresh full
Linux/Windows and canonical-package gates remain open for this new runtime. See
STARTUP_STORAGE_EXPERIMENTS.md for failed attempts and exact large-input receipt scope.
The final new-runtime summary is
artifacts/selected-reference-cache-20261024/bounded-retry/summary.json: all 98581
selected original-byte sites and 200 pages pass, as do all 36 product collection
replays. All 36 matched benchmark trials complete; six competitor Taobao field
collections fail independent equality (97 extra sites each). Those failures are not
rewritten as passing accuracy or equal-correct-result timing. First complete query
latency improves relative to the paired competitor in this corpus, while repeat and
startup deficits remain explicit. Source/runtime and helper identities are unchanged
through the final run; the earlier failed timeout and pre-bounded-retry run stay separate.

The preceding complete-collection benchmark and isolated selected-result spool experiments are
recorded in STARTUP_STORAGE_EXPERIMENTS.md. At those experiments the runtime still matched
e3f3819; neither private prototype was adopted or approved for release. The benchmark/normalization/replay
selection passes 95 local tests without skips: full-page-benchmark-targeted-final.xml under
artifacts/startup-next-20261023. This is distinct from the earlier 95-test container/reference
selection below and does not raise the exact e3f3819 CI count.

The development-only verifier scripts/verify_mcp_reference_pages.py reads every successful
page for String.equals method references and Build.MODEL field references through real
stdio. A frozen independent JVM scanner consumes original APK bytes, mapped to canonical
names only after independently enumerating every original DEX. Missing DEX entries,
duplicate inventories, swapped canonical mappings, altered bytes, diagnostic changes,
same-count corruptions, wrong ordering and skipped/repeated continuation offsets fail.
Only implementation-specific backend/backend_version labels are excluded from equality.

Evidence root: artifacts/startup-next-20261023. The final batch receipt is
current-reference-pages-corpus-final.json; its three
current-{taobao,wechat,douyin}-mcp-full-reference-pages-final.json receipts pass:

| Input | Complete method sites | Complete field sites | Successful pages | Instructions per full query |
| --- | --- | --- | --- | --- |
| Taobao | 24461 | 332 | 50 | 12495817 |
| WeChat | 26184 | 110 | 54 | 21430036 |
| Douyin | 47005 | 489 | 96 | 52547329 |

All 98581 ordered rows and every scanner diagnostic agree, not just totals. Each method
query first receives response_limit at limit=1000, records that response and retries the
same offset at limit=500. No rows are lost by recovery. These 200 successful pages are
not 200 distinct full instruction corpora; changing offsets currently repeats scans.
Original input, runtime, scanner source, executable and jar hashes stay unchanged;
original DEX inventory/canonical mapping, session/input/source provenance and complete
owned-temporary cleanup pass. The independent JVM's explicit heap cap is 1024 MiB;
its work/storage are accuracy-oracle costs, not product latency or RSS measurements.

The initial two attempts remain failed evidence: oversized pages, then an incorrectly
compared backend-version label; the initial Douyin scanner also exited nonzero with a
512-MiB heap (that first receipt did not preserve stderr, so its root cause is not claimed).
Two regressions subsequently exposed and fixed a verifier-only common-mode inventory gap:
an omitted original DEX or swapped canonical mapping must not be accepted based solely on
session metadata. All three complete transport checks were rerun after that fix. Earlier
checked receipts are separate; their exact helper is retained as reference-pages-checked-verifier.py.

The final verifier, container and preparation-directory selection passes 95 tests with no
failures/errors/skips: reference-pages-and-prefetch-final-targeted.xml. This is not a
replacement for a final full source/package/Windows matrix. Runtime code is unchanged
from e3f3819; the added acceptance scripts/tests do not change its historical CI count.
Full-collection performance against the competitor, additional graph inputs and the
startup/storage gaps remain open; no new publication is approved by these receipts.

## Historical v0.2.x native-query evidence

The versioned publication statements below describe the withdrawn increments, not current
download availability. Original receipt versions and commits are preserved; they are not
relabelled as fresh acceptance of the consolidated v0.2.3.

The maintainer superseded the replacement-v0.3.0 plan with accepted 0.2.x increments.
Old v0.3.0/v0.4.0/v0.4.1/v0.5.0 releases and tags were withdrawn on 2026-10-23 after
verifying their backup metadata, all 16 asset hashes and Git tag objects. v0.2.2 and
earlier releases/tags remain unchanged. v0.2.3 was published, targeting
4c28572935eda91bd8250c54d1663526d532a858 on main and its annotated tag.
CI 39826824176 passes all 17 jobs: each of the eight Linux/Windows Python 3.10-3.13
cells passes 1019 tests, zero failures/errors/skips, plus signing, Rust, stability,
packaging and both clean-distribution jobs. The latter use the same canonical sdist.
The exact accepted Linux/Windows native wheels and sdist were published, downloaded
again and matched to both local SHA-256 and GitHub asset digests. Evidence is under
artifacts/acceptance-0.2.3-ci-39826824176, including acceptance-summary.json and
published-readback.json. This increment does not close the overall performance/workflow goal.

v0.2.4 was published, targeting 29475d9f58edc09969ee08bd6491bd515752a41a.
CI 39836635008 passes all 17 jobs, including 1075 tests per Linux/Windows Python 3.10-3.13
cell with zero failures/errors/skips and both canonical-sdist/native-wheel clean-install jobs.
The published packages are those exact CI assets, not local rebuilds. Downloaded asset hashes
match both the staged files and GitHub's server digests. Receipts:
artifacts/acceptance-0.2.4-ci-39836635008/{acceptance-summary,published-readback}.json.

Independent v0.2.4 string oracles match all 7679 selected literal `https://` sites across
86,473,182 instructions in Taobao/WeChat/Douyin. Taobao fuzzy matching verifies 28,110 sites;
the exact Linux wheel additionally verifies 2163 selected string sites and all 2,914,002
persisted declared call sites. These are full multiset comparisons with unchanged input/runtime,
not count-only checks. The oracle receipts are increment024-29475d9-*.json and
increment024-ci-wheel-*.json under artifacts/release-renumber-20261022.

v0.2.5 was published, targeting 1b25267d2f123b03d722509f56425da347031818.
CI 39847579502 passes all 17 jobs, including 1096 tests and seven signing variants per
Linux/Windows Python 3.10-3.13 cell, zero failures/errors/skips. Both clean-distribution jobs
verify the same canonical sdist, matching packaged sources and installed native-wheel bytes.
Fresh source and exact Linux CI-wheel oracles each verify all 884,805 original classes and
all snapshot DEX bytes across Taobao/WeChat/Douyin. That wheel independently verifies all
2,914,002 Taobao call sites and 2163 selected string sites. Re-downloaded published assets
match local and GitHub SHA-256 digests. Receipts:
artifacts/acceptance-0.2.5-ci-39847579502/{acceptance-summary,published-readback}.json.

v0.2.6 is published, targeting a0a34d77f0f21cac27b69a69c85070a663605916.
CI 39858964129 passes all 17 jobs: each Linux/Windows Python 3.10-3.13 cell passes
1108 tests without failures, errors or skips and all seven signing variants. Both canonical
source/native-wheel clean-install jobs pass. Fresh source and exact Linux CI-wheel oracles
each verify all 884,805 original classes/owners and every snapshot DEX byte. Published asset
hashes match fresh downloads and GitHub server digests. Receipts:
artifacts/acceptance-0.2.6-ci-39858964129/{acceptance-summary,published-readback}.json.
This input-integrity increment does not establish a startup, total-memory or workflow win.
Older version labels identify their original scope and evidence, not approval of a later
candidate; receipts must not be retroactively relabeled.

The v0.2.6 implementation rechecks file identities after the final complete hash, including a freshly
reopened path. All identities use fstat rather than mixing Windows path-stat timestamps.
Both container preparation and archive reads reject late content changes and replacement;
all original full hashes, DEX checksums, duplicate checks and snapshot isolation remain.
Failed-before receipts, final regression results and the non-adopted parallel-hash experiment
are retained under artifacts/release-renumber-20261022/increment026-*.
The experiment's three-round preparation timings are mixed and do not establish a speedup.
Its runtime differs from the released serial-hash fix and does not describe that runtime.

v0.2.7 is published and latest, targeting f7efd9a0f907280c31993b95535ec85ee5bf4494.
CI 39866704262 passes all 25 jobs. All eight Linux/Windows Python 3.10-3.13 source
cells pass 1132 tests without failures/errors/skips and seven signing variants each.
All eight distribution cells pass the full suite for both the canonical sdist and exact
native wheel. Fresh source and CI-wheel ownership receipts each verify all 884,805 owners
and snapshot DEX bytes; source fuzzy oracles verify all 108,151 selected sites across
86,473,182 instructions. The wheel additionally verifies all 2,914,002 Taobao call sites,
2163 selected string sites and nine bounded graph cases. Published assets match fresh
downloads and GitHub digests. Receipts:
artifacts/acceptance-0.2.7-ci-39866704262/{acceptance-summary,published-readback}.json.

The v0.2.7 query-memory implementation uses one read-only mapping and pinned native buffer per
stored DEX; compressed members and builds without that capability retain owned bytes.
The complete CRC, ZIP local-name/overlap checks and checked cursor remain mandatory.
Python 3.10 uses a native cp310 wheel; Python 3.11+ uses cp311-abi3 because the public
[buffer API entered the Stable ABI in 3.11](https://docs.python.org/3/c-api/buffer.html).
The package CI matrix now tests both wheel tiers
against the same canonical sdist on every supported interpreter and platform. Full-result diagnostics and their mixed
timing outcomes are recorded in GOAL_02X.md; no overall speed or total-memory win is claimed.

The v0.2.8 candidate dictionary-encodes prepared DEX ownership; it does not change the DEX
decoder, native buffer path or snapshot format. Five alternating preparation-only rounds
against v0.2.7 verify identical complete metadata, ordered class/owner hashes and private
snapshot hashes for each original APK. Owner-file sizes (before / after, bytes) are
5,955,584 / 4,673,536 (Taobao), 11,255,808 / 8,294,400 (WeChat) and
27,541,504 / 19,992,576 (Douyin). Preparation medians are 1.3484 / 1.1736,
2.2570 / 2.1293 and 5.0610 / 5.0386 seconds. Total retained files decrease only
about 1-2 percent; raw DEX snapshots remain. Sampled process RSS does not establish a
consistent reduction. These are direct preparation diagnostics, not process-start-to-first
MCP or competitor evidence. Tiny/empty directories incur an extra fixed SQLite page.
Receipt: artifacts/release-renumber-20261022/increment028-owners-before-after.json.
Fresh full-source, real-MCP, independent ownership, Windows and exact-package acceptance
are required before publishing this candidate. Overall performance/workflow closure stays open.
The first candidate CI (39899889877) is not accepted: its Windows 3.10 distribution job
uses Python 3.10.11 and fails because tarfile lacks the newer extraction-filter argument.
The acceptance extractor now preflights paths/types/duplicates and copies regular files
into an empty temporary directory without depending on that API. Fourteen new regressions
include a legacy-API simulation and rejected traversal/link/special-file inputs. The original
failure log and red/green regression receipts remain under increment028-*; all final commit
and package gates must be refreshed rather than relabeling that failed candidate.

The v0.2.5 directory-only five-round before/after diagnostic uses the same Python/runtime/input,
four inherited CPUs and alternating subprocesses. Every inventory name and retained ZipInfo
slot matches stdlib. CPU medians (v0.2.4 / new reader) are 0.08159 / 0.04712 seconds on Taobao,
0.26339 / 0.13073 on WeChat and 0.87671 / 0.56246 on Douyin. Peak directory-process RSS changes
are small; immutable snapshot/owner bytes are unchanged. A full preparation diagnostic checks
complete metadata, all owner rows and field-query pages against v0.2.4, but wall-clock results
are mixed: the Douyin median is slower. No universal startup or total-memory improvement is
claimed. Both receipts are increment025-{directory,preparation}-before-after.json under
artifacts/release-renumber-20261022. Their direct-worker timings are not real MCP acceptance.

The selected increment adds literal string-search-to-use-site handoff, a checked 32-bit jumbo
operand path and native ASCII pool matching with strict Unicode fallback. A profile of the
first correct implementation attributed most query cost to Python decoding of every pool
entry. The common ASCII matcher now uses linear-time substring matching; even nonmatching
ASCII entries retain length validation and non-ASCII entries retain strict modified UTF-8
decoding. The same matcher also serves type filters, so their accuracy must be revalidated.

Alternating three-round real-stdio string trials use the pinned unmodified installed competitor,
the same interpreter/input and actual inherited CPU affinity. Cold-batch / process-start-to-first
medians in seconds (ours versus competitor):

| APK | CPUs | Cold string query | Process start to first result |
| --- | --- | --- | --- |
| Taobao 10.62.0 | 4 | 0.6325 / 1.8091 | 3.2130 / 3.3581 |
| WeChat 8.0.74 | 2 | 0.6809 / 3.6947 | 4.0617 / 5.1220 |
| Douyin 39.1.0 | 4 | 1.9230 / 6.6112 | 8.3953 / 8.8902 |

Receipts: artifacts/release-renumber-20261022/increment024-taobao-affinity4-ascii-pool.json,
increment024-wechat-affinity2-ascii-pool-512mib-8gib.json and
increment024-douyin-affinity4-ascii-pool-512mib-8gib.json. All trials and before/after identities
pass. Taobao also retains the slower pre-optimization receipt. Two failed WeChat configurations
remain explicit: 128 MiB was below the input's expanded DEX size; 512 MiB with a 4-GiB session
ceiling could not accommodate the existing conservative preparation reservation. Successful
large-input runs explicitly allow 512-MiB expansion and an 8-GiB common external temporary-file
ceiling. These are configuration changes, not weakened product bounds. OS caches are retained
and other desktop processes may introduce noise. Within-product cold/warm structured equality
is checked; cross-product grouped totals do not prove site equality. Independent full-site
oracles and final cross-platform/package gates were subsequently completed for v0.2.4 above.
The snapshot/tmpfs, other workflows and universal startup claims remain outside these wins.

Historical v0.2.3 pre-freeze evidence: the Linux matrix passed 989 tests on each of
Python 3.10-3.13, with zero
failures/errors/skips and unchanged runtime hashes. Its supported-upgrade environments use
Pydantic 2.14.1; all 23 schema-cache/fallback tests also pass on locked Pydantic 2.13.5. Ten
new distribution-identity regressions additionally reject source/data, version and native
accelerator drift. These were intermediate results, superseded by the accepted 1019-test
CI run above; they do not approve a later increment.

The first full CI attempt (39820634142) failed and was not released. It exposed two actual
compatibility defects absent from the older local interpreters. Python 3.13 dedents compiled
docstrings, unlike 3.10-3.12: input-cache records now canonicalize descriptions for generation
checks, while public SDK tools still receive each live function's exact original docstring.
Latest zipfile backports can keep bit 11 in a live ZipInfo while clearing it in an ASCII
filename's local header. The snapshot reader accepts only that ASCII-equivalent encoding
difference and verifies the exact local filename bytes; encryption, descriptor, compression
and non-ASCII flag mismatches still fail. CRC, DEX integrity and original input hashes remain
mandatory. Nine new regressions bring the final suite to 1008 tests per matrix cell. Failed
logs/XML are preserved separately; all final CI/package/accuracy receipts must be refreshed.

Release policy: the authorized withdrawal is complete. New main merges, release tags and
assets must wait for that increment's frozen Linux/Windows, installed sdist/wheel, signing,
stability and accuracy gates. An incremental release does not close remaining overall deficits.

Core references, discovery, structure and streaming indexes now use checked native DEX
boundaries, with an optional CPython stable-ABI C accelerator and an independent Python
fallback. Neither needs JADX or Java. ASC remains the exact-method Smali engine; Java
decompilation is explicit opt-in only. DEX 041 normalization uses separately pinned
standalone dexlib2 3.0.9, not a JADX distribution. Installation does not download a backend.

`search_refs` adds a one-pass union with literal owner/name filters, omitted member names,
exact prototype/type filtering, read/write selection and global pagination. The graph index
can build call relations only. Immutable session readers can run concurrently; completed
pages retain bounded host caching without keeping whole APK objects or workers resident.

Startup still performs original integrity and duplicate-class checks before reporting ready.
Actual MCP progress reports snapshot/class-directory completion; heavy indexes remain lazy.
Do not compare this validated-ready contract to a competitor's path-registration time as if
both performed the same work. Still report both measured end-to-end times without adjustment.

Preparation now streams central-directory records instead of materializing a second complete
directory byte buffer and retaining a ZipInfo for every resource. All names still participate
in shared unsafe-name/NUL/duplicate/special-file validation, inventory limits, nested provenance
collision checks and next-local-header bounds. Only DEX/class/JAR/APK metadata is retained.
Resource browsing keeps ordinary full ZipFile inventories; it never sees a partial inventory
disguised as complete. Original before/after archive hashing, selected-entry ZIP CRC and strict
DEX checksum/signature validation remain unchanged. No new dependency or Java backend is added.

The custom directory reader is isolated in preparation_zip.py and keeps stdlib member opening,
decompression, local-name matching and CRC errors. Its private stdlib directory hooks require
explicit compatibility tests: ZIP64 security-fix backports differ even within Python minor
versions. Tests compare every available ZipInfo slot and member bytes with ordinary ZipFile,
including prefixes, comments, descriptors, Unicode, malformed extras and omitted-resource
safety/overlap/inventory checks. The 39-case reader suite passes separately on Linux Python
3.10-3.13; 139 preparation/container/directory/real-transport cases pass without skips. These
are development receipts, not final Windows or distribution acceptance.

The host registers precompiled output schemas through the public MCP SDK 2.2 Tool/FuncMetadata
interfaces. The package includes `output_schemas.json`, bound to contract source, exact Pydantic
version and schema digest. Missing/stale assets regenerate current schemas; strict SDK output
validation remains enabled and lazy. Check the generated asset with
`uv run python scripts/compile_output_schemas.py --check` (regenerate without `--check` after
contract changes). Installed distribution tests compare every schema to the current TypeAdapter.
Input schemas are also packaged in `input_schemas.json`, bound to server/registration sources,
exact SDK/Pydantic versions and a content digest. On a cache hit, public SDK Tool/FuncMetadata
objects advertise the unchanged schema; their input-validation delegate constructs the original
SDK model on first use and retains its JSON-string parsing, defaults, validation and Context
injection. Unknown functions and stale/malformed caches use ordinary SDK registration instead.
`uv run python scripts/compile_input_schemas.py --check` independently rebuilds all 18 original
SDK registrations and compares them. Both compiler checks run on every CI Python/OS matrix cell.
Native workers share host path/paging checks without eagerly importing the host configuration,
runner or CLI. CLI-specific infrastructure loads only for explicitly selected CLI operations;
the same external bootstrap, cancellation, process-tree and memory ceilings still supervise it.

Reproduce same-interpreter, same-input, alternating fresh-stdio trials with the unmodified
competitor at `848c711f1d80a1c2577283f1fa5f475ff734aa40`:

```sh
uv run --with ./artifacts/aimard-asc-mcp python scripts/benchmark_competitor_runtime.py INPUT.apk \
  --rounds 3 --workers 2 --graph-depth 3 --output matched-runtime.json
```

The harness preflights the actual installed competitor Python source tree against the pinned,
clean checkout before starting trials. Missing packages or stale/different installed code fail
early. Reports include interpreter path, package origin and every competitor Python-source hash;
the same match is required again after all trials. A source SHA alone is not evidence that the
matching installed package was executed. The 39-case harness/wrapper selection covers package
identity, complete structured cold/warm equality, timing boundaries, sampled storage enforcement
and inherited CPU-budget enforcement: cpu-budget-monitor-zero-skips.xml.

The pinned competitor passes its outer pool's worker_count into an inner per-query process
pool. Matching worker settings is therefore not an aggregate CPU cap. Current reports add
cpu_budget_version=1 and an explicit logical-CPU affinity set of size workers, inherited from
the same Python/psutil wrapper before product imports. Wrapper time/RSS is included for both;
only the owned server tree is modified, never the benchmark parent or unrelated processes.
The monitor samples each descendant's nonempty subset mask after transport initialization.
An escaped/unreadable mask stops that trial's processes and fails it; an already-exited process
does not count as a successful sample. Every passing real trial requires actual samples.
Unsupported platforms or requests exceeding available affinity fail rather than silently
weakening the budget. Historical reports without this version match settings, not a hard
aggregate logical-CPU limit. Do not compare their numbers as a controlled optimization ratio.

The report records full runtime hashes, real progress, cold/warm calls, concurrent batches,
aggregate descendant RSS, output and timeout failures. Both implementations share external
180-second/4-GiB limits; OS caches remain intact. A competitor timeout is not a completed
graph timing or evidence of our graph completeness. Verify every emitted graph site with
the independent decoder and complete method/field rows and diagnostics against the frozen
JVM oracle (`benchmark_reference_scan.py --native`). Pilot results are not release authority.

Timing version 2 records decoded-response arrival directly, including the complete cold
batch's first-result timestamp, and saves the potentially multi-megabyte report only after
all measured calls finish. Earlier report writers ran inside call-finalization paths; their
per-call seconds exclude that I/O, but ready/batch and derived end-to-end metrics can include
it. Keep those original receipts intact and label their timing limitation instead of silently
rewriting them or mixing the two methods. New receipts include timing_version and harness
SHA-256. The expanded nine-case fake-transport regression checks that report persistence happens
only after close, ready/first-result metrics stop at the correct received responses, regular-file
accounting excludes symlinks, and a sampled temporary-byte cap fails both implementations.
Temporary-file logical/allocated bytes are sampled in a background thread every 0.2 seconds,
separately from RSS; both implementations share the same external temporary-byte cap. Allocated
bytes use st_blocks if available (otherwise null). Peaks are sampled lower bounds, and missing
or failed storage measurements cannot pass a trial. These are command-flow unit regressions,
not independent HTTP performance measurements.

Preparation overlaps ownership insertion with the next DEX copy, but scans only closed/flushed
members and releases every mapping before the enclosing ZIP grows. SQLite stays on one owner
thread, at most one DEX's names remain live, and the pending database only becomes owners.sqlite
after all original-input validation succeeds. Error/metadata/late-input/hash cases must leave no
ready metadata and no background writer preventing cleanup. Raw-file, archive, 041 normalization
and pure Python fallback semantics remain covered. The 257-case targeted receipt,
pipelined-directory-and-path-zero-skips.xml, includes selected real stdio/HTTP investigation,
fuzzy references and bounded graphs, but deliberately deselects 52 other integration cases.

The newer compact-directory-targeted-zero-skips.xml passes 281 cases with the same 52-case
deselection. It includes real owner-writer timeout/cancellation, cleanup/recovery and compact
key ordering. Linux source checks on Python 3.10-3.13 each pass 168 cases with zero skips
(compact-directory-py3.{10,11,12,13}.xml). These receipts predate five separately passing
installed-package identity harness cases and are not fresh native-wheel or Windows evidence.
Class-directory format 1 uses internal CESU-8 keys with exact UTF-16 ordering; format 0 is
read-only compatible, and unknown formats are rejected. The ownership verifier independently
encodes original class names one UTF-16 code unit at a time rather than reusing product codecs.

After shortening validated root-inventory lifetime, the current selection passes 288 cases
with zero skips and the same 52 deselections (released-inventory-targeted-zero-skips.xml).
Linux source checks on Python 3.10-3.13 each pass 214 cases without skips, including containers
and all 20 harness cases (released-inventory-py3.{10,11,12,13}.xml). Three fresh full original-APK
class/ownership/snapshot verifiers also pass (released-inventory-{douyin,wechat,taobao}-full-ownership.json).
These are targeted development receipts, not proof of the final complete release matrix.

The checked ASCII directory selection additionally passes 377 native/graph/structure/index
cases and 320 preparation/container/benchmark/real-transport cases (zero skips; the latter
deliberately deselects 52 other integration cases). Receipts:
checked-directory-native-zero-skips.xml and checked-directory-targeted-zero-skips.xml.
Three full original-input owner/snapshot checks pass after that change:
checked-directory-{douyin,wechat,taobao}-full-ownership.json. Strict Unicode/duplicate handling,
CRC, legacy accelerator and pure Python fallback remain required, not performance shortcuts.

The following duplicate-stamp selector revision passes 397 native/graph/structure/index cases
without skips (duplicate-stamps-native-zero-skips.xml), including twenty additional member-ID/
duplicate/class-local-generation regressions. Its per-call table is at most 524,292 bytes and
must be freed on every exit; there is no persistent host state. Three fresh alternating rounds
against the frozen JVM oracle match every method/field row and diagnostic, 24,461/332 sites and
12,495,817 decoded instructions, with unchanged input/runtime/oracle sources:
duplicate-stamps-full-reference-parity.json. The real-MCP four-CPU field receipt still trails
the competitor's complete first result by 0.6832 seconds at the median. See
NATIVE_QUERY_VALIDATION.md for separate stage, memory and CPU-allocation details. No feature
freeze, Windows approval or final source/wheel package acceptance follows from these checks.

After the duplicate-stamp revision, all three full owner/snapshot oracles pass again with
unchanged source/input and identical class-owner digests:
duplicate-stamps-{douyin,wechat,taobao}-full-ownership.json. Python 3.10-3.13 each pass
331 Linux source cases with zero skips (duplicate-stamps-py3.{10,11,12,13}.xml). The
real stdio/HTTP investigation/fuzzy/bounded-graph selection, with preparation/container and
benchmark regressions, passes 320, zero skips and 52 deliberate integration deselections
(duplicate-stamps-targeted-zero-skips.xml). Existing interpreters load the rebuilt shared
stable-ABI source extension; these are not new wheel/sdist installations or Windows results.

The incoming graph-filter revision additionally passes 374 native/graph/structure and real
acceptance-script cases with zero skips (frontier-filter-native-transport-zero-skips.xml).
The graph script now uses artifact preparation, frontier results, full warm-response equality
and Java-disabled stdio; it no longer requires obsolete implicit-full-index fields. A larger
expansion budget also scales its worst-case session reservation. Its independent decoder
checks canonical DEX-to-original-entry mapping, exact emitted instruction operands/offsets/
opcodes and polymorphic prototypes. A failed recheck clears any earlier independent pass;
transport success and independent-site success are separate fields. Reproduce with:

```sh
uv run python scripts/benchmark_call_graph.py INPUT.apk --expanded-mib 512 --output graph.json
uv run --with androguard python scripts/benchmark_call_graph.py INPUT.apk \
  --output graph.json --verify-sites
```

The input, runtime and verifier must remain unchanged between these commands. The standalone
pilot is not a matched competitor timing. The separate matched product-revision receipt has
mixed per-round outcomes despite a lower cold median; do not call it a robust startup win.
See NATIVE_QUERY_VALIDATION.md for exact values and the remaining release requirements.

Run the full original-input ownership/snapshot oracle separately from timing trials:

```sh
uv run python scripts/verify_preparation_directory.py INPUT.apk --expanded-mib 512 \
  --output ownership-oracle.json
```

This compares every original DEX class and owner using accelerator=False, all snapshot DEX bytes
by SHA-256, counts/provenance and the entire common metadata envelope. Fixture corruption tests
must fail on a missing class, wrong owner or damaged snapshot. The verifier keeps a full oracle
dictionary only on the acceptance side; it is not a production memory policy or performance run.
All three large original APKs pass on the current candidate: 551,538/233,555/99,712 classes for
Douyin/WeChat/Taobao, with stable input/runtime hashes. This does not replace full call-site and
graph completeness oracles or final cross-platform installation gates.

Do not omit RAM-backed storage from memory conclusions. On this host, findmnt identifies /tmp
as tmpfs; the current Douyin receipt retains about 500 MB of immutable snapshot/directory files.
Warm host RSS around 79 MB is therefore not a 79-MB total memory footprint or a total-memory
win over the competitor. Record filesystem placement and separate file/RSS measurements; do not
add unrelated phase peaks as an exact simultaneous total. Startup field latency, startup RSS
and retained RAM-backed storage remain open candidate gaps, not accepted release tradeoffs.

The large fuzzy union also has a complete independent instruction-decoder check, rather
than only checking the first page or trusting another implementation's byte candidates:

```sh
uv run --with ./artifacts/aimard-asc-mcp python scripts/verify_fuzzy_references.py INPUT.apk \
  --output fuzzy-oracle.json
```

It compares every matching call site and matched target, plus the full instruction count,
against Androguard method-ID pools and sequential instruction decoding. It does not turn
static declared operands into resolved virtual dispatch, reflection or JNI targets.

Frozen workload results, startup/end-to-end caveats and graph failure semantics are
recorded in [NATIVE_QUERY_VALIDATION.md](NATIVE_QUERY_VALIDATION.md). Verify the full
persisted call-index multiset separately from bounded graph responses:

```sh
uv run --with ./artifacts/aimard-asc-mcp python scripts/verify_call_index.py INPUT.apk \
  --output call-index-oracle.json
```

The 0.2.3 candidate can explore bounded call-graph frontiers without first building a
whole-APK index. Full instruction validation remains mandatory. Up to 32 BFS nodes share
a scan; dense batches shrink before the original disk-bounded index fallback is used.
An existing valid session index still takes precedence; explicitly configuring the durable
xref cache preserves the original calls-only build/restore path. Frontier responses identify
`backend=native-dex-frontier` and omit `index`; `query_cache.hit` describes exact-page reuse,
not creation of an index. Compare all graph fields, ordered nodes/edges, diagnostics and
truncation against a freshly built full call index:

```sh
uv run python scripts/verify_frontier_graph.py INPUT.apk --root 'Lexample/Main;->run()V' \
  --depths 1 3 5 --output frontier-parity.json
```

This direct-worker comparison is accuracy evidence only. Real stdio/HTTP and matched
fresh-process latency, preparation, RSS and disk/tmpfs receipts are separate release gates.

## v0.4.1 cold-query gate, 2026-10-22

The scanner optimization preserves fresh supervised workers and the existing 512-MiB JVM
heap bound. New differential checks compare instruction opcode, code-unit offset, size,
member operand and polymorphic second operand against the pinned decoder. They also compare
every cached method/field descriptor with the public reference pools. Regressions cover
packed/sparse switches, wide instructions, array payloads, unknown opcodes, truncated headers,
oversized/overflowing lengths, prefix-name ordering and pagination. The Java oracle is included
in the source package, including a malformed unreferenced-prototype fail-closed regression,
and exercised against installed wheel code during clean-distribution acceptance.

Large-APK complete-result parity uses the frozen v0.4.0 source and the unchanged 12-DEX
Taobao APK. All 24,461 method sites and 332 field sites, not just the first page, must match
with all 12,495,817 instruction counters and resolution diagnostics. Reproduce with:

```sh
uv run python scripts/benchmark_reference_scan.py INPUT.apk \
  --baseline-source BASELINE/MethodBridge.java --java JAVA \
  --jadx-home JADX_HOME --rounds 3 --output full-parity.json
```

Performance receipts are development evidence, not permission to release. The frozen candidate
must pass the complete Linux suite, the native Windows/Linux Python 3.10-3.13 matrix, real
stdio/HTTP tests, clean sdist/wheel acceptance, independent signing and both stability jobs.
Candidate commits on the acceptance branch are allowed; main/tag/release must wait for every
job to pass. Publish only the exact wheel/sdist bytes from that successful CI run. The release
notes must identify the tested commit, successful run and artifact SHA-256 values.

The preceding v0.4.0 release was approved by
[CI 39667389148](https://github.com/cnlnn/droidasc-mcp/actions/runs/39667389148)
at `319ef0ca900188a19bf30b6b8d0e42a29e03a43f`: all 16 jobs passed, including 426 tests
with zero failures/errors/skips in each of the eight platform/Python suites. That is historical
evidence only and is not reused for this candidate. The sections below retain their original
development context.

## v0.4.0 feature-frozen gate, 2026-10-22

The competitor's main commit was rechecked as `848c711f1d80a1c2577283f1fa5f475ff734aa40`.
The AST audit reports 25 tools, two resource templates, three prompts and 87 parameters,
with zero inventory omissions. [The source map](COMPETITOR_API_AUDIT.md) separately records
behavioral tests and intentional interface differences; an inventory check alone is not parity.
The final focused structural/container/real-transport regression passed 43 tests. The independent
signing oracle passed seven variants with the original APK unchanged. Local 20-second/two-worker
stability completed 190 operations with no errors or live children, unchanged five handles and
1,314,816 bytes host RSS growth. Thirteen DEX/index lifecycle cycles ended with no child,
session, storage, reaper or handle growth (host RSS growth 1,388,544 bytes).

These development results do not approve a release. The feature-frozen full Linux suite,
native Windows/Linux Python 3.10-3.13 matrix, real stdio/HTTP, both clean sdist/wheel installs,
independent signing and both stability jobs must all pass on the candidate commit. Only then
may main and the v0.4.0 release advance. The release notes must link the exact successful CI run,
tested commit and published artifact hashes. Older receipts below apply only to their named
versions/commits and must not be reused as this candidate's acceptance.

## Index/Rust candidate, 2026-10-21

Local Linux/Python 3.13 regression: **248 passed, zero skips**, 345.29 seconds,
with Python ASC 0.1.2.post3, JADX 1.5.5/JDK 17 and the pinned native Rust binary.
An additional real stdio/HTTP index/guidance rerun passed both transport cases.
Thirteen concurrent session lifecycle cycles, including index construction/reuse,
ended with zero live children, zero remaining storage/sessions, no reaper thread,
zero handle growth and 1,310,720 bytes host RSS growth.
These numbers describe the prior index/Rust baseline, not the later discovery/cache candidate.
The discovery/cache regression initially returned 257 passed / 2 failures because old transport
assertions compared cache-hit metadata literally. Both transport reruns passed after asserting
identical evidence separately from the expected cache-hit transition. A new independently
assembled boundary/payload reference regression also passed. Complete candidate package and
Windows gates are tracked separately; these narrow checks do not replace them.

### Clean-package regression at `88de70b`

On 2026-10-21, `scripts/verify_dist.py` extracted the built sdist into a new temporary
project, installed its locked dependencies, then replaced the editable package with the
built wheel and verified that imports came from `site-packages`:

| Installation | Result | Duration |
| --- | --- | --- |
| Clean sdist | 260 passed, zero skips | 440.67 s |
| Wheel replacing sdist installation | 260 passed, zero skips | 377.11 s |

Both runs supplied the public Android and R8/Kotlin fixtures, their mapping, JDK 17,
JADX 1.5.5 and the pinned optional Rust binary. The package-content assertions and
installed CLI `--help` also passed. These are Linux/Python 3.13 results, separate
from the native Windows/Linux [CI run](https://github.com/cnlnn/droidasc-mcp/actions/runs/39618031586).

Downloaded JUnit artifacts from that exact commit establish **260 passed, zero
failures/errors/skips** in each of the eight Windows/Linux Python 3.10-3.13 jobs.
Linux suite durations were 265.14-284.76 seconds; Windows durations were
284.36-412.77 seconds. Counts were read from the XML, not inferred from job status.
The complete run finished successfully, including both native Rust builds, both
stability jobs and both clean-distribution jobs. This is the `88de70b` baseline,
not evidence for subsequent durable-cache changes.

### Durable-cache completion audit

The previous index persisted only within its session. The new opt-in durable store
closes the cross-session/restart requirement without retaining inputs by default.
Targeted acceptance passed **12 tests** on Linux, including real stdio/HTTP server
restarts with an intentionally unavailable Java executable during reuse, identical
field rows, an entirely new service instance, corrupt/oversized manifests, checksum
failure, TTL/quota eviction, separate-process writers and lock recovery after a killed
writer. The existing real index-JVM cancellation tests still passed. The subsequent
complete local Linux/Python 3.13 run passed **270 tests, zero skips**, in 444.04 seconds
with all public fixtures and both optional backends. Local JUnit evidence is
`artifacts/validation/persistence-tests.xml`. The native Windows/Linux and clean-package
gate for implementation commit `9712467` is
[CI 39622441029](https://github.com/cnlnn/droidasc-mcp/actions/runs/39622441029);
it exposed a Windows/Python 3.11 concurrent-lock initialization failure. Two
first-time writers could observe an empty lock file, then one attempted a buffered
initialization write after another had locked that byte. The fix removes lock-file
writes entirely: Windows `_locking` supports byte ranges beyond EOF, as documented
by [Microsoft](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/locking).
A regression asserts the lock remains empty across repeated acquisition, alongside
the existing separate-process publication and killed-writer tests. The corrected
suite contains 271 tests. The corrected implementation at `625aa32` passed
[CI 39624408098](https://github.com/cnlnn/droidasc-mcp/actions/runs/39624408098),
including all eight Windows/Linux Python 3.10-3.13 suites: downloaded JUnit XML
records 271 tests and zero failures/errors/skips in each. Both native Rust builds,
both stability jobs and both clean-distribution jobs also passed. These results
belong to that commit, not subsequent performance changes.

The same 12-DEX Taobao APK was then tested through two separate real stdio MCP server
lifetimes. The first server built and retained the complete 2,349,907,968-byte index in
**471.5827 seconds**. After closing the session and exiting that server, the second server
opened a fresh immutable session in **12.0965 seconds**, restored/verified the saved index
and returned all **332 field-reference rows in 3.3324 seconds**. Every row and the complete
count matched the pre-index streamed result. Java was intentionally unavailable in the
second server, proving reuse rather than rebuilding. The original APK SHA-256 was unchanged.
Reopening plus restore/query therefore cost about **15.43 seconds**, not 3.33 seconds total.

This run explicitly used a 4 GiB per-session index quota, 6 GiB durable-cache quota and
900-second worker timeout. Defaults do not fit this index. First-build cost remains
substantial and is not a competitor cold-query speedup. The durable store retains derived
identifiers/relationships until eviction; it is opt-in and does not retain the original APK.
Reproduce with `scripts/benchmark_persistence.py <apk> --cache-dir <private-directory>
--output <report.json>`. Local result: `artifacts/reverse-acceptance/taobao-persistent-index.json`.

| Goal requirement | Implementation and independent acceptance evidence |
| --- | --- |
| Reusable persistent reverse index | Atomic SQLite session index plus opt-in content/backend-bound durable copies; full restart with Java unavailable on both transports and the large APK above; corruption, quota, killed-writer and multi-process tests in `test_durable_index.py`. |
| Type/annotation/declaration relationships | `IndexBridge.java` and `test_index_parity_and_type_oracle`: independently authored nested annotations, declaration types, arrays, superclass/interface relationships and instruction offsets. |
| Representative large-APK performance | Taobao all-DEX full index and cold/warm queries; Taobao and Douyin Python/Rust backend stdio checks, retained hashes, measured limits and explicit coverage caveats below. |
| Optional Rust integration and source verification | Pinned public CLI adapter, native process supervision, explicit backend selection; source/revision and unsupported/error coverage documented in `RUST_BACKEND.md`; Linux/Windows native builds and transport tests in CI. |
| Runtime-debugging boundary | `RUST_BACKEND.md` separates static operands from reflection/JNI/loaded DEX and debugger control; dynamic integration is not presented as implemented. |
| Local and Windows/Linux gates | Full local regression plus strict fixture/no-skips, eight OS/Python combinations, clean sdist/wheel, stability and Rust jobs; use the exact commit's CI conclusion. |
| Candidate delivery only | Work remains on `codex/dex-input-analysis`; no merge, tag or release is part of this acceptance. |

### Large-sample index and backend evidence

Real stdio MCP, all 12 top-level DEX files from local Taobao 10.62.0, 99,712 classes:
schema 3 published **2,349,907,968 bytes** (2.19 GiB) under the unchanged 4 GiB test quota.
It indexed 1,409,112 field, 2,914,002 method and 13,879,251 type relationships, with
1,085,761 definitions. Build time was 460.0459 seconds and sampled descendant RSS
peaked at 664,887,296 bytes. The first two storage designs exceeded 4 GiB and failed
without publishing partial indexes; their local reports are retained rather than hidden.

| Exact query | Streamed seconds | Indexed seconds, three repeats | Matching rows |
| --- | --- | --- | --- |
| `String.equals(Object)` | 9.8224 | 0.6328 / 0.5660 / 0.6814 | 24,461 |
| `Build.MODEL` | 7.3267 | 0.4092 / 0.4040 / 0.3976 | 332 |
| `Activity` type relationships | not measured | 0.8618 / 0.7445 / 0.5558 | 24,910 |

For the method/field pair, complete counts, diagnostics and the first 100 rows
matched the independent streamed implementation on every repeat. This is not
exhaustive equality of all rows or all queries. The APK hash was unchanged and
the session was closed. The default 256 MiB index quota and 180-second timeout
are insufficient for this sample; the benchmark explicitly uses 4 GiB and 900
seconds, with a 6 GiB session budget. Index cost is substantial: do not auto-build
for a single exact-reference lookup. Member discovery now uses a declaration-only
path without building the full index.

### Interactive discovery and exact-page reuse

On the same Taobao APK, real stdio MCP with no full index:

| Query | First seconds | Repeated seconds | Matches |
| --- | --- | --- | --- |
| Method descriptor contains `->equals(` | 4.0018 | 0.6646 / 0.3350 / 0.3183 | 1,372 |
| String pool contains `https://` | 2.5270 | 0.4198 / 0.3318 / 0.3156 | 1,723 |
| Exact `String.equals(Object)` references | 8.6978 | 0.3165 / 0.2533 / 0.3211 | 24,461 |
| Exact `Build.MODEL` references | 9.3805 | 0.3272 / 0.3975 / 0.3231 | 332 |

The separate immutable session-open cost was **12.8858 seconds**, so opening and
the first member query together cost about 16.89 seconds. The declaration-only
query peaked at 635,822,080 bytes descendant RSS; the first exact method query
peaked at 749,490,176 bytes. Identical pages, counts and diagnostics matched on
all three cache repeats (excluding cache metadata). Different pages may rescan.
Input SHA-256 was unchanged; the session closed successfully. These are single-host
measurements, not controlled speed rankings. The harness still explicitly sets
4 GiB / 900 seconds, although these queries do not build an index and the page
cache itself is capped at 4 MiB. Reproduce using `scripts/benchmark_backends.py
<apk> --interactive`; raw report: `artifacts/reverse-acceptance/taobao-interactive-benchmark.json`.

### Snapshot and exact-reference latency follow-up, 2026-10-22

The next candidate stores temporary immutable DEX snapshots without ZIP compression.
Header/table bounds, SHA-1/Adler-32/SHA-256 checks, input-change detection, public-CLI
class counts and duplicate-class rejection remain in place. This trades disk space for
preparation time: this sample has 112,915,728 uncompressed DEX bytes versus 43,386,976
compressed DEX bytes in the original APK. Existing session reservations already budget
twice the uncompressed input bytes; neither originals nor reservation limits change.

Exact incoming-reference scans now memoize descriptor comparisons by decoded member ID,
within one DEX and one method/field query. The bounded memo is 64 KiB per currently
scanned DEX. Repeated IDs avoid constructing reference objects and descriptors. Instruction
iteration, unknown/optimized-opcode rejection, code-unit offsets, dynamic diagnostics,
complete counts and paging remain unchanged; this is not a raw-byte pattern scan.

Fresh-server stdio MCP runs on the same Taobao sample, with no full index:

| Operation | Before | Stored snapshots only | Final candidate |
| --- | --- | --- | --- |
| Immutable session preparation | 13.2285 s | 0.8335 s | 0.8306 s |
| Exact `String.equals(Object)` references | 8.1295 s | 7.5193 s | 6.8328 s |
| Exact `Build.MODEL` references | 6.9239 s | 6.9822 s | 5.3987 s |

All runs returned the same 24,461 method and 332 field instruction rows by count, and
identical first-100-row SHA-256 values. All exact scans decoded 606,974 methods and
12,495,817 instructions with zero scan errors. Final identical-page repeats took
0.2466-0.3981 seconds. Original APK hashes were unchanged and all sessions closed.
The benchmark now records page hashes and decoder counters in its JSON report.
These are host-specific measurements, not a universal speed ranking or a CPU/RAM claim.

A separate engine-only comparison alternated fresh JVMs running pre-change `625aa32`
and candidate sources against the same original APK, three trials each. Method median
wall time was 8.7104 -> 7.5403 seconds; field median was 6.4034 -> 5.8103 seconds.
All 24,461 method rows, 332 field rows and every diagnostic matched on every trial.
The field rows also matched the previously saved independent Androguard decoder oracle,
bound to the unchanged APK SHA-256; this was reuse of that oracle, not a new oracle run.
Earlier trial reports, including a slower single candidate field run, are retained.

Regression fixtures deliberately reuse member ID zero for different methods and fields
in separate DEX files, exercise repeated invoke/static-range/read/write instructions,
and check exact results through stdio and HTTP. The stored-copy test checks exact bytes
and hashes in both the immutable bundle and the public-CLI per-DEX temporary archive.
Complete local/native/package gates must be read for the exact candidate commit, not
inferred from these narrower comparisons.

The performance implementation at `6e057e9` subsequently passed local strict acceptance
with **274 tests, zero skips** in 364.58 seconds. Clean sdist and installed-wheel runs
passed the same 274 tests in 385.44 and 392.32 seconds. The
[complete Windows/Linux CI run](https://github.com/cnlnn/droidasc-mcp/actions/runs/39632380156)
passed all 16 jobs. Downloaded JUnit XML confirms 274 tests and zero failures/errors/skips
in each of the eight Python 3.10-3.13 OS combinations. Both native Rust builds, stability
jobs and clean-distribution jobs passed. This is the performance baseline, not acceptance
of subsequent archive workflow additions.

Local evidence: `artifacts/reverse-acceptance/taobao-interactive-before-stored.json`,
`taobao-interactive-after-stored.json`, `taobao-interactive-optimized-final.json` and
`artifacts/validation/reference-memo-parity.json`. Private APKs and reports remain ignored.

The same real MCP adapter exercised both Python and Rust manifest/class/source/
string-reference operations on Taobao and Douyin 39.1.0 (53 DEX, 551,538 classes).
Class counts matched and original hashes were preserved. Rust reference coverage
remains explicitly unverified despite matching aggregate hit counts. These are
single-host exploratory timings, with other acceptance processes running; no
isolated competitor benchmark, universal speedup or full-source equivalence is claimed.

Local raw reports: `artifacts/reverse-acceptance/taobao-index-benchmark.json`,
`taobao-index-uncompacted-failure.json`, `taobao-index-schema2-failure.json` and
`aweme-rust-benchmark.json` in that directory. Private APKs and these local artifacts
are excluded from packages and Git. Reproduce with `scripts/benchmark_backends.py`.

## Reproduce

Candidate exact-method acceptance additionally needs the optional pinned backend:
`uv run python scripts/setup_jadx.py`, JDK 17 on PATH, and
`DROIDASC_MCP_JADX_HOME=/absolute/path/to/artifacts/jadx-1.5.5`.
CI verifies the upstream ZIP SHA-256 before extracting it. Use the newly built fixture (including
`MethodCases.java`) and the `complex` release fixture; set `ASC_TEST_EXPECT_FIXTURE=1`,
`ASC_TEST_APK`, `ASC_TEST_COMPLEX_APK` and `ASC_TEST_COMPLEX_MAPPING`, then run the full suite.
Strict fixture mode fails on skipped optional-backend tests as well as missing APK tests.
The optional Rust integration gates also need `uv run python scripts/setup_rust.py` and
`DROIDASC_MCP_RUST_ASC` pointing to its binary. CI builds the pinned native binary on
Linux and Windows and supplies it to the Python matrix and clean-distribution jobs.

Index gates cover full streaming-result equivalence, type declarations/instructions/nested
annotations, exact array identities, concurrent first-build serialization, stale backend
identity rejection, disk-quota failure without publication, and actual index-JVM cancellation
over stdio and HTTP with temporary-directory cleanup and successful recovery. Literal member
discovery checks overloads, same-name/different-type fields, arrays, case sensitivity, literal
wildcard characters, pagination and feeding discovered identities back into exact references.
The working index persists for the session lifetime. An explicitly configured durable
cache can retain a verified copy across restarts, within its separate budget/retention.
Large-corpus acceptance is a separate gate; small fixtures do not establish large-input
resource suitability.

New gates cover immutable sessions after source replacement/deletion, concurrent sample isolation,
warm/cold output equivalence, preparation capacity, TTL/close pinning, cancellation/failure cleanup
and normal server lifespan teardown. Exact-method transport gates check overload separation,
constructors, synthetic bridges, array signatures, native declarations, Unicode identifiers,
Java-to-Smali target preservation and actual descendant JVM cancellation/recovery. These are small
fixture checks; they do not establish equivalent Java correctness or speed on arbitrary obfuscation.

ASC post3 gates additionally reassemble native method Smali (debug info, native parameters and
catch labels) with the JVM disabled in the server configuration. Source-built Smali oracles verify
descriptor-exact cross-DEX references and instruction positions, undefined targets, polymorphic
call-site prototypes, pagination, single-shot/session equivalence and unknown-opcode rejection.
The independent Kotlin/R8 fixture proves obfuscated overload identity and continuation-to-workflow
references, with R8 mappings kept on the test side. Both MCP transports run these checks.
Field-reference gates use independently authored Smali positions for static, instance-wide and
object-array accesses, same-name/different-type fields, external and unused fields. They verify
read/write filtering before pagination, history independence, one-shot/session equivalence, input
hash preservation, invalid identities and fail-closed scanning even after matching earlier accesses.
Clean sdist/wheel verification requires `--complex-apk` and `--complex-mapping` alongside
`--fixture-apk`. Its per-command budget is 600 seconds to accommodate the additional JVM queries;
worker deadlines, cleanup latency assertions and the no-skips gate are unchanged.

Upstream inspection: [ASC dev-0.1.2-post3](https://github.com/MG1937/ASC/releases/tag/dev-0.1.2-post3),
tag commit `9216fe234e1fc80f3148ca42e361e67e3174d0e2`. The public CLI adds exact `--method` and
`--debuginfo` disassembly. Its implementation rebuilds the owning class DEX and passes the exact
prototype to the disassembler; it does not expose structured exact-method xrefs. Consequently,
native Smali uses that public CLI, while structured operands use the pinned dexlib2 API. Nothing
here claims to implement ASC-internal API access or a complete runtime call graph.

Method JVM scratch files and user-home state are confined to the parent-owned query directory;
cancellation tests plant a sentinel there and require both the JVM and directory to disappear.
Session eviction uses a monotonic access sequence, independently of the TTL clock resolution.
Windows pipe readers poll available bytes and observe a shutdown event rather than waiting for a
full buffered read or every inherited writer handle to close. Native tests retain an open writer
while stopping its reader, in addition to checking real Job Object process-tree cleanup.

```bash
uv sync --locked --extra dev
uv run pytest -q -s --junitxml=artifacts/validation/tests.xml -o junit_logging=all
ASC_TEST_APK=/absolute/path/to/a/local.apk uv run pytest -q -s \
  --junitxml=artifacts/validation/with-apk.xml -o junit_logging=all
uv run ruff check .
uv build
uv run python scripts/verify_dist.py dist/droidasc_mcp-0.2.2.tar.gz dist/droidasc_mcp-0.2.2-py3-none-any.whl
```

User-supplied APKs are read locally, never uploaded or included in test artifacts. Tests print
counts rather than APK contents; failure logs can contain assertion details and local paths.
Artifacts are gitignored. Local real-APK checks are skipped unless `ASC_TEST_APK` is supplied.
CI instead builds the repository's public-source [acceptance APK](../tests/fixtures/android/README.md)
and uploads only that generated APK for the other jobs to analyze.

## 0.1.1 release acceptance (Linux, Python 3.13)

- 41 tests passed with a local APK supplied, including all six tools over stdio and loopback HTTP.
- A clean sdist extraction passed 39 tests; installing the wheel into that isolated environment
  passed the same 39 tests. The two real-APK tests were explicitly skipped in both package checks.
  Wheel imports were verified to come from `site-packages`, not the development checkout.
- Four new regression gates were run before the fix and failed: late overflow accepted as success,
  reader failure swallowed, unrelated queries serialized, and missing `next_offset`. All now pass.
- Further gates cover same-query request coalescing, cache hits during an unrelated fill, decoding
  and sorting only once, decoded-memory budget rejection, and cache eviction based on object size.
- CI now uses `uv sync --locked` and validates source and wheel distributions, in addition to the
  existing Python 3.10-3.13 Linux matrix. Its remote result is separate from these local results.

The local JUnit output is `artifacts/validation/0.1.1.xml` (gitignored). Initial hardening results
below are retained as historical observations; timings and RSS deltas are workload-specific.

## Cross-platform CI

- GitHub Actions runs the test suite on `ubuntu-latest` and `windows-latest`, each with
  Python 3.10, 3.11, 3.12, and 3.13. Every test job uploads its JUnit results, including skips.
- A single Ubuntu job builds the sdist and wheel and uploads `python-distributions`.
  Both operating systems install these same artifacts on Python 3.13, then rerun the tests
  outside the original checkout. The distribution command uses Bash for glob expansion.
  GitHub Releases publish those artifacts from the successful tag run, without rebuilding them.
- An Ubuntu job builds the original test app with JDK 17, Gradle 8.13, AGP 8.9.2, Android SDK 35,
  and Build Tools 35.0.0. The same `acceptance-apk` artifact goes to every test/distribution job.
  No third-party APK download or private sample is involved.
- Always-on checks include stdio and loopback HTTP discovery, ping, synthetic ZIP metadata,
  rejected input, finite stdout/stderr limits, and timeout cleanup of a live parent and child.
- The two real-APK transport checks run in strict fixture mode in CI. Assertions cover the
  artifact's SHA-256, parsed manifest/package, known DEX classes, pagination, decompiled marker,
  and string/type/method/field reference callers. Missing fixture input is a test-session error.
  The same checks run after both source and wheel installation via `verify_dist.py --fixture-apk`.
- Process-state checks use psutil on both platforms. The cleanup-after-leader-exit unit test
  checks the platform's lifetime primitive; real orphan tests execute on both platforms.
  Strict fixture-mode CI fails if any test is skipped, including distribution acceptance.
- Dedicated stability jobs run concurrent uncached worker operations for 20 seconds on each OS,
  then require bounded host RSS/handle growth and no remaining child process.
- Cancellation acceptance abandons an in-flight MCP call, observes its real worker stop, and then
  successfully calls `asc_ping` on the same session. A separate real-process test covers the tree.
- Query-boundary acceptance sends option-shaped reference values over both transports and checks
  that an outside-root sentinel is unchanged. The upstream-reserved `--gui` query fails explicitly.
  Output-path probes use forward slashes, valid on both OSes; separate malformed string/type
  regex probes require explicit errors and a usable session, without changing engine semantics.
  Exact method/field lookups compare the default-package `Login` name with `LLogin;`, while fuzzy
  class queries retain their substring semantics. These checks also run after sdist/wheel install.
- Memory-limit acceptance deliberately exceeds a 96 MiB worker cap, checks the explicit failure,
  then runs a fresh operation to prove supervisor recovery.
- The matrix defines coverage, not a success claim. Inspect the commit's Actions run for results.
- This fixture is a small two-DEX Java app, not an obfuscated/large-multidex/Kotlin/native-code corpus
  or an Android runtime/UI test.

## Windows orphan regression

The pre-fix [native Actions run](https://github.com/cnlnn/droidasc-mcp/actions/runs/35515384740)
at `434925e` executed the previously skipped tests: every Windows Python job reported
42 passed, 1 failed, 0 skipped. The actual failure was a child still running after the
supervisor timed out; Linux passed. This is distinct from a platform-incompatible test.

Windows now uses `pywin32` Job Objects with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`. A trusted
bootstrap waits for a one-byte startup handshake before importing the target CLI module.
The supervisor assigns the process to its Job before sending that byte. The Job handle is
unnamed and non-inheritable; closing it cleans up associated descendants after their parent exits.
Failed assignment closes the Job and kills the waiting bootstrap; it does not fall back to an
unsupervised operation. The bootstrap restores the CLI's argv and stdin-at-EOF behavior.

Regression coverage includes a live parent, an exited parent, a grandchild holding inherited
pipes, successful completion with a detached-output child, output overflow, joined reader
threads, and repeated-operation handle/descriptor counts. Portable fault-injection tests check
Job configuration/assignment failures and startup gating; those mocks are not the native-kernel
acceptance evidence. A separate regression checks cleanup if reader construction fails.

## Android 16 device corpus (2026-09-21)

An ARM64 Android 16 device was accessed over ADB in read-only fashion. Only the installed base APKs
of four open-source applications were pulled into gitignored `artifacts/`; no application data,
accounts, configuration splits, or private APK was read. `scripts/validate_corpus.py` ran ping,
metadata, manifest, class listing, source, and string-reference operations successfully for each:

| Package/version | APK characteristics | Observed result | SHA-256 |
| --- | --- | --- | --- |
| Syncthing-Fork 2.1.3.0 | 59,098,704 bytes; Kotlin; 5 DEX | 35,591 classes; 3,415 `android` reference lines | `d3ae43e6d010d56c8e113aa609d194ccbf32699e63993cf6e05070549ae3bbb4` |
| Termux 0.118.3 | 113,880,067 bytes; Kotlin; 1 DEX; 8 native libraries | 2,696 classes; 155 reference lines | `e6265a57eb5ca363808488e3b01955958bed93bc0c8a0d281849b363b11027ec` |
| F-Droid 1.23.2 | 12,426,276 bytes; Kotlin; 2 DEX; 4 native libraries | 19,701 classes; 996 reference lines | `985f5181d48bb6bafd54083a048b391271e0ab28385881cc41294fb01a222762` |
| LocalSend 1.18.2 | 5,479,806 bytes; Flutter assets; obfuscated names; 1 DEX | 3,494 classes; 367 reference lines | `a34c6cc65f0da4668f7c84e1c50261a4294a2e1842475ed6aba8237aead95905` |

Split-delivered applications were assessed using `base.apk`; this does not claim analysis of their
ABI/resource split APKs. The corpus shows compatibility with these current files, not every APK
produced by the same frameworks or build systems. The generated JSON record remains local at
`artifacts/device-corpus-20260921/validation.json`.

The same four-APK corpus then completed a 300-second, two-worker stability run with 9,204 uncached
metadata/class-list operations. The MCP host grew by 1,208,320 RSS bytes, file descriptors remained
at 5, and no errors or live child processes remained. This is a bounded run on one Linux host, not
evidence of leak-free operation for arbitrary durations or samples.

## Large Android 16 device corpus (2026-09-21)

At the device owner's request, three current commercial base APKs were pulled read-only over ADB.
No application data, account data, or split APK was accessed, and the APKs remain gitignored and
are not redistributed. Under the 2 GiB worker-tree budget, all six operations completed:

| Package/version | APK characteristics | Observed result | SHA-256 |
| --- | --- | --- | --- |
| Douyin 39.1.0 | 364,994,058 bytes; 53 DEX; 276 native libraries | 551,538 classes; 4,047 manifest lines; 22,893 `android` reference lines; 3.545 s | `c2b49cb5f85b8432e9c73a259c9eb9b8dd8d891e853177df2ce5a14ee4f3f5b9` |
| WeChat 8.0.74 | 261,152,116 bytes; 16 DEX; 204 native libraries | 233,555 classes; 2,916 manifest lines; 24,006 reference lines; 1.853 s | `e69e7fef8de8211695f08fc22e8f374333246c2483e637ae317f7a0f15d564cf` |
| Taobao 10.62.0 | 91,402,818 bytes; 12 DEX; 138 native libraries | 99,712 classes; 6,263 manifest lines; 12,144 reference lines; 1.490 s | `2d8844a2cefecb8b99f5e8dc83e3eabba39391b02e2dc27c562d8ba3d0755348` |

The measured peak across the sequential corpus run was 1,257,508,864 worker-tree RSS bytes;
the largest individual worker used 367,116,288 bytes and the MCP host peaked at 128,929,792 bytes.
Repeating Douyin with a 1 GiB tree budget produced the expected explicit aggregate-memory error;
the 2 GiB default completed. Durations are warm local observations, not performance guarantees.

The three large APKs then completed a 300-second, two-worker stability run with 1,400 uncached
metadata/class-list operations. The host ended 1,019,904 RSS bytes above its warmed baseline,
file descriptors stayed at 5, and no operation failed or child process remained.

## Initial hardening observations (Linux, Python 3.13)

The local full suite passed 32 tests with an APK supplied. Both stdio and Streamable HTTP exercised
all six tools against that APK (165 classes). HTTP also checked a rejected input.

| Check | Observation | Scope |
| --- | --- | --- |
| Parent exits while child retains pipes | Timeout returned in 2.010 s; child no longer executing | Real POSIX child, not mocked killpg |
| stdout budget | Rejected in 0.032 s; no result files; sampled host RSS delta 86,016 bytes | Finite 2 MiB producer, 32 KiB capture cap |
| stderr budget | Rejected in 0.032 s; no result files; sampled host RSS delta 45,056 bytes | Finite 2 MiB producer, 64 KiB capture cap |
| Unstable reference ordering | Six rows; paged concatenation identical; no duplicate/missing rows | Controlled subprocess reverses DEX-like lines between executions |
| Snapshot reuse/expiry | One process for initial pages; second process after forced expiry | Expiry timestamp advanced in the test, not a real 60-second wait |
| Metadata worker/queue | Separate PID observed; exhausted slots return queue timeout | Controlled worker plus real APK metadata transport checks |
| Class descriptor | `Login` becomes `LLogin;` | Direct regression assertion |

The first commit (`4a78bb7`) was also executed with the same finite stdout/stderr producer. It
accepted both 2 MiB streams despite the 32 KiB configured output limit; the new runner rejected
them. Its class conversion produced `Login;`, while the new service produced `LLogin;`.
The original orphan-cleanup implementation was not run because its unbounded pipe wait could hang.

## What this does not prove

- Host RSS sampling is separate from the worker ceiling. Windows limits aggregate Job memory;
  POSIX `RLIMIT_AS` is inherited and applies per process, with a separate 50 ms aggregate tree-RSS
  watchdog. The watchdog can overshoot briefly between samples.
  Synthetic workloads are regression checks, not an arbitrary-malformed-APK stress benchmark.
- A killed Linux child may remain a zombie until its reaper runs; the test checks that it cannot
  execute, not that the PID instantly disappears.
- The order test uses controlled output; it does not demonstrate a real ASC scheduling race.
- APK-path pagination is not an immutable content-addressed input session. DEX sessions bind an
  immutable validated bundle, but lossless parsing of embedded newlines in ASC text is unsupported.
- HTTP is loopback-only in these tests; there is no authenticated remote-deployment acceptance.
- Local measurements do not imply remote CI success; inspect the commit's GitHub Actions checks.
