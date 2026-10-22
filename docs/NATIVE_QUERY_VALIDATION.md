# Native-query validation, v0.2.x

The next v0.2.3 is an active, unreleased candidate. On 2026-10-23 the maintainer replaced
the consolidation plan with accepted 0.2.x increments. The old v0.3.0/v0.4.0/v0.4.1/v0.5.0
releases and tags were backed up, verified and withdrawn; v0.2.2 remains latest. Runtime changes
include checked fused class/instruction selection, bounded decompression and a disk-backed
class ownership directory. See GOAL_02X.md for the governing workflow and performance scope.

The tables below are **historical v0.5.0 measurements**, not validation of the changed
v0.2.3 candidate. Original receipt filenames and source hashes remain traceable. Fresh
same-condition performance, complete-result accuracy and cross-platform package receipts
must replace their release authority before publication.

## Scope and reproducibility

Runtime source: `e263db57c21d8419573a55f5372cb17704bf9807`.
Competitor: unmodified `aimardcr/asc-mcp` at
`848c711f1d80a1c2577283f1fa5f475ff734aa40`, also the upstream HEAD checked
on 2026-10-22. This is a workload-specific comparison, not universal superiority.

The unchanged Taobao 10.62.0 APK has SHA-256
`2d8844a2cefecb8b99f5e8dc83e3eabba39391b02e2dc27c562d8ba3d0755348`:
12 DEX files, 99,712 classes, 606,974 methods and 12,495,817 instructions.
Both implementations use the same Python interpreter and dependencies. Fresh real
stdio servers alternate order across three rounds, with the same request-concurrency
budget, 180-second call deadline and 4-GiB aggregate descendant RSS limit. OS caches
are not dropped. Reports contain per-file runtime hashes and unchanged-input checks.
Java is deliberately unavailable and JADX is unset on our measured core query path.

```sh
uv run --with ./artifacts/aimard-asc-mcp python scripts/benchmark_competitor_runtime.py INPUT.apk \
  --scenarios method field fuzzy concurrent --rounds 3 --workers 4 --output workers4.json
```

Repeat with `--workers 2` for the equal two-worker budget. Our single-query scanner
does not spawn an internal pool; this budget controls independent requests. The
competitor also creates an inner DEX-decoding process pool inside a resident request
worker. Historical reports without `cpu_budget_version` match configuration, not an
aggregate CPU ceiling. The current harness additionally applies the same inherited
logical-CPU affinity set before either product imports, and samples every owned
descendant's affinity after transport initialization. See the fresh CPU-budget section
below; do not treat old and new CPU allocation methods as a controlled speedup ratio.

## Cold queries

Median cold batch seconds, after opening a fresh session:

| Workload | Ours, 2 workers | Competitor, 2 | Ours, 4 workers | Competitor, 4 |
| --- | ---: | ---: | ---: | ---: |
| `String.equals` references | 0.991 | 1.955 | 0.958 | 1.159 |
| `Build.MODEL` field references | 0.820 | 1.688 | 0.807 | 1.015 |
| `java.lang` / name contains `equal` | 1.034 | 1.961 | 1.023 | 1.225 |
| Concurrent method + field | 1.096 | 2.116 | 0.998 | 1.367 |

The four-worker cold-query medians improve by approximately 16-27%. These are
individual declared instruction sites, not resolved virtual dispatch. Our result
totals and the competitor's grouped-caller totals are not interchangeable. In
particular, the independent field oracle finds 332 real sites; the competitor
reports 417 caller groups. Its heuristic byte-candidate counts are not an
independent accuracy oracle and are not substituted for decoded instruction sites.

Median per-trial aggregate peak descendant RSS at four workers, MiB:

| Workload | Ours | Competitor |
| --- | ---: | ---: |
| Method | 143.2 | 810.6 |
| Field | 143.0 | 707.4 |
| Fuzzy | 143.4 | 815.9 |
| Concurrent | 209.9 | 1464.2 |

RSS sums owned processes and can count shared pages more than once. It excludes
OS file cache, and is not a measurement of unique physical memory/PSS. No resident
full-APK object graph or query-worker pool is retained by our host. Completed-page
caching remains bounded (32 pages / 4 MiB, at most 256 KiB per page).

