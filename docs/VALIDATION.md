# Local acceptance checks

Current completion scope: [GOAL_02X.md](GOAL_02X.md). Competitor workflow closure,
ergonomics, performance and independent accuracy remain the overall completion criteria.

## v0.2.x native-query gate, updated 2026-10-23

The maintainer superseded the replacement-v0.3.0 plan with accepted 0.2.x increments.
Old v0.3.0/v0.4.0/v0.4.1/v0.5.0 releases and tags were withdrawn on 2026-10-23 after
verifying their backup metadata, all 16 asset hashes and Git tag objects. v0.2.2 and
earlier releases/tags remain unchanged; GitHub now reports v0.2.2 as latest.
Runtime code has changed: preparation/storage and the checked native selector are being
restructured. The next candidate is v0.2.3, not frozen or published. Rebuild package metadata
and run the complete Linux/Windows and clean-sdist/native-wheel
gates on the final commit before publishing its exact CI artifacts. Release notes must identify
that commit, run and hashes. Older version labels below identify historical releases and their
original evidence, not approval of this candidate; receipts must not be retroactively relabeled.

The pre-freeze Linux source matrix passes 989 tests on each of Python 3.10-3.13, with zero
failures/errors/skips and unchanged runtime hashes. Its supported-upgrade environments use
Pydantic 2.14.1; all 23 schema-cache/fallback tests also pass on locked Pydantic 2.13.5. Ten
new distribution-identity regressions additionally reject source/data, version and native
accelerator drift. Final CI must run all 999 tests per OS/interpreter and both clean-package
suites on the exact candidate commit; these local results do not replace that release gate.

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