## Startup remains different

Our open operation validates checksums, snapshots DEX bytes and rejects duplicate
class definitions before reporting ready. The competitor registers the path and
defers analysis. At four workers, median open-call time is 1.196 versus 0.116 seconds;
open-call peak RSS is 131.2 versus 95.8 MiB. Including process startup, median ready
time is 1.965 versus 0.805 seconds. These costs must not be hidden or subtracted.

Median process-start-to-first-result seconds:

| Workload | Ours | Competitor |
| --- | ---: | ---: |
| Method | 2.912 | 1.963 |
| Field | 2.809 | 1.827 |
| Fuzzy | 2.979 | 2.051 |
| Concurrent | 2.967 | 2.225 |

Thus cold *queries* and query peak RSS improve, but initial startup and end-to-end
first use do not beat this competitor. Actual MCP progress reports snapshot and
class-directory completion; heavy indexes are lazy. There is no artificial ready
signal, speculative incomplete result or background work excluded from these totals.

## Large graphs

One additional frozen same-input/root/depth-three/both-direction trial uses two
workers and the same external deadline/RSS cap. Our cold call-only index plus bounded
graph completes in 58.369 seconds, with 349.9 MiB peak descendant RSS. The complete
SQLite call index occupies 491,614,208 bytes (within the default 512-MiB index limit).
The returned graph has 177 nodes / 178 call sites and is explicitly truncated by
the 128-KiB response limit; it is not an unlimited complete traversal.

The unmodified competitor errors after 54.505 seconds / 2723.3 MiB with
`'list' object has no attribute 'get_class_name'`. Its graph builder calls object
methods on the list returned by pinned Androguard's `get_cm_method`. This confirms
the source-level incompatibility on the real large-APK MCP path. It is not a valid
graph timing or a basis for an unlimited-graph speedup factor. Historical timeout
runs are retained separately and are not substituted for this current failure.

Our graph's emitted sites and the full persisted call-index multiset require
independent instruction-decoder acceptance, not just successful bounded traversal.

## Candidate frontier reconstruction

The current development branch no longer requires whole-APK calls-index construction for
an ordinary uncached graph. It validates instructions with bounded BFS frontier batches;
existing session indexes, explicit durable-cache build/restore and dense-frontier disk
fallback remain available. This is a candidate architecture change, not a frozen release.

Three real-stdio alternating rounds at each two/four-worker budget yield median cold graph
times of 5.6871/5.5505 seconds and process-start-to-first-result of 7.8104/7.9555 seconds.
Peak aggregate RSS is approximately 139 MiB. Results remain exactly 177 nodes/178 call sites,
explicitly output-byte truncated; no 491,614,208-byte whole-APK index is created. The graph
matches every full-index output field in all nine direction/depth combinations. The
competitor fails every trial with the same exception; report status remains failed, so
these results do not establish a successful graph timing ratio against it.
These historical version-1 aggregate ready/batch metrics also have the receipt-I/O timing
limitation described below; remeasure with version 2 before freezing any latency claim.

Receipts in artifacts/release-renumber-20261022: frontier-large-exact-parity.json and
frontier-large-graph-workers{2,4}.json. They precede the optional durable-cache routing guard;
the subsequent 336-case zero-skip regression preserves both paths. Fresh final frozen
source identities, complete instruction-site parity and all platform/package gates are still
required. Startup and resource-heavy ZIP inventory memory deficits are not closed here.
Index disk usage is reported separately: on this machine `/tmp` is tmpfs, so index
bytes also consume system memory outside descendant RSS. This is not zero-cost RAM.

## Candidate compact ZIP inventory

The preparation path now streams directory records and retains full ZipInfos only for
code/container members. Every name and local-header offset is still inventoried and checked;
ordinary resource browsing remains a full stdlib ZipFile operation. Member decompression,
local-header/name agreement and selected-entry CRC checks still use stdlib readers. Full
original-archive before/after hashing and DEX checksums are not skipped or moved behind ready.

On the resource-heavy Douyin APK, three alternating fresh-process directory-only diagnostics
inventory exactly 47,676 names with matching inventory and selected-metadata hashes. Retained
ZipInfos fall from 47,676 to 55; median process peak RSS falls from 62,382,080 to 30,945,280
bytes. Directory construction is approximately 0.256 versus 0.262 seconds, not a latency win.
Receipt: artifacts/release-renumber-20261022/compact-zip-douyin-directory.json. This isolates
the allocation root; it is not a substitute for complete fresh-MCP timing/RSS or Windows tests.

The 39 reader regressions pass on each Linux Python 3.10-3.13, including ZIP64 backport
capability differences and exact member metadata/bytes against independent stdlib parsing.
The 139-case preparation/container/directory/stdio/HTTP selection also passes without skips.
Receipts: compact-zip-py3.{10,11,12,13}.xml and compact-zip-transports-zero-skips.xml under
artifacts/release-renumber-20261022. Final source-frozen accuracy and release gates remain open.

An initial three-round real-MCP diagnostic, compact-zip-douyin-workers4.json, completes all
24 implementation/scenario trials with stable input/runtime hashes. Its open-phase RSS is
approximately 132 versus 134 MB, but the older harness includes full report serialization
inside some ready/batch measurements. Preserve the receipt as historical diagnostic evidence,
not clean first-result latency authority. Timing version 2 stops at decoded response arrival,
records full first-result latency directly and writes the report only after all measured
calls; a new receipt must be used for those comparisons. No result closes all startup gaps.

The corrected timing-version-2 report, compact-zip-douyin-timing-v2-workers4.json, passes
all 24 alternating real-stdio trials with unchanged runtime/input hashes. Median seconds:

| Scenario | Our cold batch | Competitor cold batch | Our full first result | Competitor full first result |
| --- | --- | --- | --- | --- |
| Method | 1.6940 | 5.1837 | 7.3610 | 6.5940 |
| Field | 1.2002 | 3.3067 | 6.1838 | 4.7044 |
| Fuzzy | 1.5526 | 4.9498 | 6.7110 | 6.3583 |
| Concurrent | 1.5956 | 5.9246 | 6.8529 | 7.3353 |

Median open-phase aggregate RSS is approximately 132.2 versus 133.7-133.8 MB. Query peaks
are approximately 132.2 MB for individual queries and 163.9 MB for the concurrent batch,
versus approximately 1,047-1,119 MB and 2,092 MB respectively. These are decimal MB, not MiB.
The specific memory deficit is reduced on this input, but the first three complete startup
paths still trail; query-only wins are not full startup wins. Additional inputs/two-worker
and graph-concurrency comparisons, independent full-result accuracy and Windows/packages
remain pending. This report validates repeated results, not full cross-implementation site
equivalence; reference counts still have individual-site versus caller-group semantics.

## Candidate ownership pipeline and retained storage

Preparation now scans each completed stored member before the enclosing ZIP is finalized,
then overlaps SQLite insertion with copying the next DEX. The writer waits before allocating
the next names list, keeping one DEX directory live. All read mappings/handles end before
the next append (including the Windows mapping path); a pending SQLite file is only renamed
after final original-input validation. No premature session-ready event is introduced.
The source-name check uses an equivalent compiled C0/backslash character class; exact path,
Unicode, duplicate, CRC and DEX checksum rules remain active.

The updated three-round/four-worker Douyin receipt, with timing version 2 and explicit
temporary-file accounting, passes all 24 trials with unchanged runtime/input:
bounded-directory-douyin-timing-v2-workers4.json. Median seconds:

| Scenario | Our cold batch | Competitor cold batch | Our full first result | Competitor full first result |
| --- | --- | --- | --- | --- |
| Method | 1.4770 | 4.5433 | 5.7023 | 5.8173 |
| Field | 1.1298 | 3.1513 | 5.6383 | 4.5365 |
| Fuzzy | 1.6297 | 4.8387 | 5.8082 | 6.1478 |
| Concurrent | 1.5092 | 5.9568 | 6.0512 | 7.1816 |

Do not turn small margins into universal wins. Field complete first-result still trails;
open-phase process-tree RSS is about 137.6-138.1 MB versus 133.8-134.0 MB. The pipeline
improves latency in this receipt but has not closed startup memory or every first-result gap.
Historical-before/current-after timings are not a randomized controlled optimization ratio.

Temporary storage is now sampled in a background thread every 0.2 seconds, separately from
RSS and without receipt I/O in timed response paths. Both implementations share the same
sampled temporary-logical-byte safety cap. Logical/allocated peaks are lower bounds; allocated
bytes use st_blocks when available (otherwise null), and symlinks are not followed. The nine
harness regressions include concurrent response boundaries and explicit over-cap failures.

This host's /tmp is tmpfs, verified with findmnt. Our Douyin temporary peak is approximately
500.36 MB logical/500.37 MB allocated, versus zero trial-directory files for the competitor.
The immutable snapshot and class database alone retain 457.06 MB and 43.27 MB. Warm process
RSS of about 79 MB versus about 160 MB for the competitor's field workload must not be
presented as a total-memory win while that RAM-backed snapshot remains. File/RSS phase peaks
also cannot simply be added into a claimed exact simultaneous peak. Storage overhead is a
remaining resource gap; filesystem placement must be disclosed and matched in comparisons.

scripts/verify_preparation_directory.py checks original APK bytes through the independent
pure Python class cursor (accelerator=False), every class/owner pair in UTF-16 order, source
provenance/counts, every snapshot DEX hash and the complete common envelope. Douyin's 551,538,
WeChat's 233,555 and Taobao's 99,712 classes all match, with unchanged input/runtime hashes.
Receipts: pipelined-directory-{douyin,wechat,taobao}-full-ownership.json. Its whole-oracle
dictionary is acceptance-only, never a product memory or runtime dependency. Fixture damage
tests demonstrate detection of missing/wrong ownership and corrupt snapshot bytes.

The next directory revision stores internal CESU-8 keys (SQLite user_version=1), retaining
UTF-16 byte-order semantics while avoiding two bytes per ASCII code unit. This is an internal
storage encoding, not a public interchange format; see [Unicode TR26](https://www.unicode.org/reports/tr26/tr26-4.html).
Supplementary characters use surrogate-pair units; lone surrogates, exact identities and prefix
ranges remain covered. Existing format-0 UTF-16BE directories reopen read-only; unknown versions
are rejected. The full Douyin oracle again matches all 551,538 original identities/owners and
every snapshot byte: compact-keys-douyin-full-ownership.json. Owners shrink from 43,270,144 to
27,541,504 bytes, while the 457,060,748-byte immutable snapshot remains unchanged.

Three alternating matched field rounds at four workers pass all six trials:
compact-keys-douyin-field-v2-workers4-with-competitor.json. Median cold calls are 1.0310/2.7145 s
(ours/competitor), but full first results are 4.7377/3.9161 s. Sampled logical/allocated temporary
peaks are 484,628,602/484,642,816 bytes versus zero competitor files. Open RSS remains roughly
137-139 versus 134 MB. This reduces actual stored data, not just RSS accounting, but neither
the remaining first-result gap nor the tmpfs retention gap is closed. The failed receipt without
'-with-competitor' lacked asc_mcp in its interpreter and is not a valid comparison. Later harness
versions explicitly preflight and hash-match installed competitor Python sources to the pinned
checkout before any trial, then repeat that check afterward.

Actual owner-thread cancellation/timeout cases observe pending SQLite writes, stop the supervised
worker, require private-storage cleanup, and successfully run a fresh analysis afterward.
The 281-case targeted selection (52 deselected) and Linux Python 3.10-3.13's 168 cases per
interpreter pass with zero skips. These source checks do not replace final Windows or newly built
sdist/native-wheel gates. The separate installed-source/full-response harness now has 20 cases.

The Taobao four-worker graph/concurrent follow-up records unchanged input/product/installed
competitor sources: compact-keys-taobao-graph-concurrent-v2-workers4.json. All six concurrent
trials pass; median cold batch/full first result are 0.5062/2.3574 seconds versus 1.7488/2.7251.
Our sampled temporary logical peak is 118.88 MB versus zero competitor trial files. Our three
graph trials return the same cold/warm structured result (177 nodes, 178 sites, explicit
output_bytes truncation); the first-result median is 6.4504 seconds. All three competitor
graphs fail with "'list' object has no attribute 'get_class_name'", so the combined report
correctly remains failed, not an accepted graph speedup. Source inspection locates a method
target from dex.get_cm_method being treated as an object in service.py's cached graph builder.
The earlier two-worker receipt reproduces the same competitor failure. Neither receipt proves
untruncated graph completeness; independent graph-site and frozen full-index checks remain gates.

Preparation now also releases the root archive's full resource-name inventory after all
capability/safety/duplicate/nested-collision/entry-budget checks, before DEX buffers grow.
Selected ZipInfos, ordinary resource-reader paths and original-input final hash checks remain.
The APK/AAR lifetime regression fails before this change and the repaired container/ZIP/
preparation selection passes 98 cases without skips. All three original-input ownership oracles
pass again with identical class/owner digests and snapshot bytes:
released-inventory-{douyin,wechat,taobao}-full-ownership.json.

The corresponding matched three-round field receipt passes all six trials with unchanged
input/product/actual competitor sources: released-inventory-douyin-field-v2-workers4.json.
Median cold calls are 1.4206/3.9502 seconds and full first results 7.2970/5.8193 seconds.
Open RSS is about 135.9-136.5/133.8-133.9 MB; stored bytes remain unchanged. Both implementations'
timings differ substantially from the earlier run, so no causal before/after optimization ratio
is claimed. The latest matched first-result gap is 1.4777 seconds, not the earlier 0.8216.
Post-run host load was 6.88/5.77/4.01 (1/5/15 minutes); this is not proof of the cause of timing
variation, and other user processes were not stopped or modified. Startup RSS, first-result
latency and retained tmpfs data remain open requirements rather than accepted performance wins.

The current development-source selection passes 288 tests without skips (52 integration
deselections), including real stdio/HTTP investigation, fuzzy and bounded graph paths:
released-inventory-targeted-zero-skips.xml. Linux Python 3.10-3.13 each pass 214 cases without
skips: released-inventory-py3.{10,11,12,13}.xml. All container, preparation, compact ownership
and 20 harness regressions are included. Schema and Ruff checks pass. No candidate freeze,
Windows result, fresh package gate or publication is implied.

## Checked directory and inherited CPU budget

The native class-directory reader now validates ASCII identities and duplicates in C,
returning owned rows and only the deferred Unicode indices. Python no longer rebuilds
every ASCII tuple/name or repeats its set insertion. Strict MUTF8 decoding still handles
all Unicode rows, including malformed unselected names, supplementary/lone surrogates and
canonical duplicate identities. The older accelerator API and independent Python fallback
remain supported. Stored-snapshot full CRC, DEX bounds and mapping cleanup are unchanged;
the stable-ABI build adds no Java or other backend dependency. The focused native/directory/
graph/structure/index selection passes 377 cases with zero skips:
checked-directory-native-zero-skips.xml.

Source inspection confirms an outer ProcessPoolExecutor in asc_mcp/runtime.py, propagation
of worker_count in server.py, and a second ProcessPoolExecutor in
analysis/artifact_handler.py:_for_each_findrefs. Identical worker settings alone therefore
do not constrain total CPU execution. New reports use timing_version=2 and
cpu_budget_version=1. A common Python/psutil wrapper sets and reads back the exact CPU mask
before importing either server; its time/RSS overhead is included for both. Unsupported
affinity fails rather than silently weakening the comparison. Samples must show nonempty
descendant masks contained in the budget; unreadable or escaping masks stop owned processes
and fail the trial. A process that exits during sampling is a benign race, not successful
affinity evidence. The 39-case harness/wrapper receipt includes these safety failures:
cpu-budget-monitor-zero-skips.xml.

Fresh Douyin field trials alternate three rounds at each budget. Input, product runtime
and actual installed competitor source hashes remain unchanged; all twelve trials pass
with complete structured cold/warm equality within each implementation:
checked-directory-douyin-affinity{2,4}-field.json. Median seconds (ours/competitor):

| Logical CPU set / workers | Transport startup | Open call | Ready from start | Cold field call | First result from start |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0,1 / 2 | 1.3537 / 1.4092 | 6.8338 / 1.0134 | 8.1339 / 2.4848 | 1.7970 / 10.7506 | 10.0072 / 13.1193 |
| 0,1,2,3 / 4 | 0.9034 / 0.9926 | 4.8764 / 0.8878 | 5.8043 / 1.9016 | 1.4025 / 4.8802 | 7.2794 / 6.7757 |

At two CPUs the full first result is 3.1121 seconds faster; at four it is still
0.5037 seconds slower. These are separate budget-specific workload observations, not a
universal ranking or proof that preparation costs disappeared. Sampled process counts
reach 2 versus 5 at two workers and 2 versus 7 at four; the same logical-CPU masks still
apply to every sampled process. Median per-trial peak aggregate RSS is
133,799,936/697,536,512 bytes at two CPUs and 135,299,072/1,061,253,120 at four. Open-call
RSS remains close, with no consistent four-CPU advantage. Our retained private files are
still 484,628,602 bytes on tmpfs, versus zero competitor trial files. This is not a
total-system-memory win. More APKs, graph/concurrent CPU-budget trials and the retained
snapshot/startup gaps remain open before any final freeze.

All three original-input ownership/snapshot oracles pass again after the checked C change:
checked-directory-{douyin,wechat,taobao}-full-ownership.json. Every class/owner matches the
independent Python cursor (551,538/233,555/99,712), every copied DEX hash is exact, and all
ordered-owner digests match the preceding receipts. The connected real-stdio/HTTP and
preparation/container/benchmark selection passes 320 cases, zero skips and 52 deliberately
deselected integration cases: checked-directory-targeted-zero-skips.xml. These are
development-source checks, not a final freeze or Windows/distribution approval.

The subsequent duplicate-stamp candidate avoids clearing a 16-KiB bitmap per class during
bulk selection. One generation table, bounded by the two 65,536-entry member pools
(524,292 bytes including one allocation padding entry), is local to each call and freed on every exit;
generation rollover clears it safely. Single-class selection retains its independent
bitmap path. Twenty additional tests cover both member kinds, within/across-group duplicates,
IDs 0/65,535, class-local generations and repeated calls. The native/directory/graph/structure/
index selection passes 397 cases without skips: duplicate-stamps-native-zero-skips.xml.
Diagnostic profiles report C-selection time 0.660/0.533 seconds before/after, but separate
profile runs are not a controlled end-to-end optimization ratio.

The new three-round four-CPU real-stdio receipt, duplicate-stamps-douyin-affinity4-field.json,
passes all six trials with unchanged input/runtime/installed competitor sources. Median cold
calls are 1.2955/5.1013 seconds, but opens are 5.1692/0.8466 and complete first results
7.7164/7.0332. The latest matched gap is therefore 0.6832 seconds, not the preceding 0.5037;
do not select an earlier best result or attribute preparation variation to the selector.
Retained storage and startup RSS are not closed by this small transient selector change.

Fresh full-result comparison with the frozen v0.4.0 JVM oracle passes all twelve alternating
comparisons (three rounds for each implementation and operation):
duplicate-stamps-full-reference-parity.json. All 24,461 method sites, 332 field sites,
12,495,817 decoded instructions and complete diagnostics match, with the exact full-result
digests below and unchanged input/oracle/runtime hashes. This is direct-backend accuracy
evidence, not MCP latency or a core Java dependency.

The three complete original-input owner/snapshot checks pass again on this runtime:
duplicate-stamps-{douyin,wechat,taobao}-full-ownership.json. Linux Python 3.10-3.13 each
pass 331 source cases, zero skips (duplicate-stamps-py3.{10,11,12,13}.xml); the selected
real stdio/HTTP/container/preparation flow passes 320, zero skips and 52 deliberate
integration deselections (duplicate-stamps-targeted-zero-skips.xml). These use the shared
rebuilt stable-ABI extension, not freshly installed release wheels or native Windows.

## Multi-input CPU-budget follow-up

WeChat's three-round concurrent method/field and fuzzy trials pass all 24 trials across
two/four logical CPUs, with unchanged input/product/installed competitor sources and complete
structured cold/warm equality within each implementation:
duplicate-stamps-wechat-affinity{2,4}-concurrent-fuzzy.json. Median batch/first-result seconds:

| CPU budget | Scenario | Cold batch, ours/competitor | First result from start, ours/competitor | First repeat batch, ours/competitor |
| --- | --- | ---: | ---: | ---: |
| 2 | Concurrent method + field | 1.0498 / 7.6354 | 5.0411 / 9.0528 | 0.1183 / 7.4658 |
| 2 | Fuzzy method union | 0.9648 / 5.4007 | 4.8450 / 6.9615 | 0.0640 / 0.0800 |
| 4 | Concurrent method + field | 0.7926 / 4.5157 | 4.1341 / 6.0853 | 0.1030 / 4.1567 |
| 4 | Fuzzy method union | 0.9041 / 3.0063 | 4.3395 / 4.5608 | 0.0464 / 0.0743 |

Concurrent median per-trial peak process RSS is 174,927,872/1,037,717,504 bytes at two CPUs,
168,218,624/1,494,376,448 at four. Sampled process counts reach 3/8 and 3/12 respectively,
still within identical inherited CPU sets. Our sampled temporary logical peak is 184,450,022
bytes versus zero competitor files; keep these RAM-backed files separate from process RSS.
The first fuzzy result at four CPUs leads by only 0.2213 seconds in this receipt. More rounds
and frozen cross-platform evidence are required before treating a small margin as robust.

The competitor's first concurrent repeat really rescans in these receipts; it is not replaced
with its much faster second repeat. Its service.py:_cached_reference_rows is a process-local
lru_cache dispatched through runtime.py's unspecialized process pool. That architecture is
consistent with requests landing on a worker whose cache is cold, but worker PID routing was
not traced, so this is an evidence-backed explanation rather than a proved scheduling trace.
Our host's bounded exact-page cache is shared by a session's requests; no resident whole-APK
worker or unbounded reference-row cache was added to achieve these repeats. This workload
does not close the Douyin startup or retained-snapshot gaps above.

Taobao's matching two/four-CPU receipts retain the graph failures rather than
discarding them: duplicate-stamps-taobao-affinity{2,4}-graph-concurrent.json. Both
reports are failed overall: each has three passing product graphs, three failed
competitor graphs and six passing concurrent trials. All input/runtime/installed
competitor identity checks pass. The unmodified competitor consistently raises
`'list' object has no attribute 'get_class_name'`; failed operations have no completed
graph latency and must not produce a graph speedup ratio.

| CPU budget | Scenario | Cold batch, ours/competitor | First result from start, ours/competitor | First repeat batch, ours/competitor |
| --- | --- | ---: | ---: | ---: |
| 2 | Concurrent method + field | 0.7746 / 6.3998 | 3.5750 / 7.6370 | 0.1058 / 6.0771 |
| 4 | Concurrent method + field | 0.7438 / 3.5271 | 3.1922 / 4.7943 | 0.1084 / 3.4781 |
| 2 | Graph | 6.1132 / failed | 8.6345 / failed | 0.0657 / unavailable |
| 4 | Graph | 5.9243 / failed | 8.3521 / failed | 0.0716 / unavailable |

Every product graph returns 177 nodes and 178 individual call sites with explicit
`output_bytes` truncation. This does not prove an unlimited graph is complete. The
fresh full-index comparison, duplicate-stamps-frontier-full-index-parity.json,
passes all nine direction/depth combinations with complete ordered graph equality,
including nodes, individual sites, resolution, dynamic diagnostics and truncation.
Its separately built call index occupies 491,614,208 bytes and takes 82.78 seconds
in this diagnostic. That index is an accuracy oracle, not a cost silently excluded
from the frontier timing; normal frontier queries do not build it. This compares
two native traversal paths, not independent instruction decoding, so the separate
full-site/index oracle requirement remains.

Concurrent median peak process RSS is 165,724,160/956,547,072 bytes at two CPUs and
165,969,920/1,515,782,144 at four. Product graph peaks are 146,513,920/146,792,448
bytes respectively. Retained temporary logical peaks remain about 118.88 MB for
the product versus zero competitor files. They are reported separately from RSS.

## Accuracy and release gate

The next graph-only revision selects incoming operands in the existing checked scanner,
while outgoing frontier methods still expose all their call sites. It does not skip caller
descriptor validation after a cap is reached, change traversal order, or omit instruction
validation. The profiler's Python-call count falls from 26,584,704 to 17,880,759, but the two
separate cProfile runs take 15.057/17.220 seconds: fewer transitions alone are not a measured
end-to-end speedup. Type-table matching was not the dominant hotspot originally suspected.

The subsequent controlled product-revision receipt is
frontier-filter-matched-revision-affinity4.json. Three alternating rounds per revision share
the interpreter, original APK, four-logical-CPU mask and resource budgets. All six fresh
stdio trials match complete graph responses across revisions (apart from session IDs and
explicit cache state), including 177 nodes/178 call sites and output-byte truncation. The
baseline is a 56-file snapshot hash-identical to the preceding measured runtime; both source
trees and input remain unchanged. Cold medians are 8.7214/7.2001 seconds before/after and
first-result medians 11.8991/11.5809, with peaks 146,354,176/146,698,240 bytes. One cold pair
and two first-result pairs regress. These are noisy three-round observations, not proof of
a robust startup/memory win, and this is not a competitor comparison.

The corrected standalone graph script measures real artifact open, frontiers and complete
warm-response equality rather than asserting obsolete full-index fields. Its receipt
frontier-filter-real-mcp-graphs-polymorphic-fixed.json passes with Java deliberately unavailable; the
separate Androguard pass verifies all 260 unique emitted call sites against original APK
bytes, with canonical entry mapping and polymorphic prototypes included. Open/cold/fanout
calls are 1.9002/2.2954/2.0646 seconds in this single diagnostic; first cold result is 5.3988
seconds from client startup. The graphs remain explicitly truncated. Input/runtime/verifier
identities and owned-file cleanup are checked. The earlier undersized-reservation attempt
remains failed in frontier-filter-real-mcp-graphs.json. The compiled fixture also exposed
Androguard's unimplemented generic method-reference API for 45cc/4rcc instructions; the
acceptance oracle now reads its decoded BBBB/HHHH operands. Both compiled formats and their
exact prototypes pass independent emitted-site and full-index checks; these fixtures are
necessary because the large APK above contains no dynamic sites. Source regression evidence is
frontier-filter-native-transport-zero-skips.xml: 374 passing cases, zero skips, including
128/512/2048-MiB reservation configurations and invalidated independent rechecks. None of
these receipts is a final Windows/canonical-package gate.

Three alternating complete-result rounds against the frozen JVM oracle match all
24,461 method sites, 332 field sites and all instruction/resolution diagnostics.
Their full-result SHA-256 values are respectively
`23822a6825a349c7bd962b7453b1a9a8df1f25547236a170ff0d216064a236cc`
and `656d23f0dda192f2825ac7e23ca2dcf84e9d83ac1a01dbeb97f686526f4daeab`.
The JVM and decompiler jars are acceptance-side oracles only, never a core runtime
dependency. Unicode/MUTF8, malformed unmatched types and invalid owner IDs have
accelerated/independent-Python differential regressions.

The complete independent fuzzy union also matches all 28,110 instruction sites and
10 targets; its multiset SHA-256 is
`ad3d0a9aa58b3c790e4bb388c6ebba65cf4bbfde64c631a441cbe24f8f5e1fc1`.

Release additionally requires complete persisted-call-index oracle checks, real
emitted-graph-site checks, and a fully green Linux/Windows Python
3.10-3.13, clean sdist/wheel, signing and stability CI run for the final commit.
Publish only that run's exact distribution bytes and record its commit/run/asset
hashes in the release notes. A competitor error is not a failed product gate, nor
does a green small-fixture suite replace the large-input accuracy checks above.
Both distribution jobs install the same canonical Linux-built source archive;
Windows additionally installs its native wheel. They do not substitute a separate
Windows-repacked source archive for the bytes selected for release.

An intermediate Windows HTTP cancellation check failed after the worker exited.
Its observer created a sentinel inside a directory concurrently being removed;
a controlled interleaving reproduces `ENOTEMPTY` with the directory left behind.
The native-worker observer is now read-only. The three-second worker-exit and
directory-removal assertions are retained, with HTTP logs on failure. This is not
a timeout increase or an ignored cleanup assertion; the final cross-platform run
must still pass the real transport cancellation path.
