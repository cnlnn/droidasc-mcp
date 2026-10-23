# Startup And Storage Experiments

Development evidence, 2026-10-23, with a separate implementation follow-up on 2026-10-24.
The earlier experimental storage/runtime changes below were not retained. Those comparisons
used the workflow candidate at
`b02c18092c7d5283a215b2d96fa441f2fe30ded0`, before the separate standalone-DEX entry
reader addition. That addition does not replace the stored preparation/query path.
These receipts neither approve publication nor close the startup/storage objective.

## Adaptive Reference Pages, 2026-10-24

The development runtime now returns the largest complete prefix that fits the existing
256-KiB DEX-result ceiling for method/field references, outgoing calls and fuzzy member
references. `limit` stays the requested, server-capped maximum. Short nonterminal pages
declare `page_limited_by=response_bytes`, the available encoded byte budget and an exact
`next_offset`. The worker newline is reserved. Metadata, diagnostics, ordering, duplicate
sites and individual identities remain intact; an unpageable row/metadata still returns
`response_limit`. This improves continuation behavior without changing the result model.
Selected-set reads stop before buffering over-budget rows; exact-page hits also account
for their added cache diagnostic. Per-page byte hints are not stored as set-wide metadata.

Evidence root: artifacts/adaptive-reference-pages-20261024/. targeted-complete.xml passes
288 tests, zero skips, with 52 other integration cases deliberately deselected. Boundary
cases include Unicode/JSON escaping, large offsets, cancellation, exact cache hits and
unpageable metadata. A generated real DEX contains 2000 repeated call sites: both stdio
and HTTP collect every original offset twice, with fixed requested page size and no
error/retry. Input/output schema checks and the pinned public-surface audit also pass.
This is a focused gate, not full Linux/Windows or installation-package acceptance.

accepted/summary.json binds all 98581 original-byte selected sites over 148 pages,
36 matched trials and 72 independent collection replays. Every product collection
passes. The same six competitor Taobao-field collections fail with 97 extra sites each;
their timings remain excluded from correct-result comparisons. The other 30 competitor
collections pass. All 36 frozen before/after method collections separately match the
independently accepted complete current response, including order, duplicates, metadata
and diagnostics: paired-runtime/accuracy.json.

Three alternating fresh-server rounds compare frozen 4c01302 (same native extension)
with adaptive paging. First complete query starts after open; medians are seconds:

| Input | First complete query before / after | Repeat complete query before / after |
| --- | --- | --- |
| Taobao | 4.0851 / 4.3730 | 3.6027 / 3.6240 |
| WeChat | 5.6125 / 4.8628 | 4.0735 / 4.2121 |
| Douyin | 7.9634 / 7.7734 | 6.8891 / 6.2245 |

The result is mixed: fewer pages and no retry do not establish a universal speedup.
Taobao first/repeat and WeChat repeat medians regress in this paired batch. The change
is retained for explicit, gap-free byte-bounded continuations, not as proof that the
remaining repeated-query latency deficit is solved. Original accuracy collection pages
fall from the preceding runtime's 200 to 148 with the same requested maximum and sites.

The separate fresh competitor batch uses the same interpreter/dependencies, four logical
CPUs/workers, 4096-MiB descendant RSS and 8192-MiB temporary-file caps, three alternating
rounds and retained OS caches. These absolute times are not a causal comparison with the
preceding before/after batch. No focused tests overlap either timing batch.

| Input | First complete method query ours / competitor | Repeat complete method query ours / competitor | Startup to complete method collection ours / competitor |
| --- | --- | --- | --- |
| Taobao | 4.4862 / 4.8623 | 3.4631 / 3.2284 | 6.3029 / 5.7331 |
| WeChat | 5.9201 / 10.2491 | 4.2108 / 4.7872 | 9.3179 / 11.8777 |
| Douyin | 7.5010 / 11.7956 | 6.1283 / 5.1270 | 11.7796 / 13.0564 |

The 870 successful product method pages include 852 explicit byte-bounded prefixes
and zero response-limit retries. First successful method-page medians from process start
are 2.6218 / 2.9564, 4.3890 / 5.7570 and 5.9172 / 7.7031 seconds. WeChat field first/repeat
complete queries are 0.5262 / 2.1478 and 0.0439 / 0.0834, but startup still loses at
3.8916 / 3.8569. Douyin field first/repeat are 0.9479 / 4.0194 and 0.0678 / 0.1342;
startup is 5.2837 / 5.4033. Taobao field comparison remains invalid as noted above.

Product method descendant-RSS maxima are 117682176 / 121659392 / 134729728 bytes versus
845029376 / 968208384 / 1104261120 for the competitor. Temporary regular-file peaks are
125277477 / 189117508 / 491522624 product bytes; the competitor records zero within its
measured temporary root. These are sampled lower bounds. `/tmp` is tmpfs, and its file
cost is separate from RSS rather than evidence of lower whole-system RAM usage.
Taobao/Douyin method repeats, Taobao complete-result startup and WeChat field startup
still lose in this batch. Storage, broader workflows/graphs and fresh full cross-platform
package gates also remain open. No new publication is approved.

## Output Schema Validation, 2026-10-24

After selected-set reuse removed repeated scans, profiles still showed host page work
and per-row client validation. A 500-site page from the actual Taobao response takes
median 0.0484 seconds to validate against the original schema versus 0.0330 seconds
with primitive type unions, over ten direct validation iterations. This is one-page
diagnostic evidence, not an end-to-end or competitor result. Inlining the row reference
adds little in that probe and is not retained. Profiles are diagnostic only: Python
3.13 cross-thread cumulative times are not additive wall-time budgets.

Production uses Pydantic's primitive_type_array schema generation when available;
older Pydantic versions keep their original schema generator. The runtime output
TypedDict contracts, strict validation, fields, values, paging and byte limits are
unchanged. Only unconstrained primitive unions become type arrays; constrained unions
retain their branches. JSON Schema supports this equivalent union representation:
[type arrays](https://json-schema.org/understanding-json-schema/reference/type) and
[anyOf](https://json-schema.org/understanding-json-schema/reference/combining).
The source-bound input cache and output schemas are regenerated. Tests compare every
generated primitive union against the original, preserve all other schema structure,
reject invalid runtime values and exercise the older-generator fallback.

The targeted gate passes 203 tests with zero skips, with 52 other integration cases
deliberately deselected: schema-types-transport-final.xml under
artifacts/selected-reference-cache-20261024/. It includes real stdio/HTTP references,
fuzzy queries, call graphs and resource views. No full cross-platform/package gate
is claimed for this runtime.

An actual frozen a1d4137 source tree, including the identical native extension, alternates
with the new runtime over three fresh-server rounds per input. Both use the same Python,
four logical CPUs/workers, complete method collections and external resource caps.
Medians in seconds are below; first query starts after open. Receipt:
schema-paired-runtime/report.json under the same evidence root.

| Input | First complete query before / after | Repeat complete query before / after |
| --- | --- | --- |
| Taobao | 4.4838 / 3.9295 | 3.7685 / 3.4210 |
| WeChat | 4.9884 / 4.5201 | 4.1774 / 3.5540 |
| Douyin | 9.5429 / 8.4443 | 7.9218 / 6.5970 |

These are shared-host observations, not a dedicated-host benchmark. One Taobao pair
regresses; the targeted suite also overlaps part of that input's trials. The separate
fresh competitor batch starts after those tests. None of the medians implies that
every query, client, round or startup workload improves.

The earlier compact-text and duplicate-page-cache-bypass prototypes are not adopted.
Their Taobao-only three-round pilot has variable first/repeat results and does not
establish a robust overall gain. Their private report and failed profiling setup
attempts are preserved separately, rather than silently replacing production evidence.
Fresh current-runtime original-byte and competitor checks are recorded separately under
schema-types/; the preceding bounded-retry/ receipts below remain historical.

That fresh batch is complete. schema-types/summary.json binds 203 targeted tests,
all 98581 independently checked original sites/200 pages, 36 matched trials and 72
independent collection replays. All 36 product collections pass; the six competitor
Taobao field collections still have 97 extra sites each. The separate
schema-paired-runtime/accuracy.json also checks all 36 before/after collections against
the independently accepted current complete response, including ordered duplicates,
diagnostics and provenance rather than only counts.

The new competitor medians below use the same interpreter/dependencies, four logical
CPUs/workers, 4096-MiB descendant RSS and 8192-MiB temporary-file caps, three alternating
fresh-server rounds, two complete collections and retained OS caches. They are separate
from the preceding before/after trial batch: absolute values across the two batches
are not a controlled causal comparison.

| Input | First complete method query ours / competitor | Repeat complete method query ours / competitor | Startup to complete method collection ours / competitor |
| --- | --- | --- | --- |
| Taobao | 5.4374 / 7.1089 | 5.0951 / 4.3342 | 7.8807 / 8.2831 |
| WeChat | 5.8857 / 8.2558 | 5.2029 / 4.9130 | 9.1925 / 9.7442 |
| Douyin | 12.2119 / 18.0429 | 11.2637 / 8.3020 | 18.6406 / 20.5192 |

First successful method pages from process start are 3.6549 / 4.3366, 4.5723 / 5.3781
and 9.0797 / 12.9147 seconds, respectively. The field first-complete-query medians are
0.5845 / 1.9895 seconds for WeChat and 1.9237 / 6.9684 seconds for Douyin. WeChat field
startup still loses at 3.8342 / 3.4198 seconds; Douyin field startup is 8.4537 / 9.7439.
Taobao field timings are not an equal-correct-result comparison and are excluded.

All three complete method repeats remain slower than the competitor in this new
batch, despite the separate before/after improvement. This leaves a measured repeat
deficit as well as WeChat field startup; favorable first-query medians do not close them.
All 1182 successful product method pages reuse the complete selected set. Process-RSS
maxima over the three method trials are 117698560 / 121647104 / 137367552 product bytes
versus 839954432 / 962154496 / 1110908928 competitor bytes. Product temporary regular-file
peaks are 125277477 / 189118848 / 491522624 bytes, separate from RSS; /tmp is tmpfs on
this host. The competitor records no regular files in its measured temporary root.
Sampling is a lower bound and does not prove whole-system RAM superiority. Startup,
storage, broader workflows/graphs and fresh full Linux/Windows/package gates remain
open. No new release is approved.

## Selected Reference Cache Implementation, 2026-10-24

The development runtime now implements selected-set streaming and host pagination in
reference_spool.py/reference_cache.py; the sequential private prototype is not copied as
the session storage manager. Before a worker writes, the session store reserves up to
32 MiB from remaining global session capacity. Completed and pending sets share that
quota; a build leases at most 16 MiB. SQLite pages and receipt files fit within the lease.
Insufficient space or cache errors fall back to normal analysis, without truncating rows.

Equal selectors share a query stripe across page offsets. Different selectors can build
concurrently in private leased directories; only complete scans with matching row counts,
bounded metadata, input/backend identity and a verified whole-file digest are published.
Readers preserve order, duplicates, resolution/provenance and scanner diagnostics. They
bound page bytes, recheck file and input identities, and close SQLite handles explicitly.
Cancellation discards only its owned lease; failed deletion retains its disk reservation.
Session close waits for pinned users and removes all session-owned files.

The first regression reproduced a new-page full-worker scan before implementation.
The current targeted suite passes 196 tests, zero skips, with 56 deliberately deselected
other integration cases:
artifacts/selected-reference-cache-20261024/focused-transport-bounded-retry-final.xml.
It includes real stdio/HTTP exact method/field and fuzzy pagination, cached-versus-uncached
full responses for six selector forms, concurrent same-selector pages, cancelled waiters,
concurrent publication, quotas, corruption, invalidation, and cleanup/error paths.
This is not a fresh full Linux/Windows/package gate.

The first large-input batch passed complete Taobao/WeChat references but then failed a
Douyin MCP timeout. Those receipts are retained under artifacts/selected-reference-cache-20261024.
The live host load average was 117.47 on 16 logical CPUs when inspected after the failure;
this coincided with the failure and does not establish causation. No unrelated processes
were stopped. A SQLite setup-error connection-close regression was also fixed before the
separate final corpus/comparison run under that evidence root's final/ directory.
Current benchmark results must identify this implementation, not the historical prototype.

That first implemented-cache run completed all three independent full-page checks and
36 matched method/field trials (three alternating rounds, two complete collections).
All product collections pass independent replay. The competitor's Taobao fields still
contain the same 97 extra sites; the failed comparison-accuracy receipt is retained.
Review then found that an oversized request against a complete cached set unnecessarily
fell back to a worker just to return response_limit. The follow-up returns the same
bounded error directly after file/input checks. Optional cache diagnostics cannot reject
a page that would otherwise fit. It changes neither requested offsets nor the response
byte cap, and smaller retries still reuse the complete set. Current-runtime repeated
accuracy/comparison evidence is under bounded-retry/, separately from the first final/ run.

The bounded-retry run is complete. Its summary.json binds all input/runtime/oracle,
benchmark/accuracy and targeted-test receipts. Independent original-byte stdio checks
pass all 98581 selected sites and 200 successful pages, including full diagnostics and
cleanup. The matched corpus has 36 trials and 72 independently replayed collections;
all 36 product collections pass. The six competitor Taobao field collections fail with
exactly 97 extra sites each, so their field timings are not equal-correct-result evidence.

Same Python 3.13.11/dependencies, four logical CPUs/workers, 4096-MiB descendant RSS and
8192-MiB temporary-file caps, three alternating fresh-server rounds per input, two
complete collections per query. OS caches are retained. The table contains medians in
seconds for the exact String.equals method query, not all queries or a stable benchmark
on a dedicated idle host. First query starts after open; startup includes open/imports.

| Input | First complete query ours / competitor | Repeat complete query ours / competitor | Startup to complete collection ours / competitor |
| --- | --- | --- | --- |
| Taobao | 4.3847 / 4.9030 | 3.6695 / 3.1422 | 6.1017 / 5.7369 |
| WeChat | 5.7758 / 6.3954 | 5.6156 / 4.1881 | 8.9115 / 7.4784 |
| Douyin | 11.4069 / 17.5069 | 9.0887 / 7.0085 | 16.9105 / 19.7155 |

Every successful product method page uses selected_reference_set: 1182 pages across
these repetitions, rather than full-input rescans or exact-page LRU hits. Repeated
oversized requests return response_limit in median 0.0213 / 0.0237 / 0.0150 seconds
for Taobao/WeChat/Douyin. The response cap remains 256 KiB. The separate original-byte
verifier replays every resulting continuation, including those bounded-error retries.

Peak descendant RSS maxima over the three method trials are respectively
117850112 / 121630720 / 135688192 product bytes versus
848683008 / 997163008 / 1090572288 competitor bytes. Product temporary regular-file
peaks are 125277477 / 189117508 / 491522447 bytes; the competitor creates no regular
files inside its measured temporary root. These sampled file costs are separate from
RSS, and /tmp is memory-backed on this host. They do not establish whole-system RAM use.

First complete queries now favor the product on these observations, but all three
repeat collections remain slower; Taobao/WeChat startup-to-complete also remain slower.
The WeChat field startup median is 3.7489 versus 3.6576 seconds. The next performance
work must measure remaining preparation and per-page/transport costs instead of claiming
that eliminating repeated scans closes every gap. Broader graph/workflow comparison,
full cross-platform suites and canonical-package gates remain open. No new publication.

The pre-entry-reader Linux Python 3.13 source suite passes 1,231 tests in 190.59 seconds,
zero failures, errors or skips: `source-full-retained-runtime.xml` under the evidence
root below. This includes the 18 added opcode regressions and real stdio/HTTP flows.
At that gate, `diff -qr --exclude=__pycache__` confirmed the complete runtime tree,
including the C source and loaded native extension, matched the frozen before snapshot.
That historical local gate did not prove Windows or clean-package acceptance. The later
workflow/raw-entry candidate at e3f3819 passed all 25 cross-platform/package CI jobs in
39967501671; see VALIDATION.md for that separate, exact-commit receipt.

Evidence root: `artifacts/startup-next-20261023/`. Inputs are the private Taobao
10.62.0, WeChat 8.0.74 and Douyin 39.1.0 corpus. Receipts bind original input hashes,
runtime files and helper code. Raw commercial APKs are not distributed.

## Preparation Micro-Optimizations

Fresh subprocesses alternate before/after order over three rounds and three APKs,
with inherited affinity restricted to four logical CPUs. Complete ordered ownership,
prepared metadata and every expanded snapshot byte agree across each paired trial.
These are direct-worker diagnostics, not MCP or competitor latency measurements.

| Experiment | Taobao median seconds | WeChat median seconds | Douyin median seconds | Decision |
| --- | --- | --- | --- | --- |
| SQLite insert batch 128 -> 499 | 0.7546 -> 0.7706 | 1.4207 -> 1.4405 | 3.1561 -> 3.2630 | Reject: slower on all three; sampled RSS also increases |
| Native batch CESU-8 keys and exact JSON length counting | 1.0596 -> 1.0072 | 1.9759 -> 1.9707 | 4.2247 -> 4.2630 | Reject: no stable preparation or RSS benefit across inputs |

Receipts: `owner-batch-probe-cpu4.json` and `key-encoding-revision-probe-cpu4.json`.
The latter prototype preserved lone surrogates, supplementary pairs, control/quote
escaping and the Python fallback; semantic parity alone did not justify retaining it.

Low-overhead phase instrumentation reports about 0.95/0.87 seconds of owner-insertion
thread CPU before/after the encoder prototype on Douyin, but total preparation wall
time regresses from 3.86 to 4.00 seconds in that pair. Overlapping phase wall times
are not additive. Cross-thread cProfile cumulative times are not phase budgets.

## Stored Versus Deflate Pilot

`compression-pilot-douyin.json` is a single paired feasibility trial. A disposable
child substitutes Deflate level 1 and reads class identities through the checked
in-memory cursor. Standard ZIP CRC checks, metadata, all 551,538 owners and hashes
of all 53 expanded DEX members agree. The complete first field page and two repeated
pages also agree. This is not an independent full-reference or real-MCP acceptance.

| Direct-worker measurement | Stored | Deflate level 1 |
| --- | --- | --- |
| Preparation seconds | 3.6756 | 11.5415 |
| First field query seconds | 1.1162 | 3.5256 |
| Retained regular-file bytes | 477,077,924 | 205,494,135 |
| Sampled preparation process RSS bytes | 65,916,928 | 88,072,192 |

Reject ordinary recompression as the default: storage falls, but preparation and
subsequent queries slow substantially. These direct-library defaults differ from
real-MCP settings. In particular, the 477.08-MB diagnostic must not replace the
484.63-MB retained-file observation in the real-MCP receipts. `/tmp` is tmpfs on this
host; file bytes are a separate memory-backed storage cost, not process RSS savings.

## Fast Codec Component Probe

`fast-codec-three-apks.json` tests LZ4 4.4.5, with independent 64-KiB blocks, declared
content sizes, block/content checksums and bounded incremental expansion. Every
expanded member SHA-256 matches its original ZIP bytes in all nine fresh-process
trials. The exact native codec and wrapper hashes are recorded.

| Input | Raw DEX bytes | LZ4 frame bytes | Median compress seconds | Median expand seconds |
| --- | --- | --- | --- | --- |
| Taobao | 112,915,728 | 65,581,903 | 0.3400 | 0.1646 |
| WeChat | 173,181,908 | 104,245,742 | 0.5068 | 0.2399 |
| Douyin | 457,055,340 | 249,596,901 | 1.2573 | 0.6266 |

This measures codec/file components only. Original APK expansion, hashing, owner
validation, query scans and MCP costs are explicitly outside these timings. It proves
neither end-to-end speed nor lower peak RSS. No codec dependency, production storage
format or automatic compression setting is added from this evidence.

## Native Cursor Prototypes

Both prototypes use the existing checked decoder and preserve pool/version/payload
bounds, complete instruction counters, dynamic-site diagnostics and error propagation.
The first preclassifies ordinary opcodes; the second separately accumulates counters
locally. Each has 18 fresh real-stdio before/after trials, three rounds per APK, equal
four-CPU budgets, 2048-MiB process-tree RSS caps and 8192-MiB temporary-storage caps.
Complete open and cold/warm response contents agree apart from session IDs and explicit
cache state. These are revision comparisons, not fresh competitor comparisons or full-site
independent accuracy. OS caches remain populated; individual pairs sometimes regress.

| Prototype | Taobao cold median seconds | WeChat cold median seconds | Douyin cold median seconds |
| --- | --- | --- | --- |
| Opcode preclassification | 0.3182 -> 0.3202 | 0.4526 -> 0.4336 | 1.0687 -> 1.0437 |
| Local counters, without preclassification | 0.3187 -> 0.3307 | 0.4329 -> 0.4374 | 1.0791 -> 1.1083 |

Receipts: `opcode-matched-three-apks-cpu4.json` and
`counter-matched-three-apks-cpu4.json`. Neither establishes a robust cross-input gain;
both C changes are removed. The new opcode regressions remain: all 256 opcode values,
five DEX versions and three selection kinds, truncated instructions, exact long-method
counters and corrupt tails after otherwise matching code.

## Original Payload Reuse And Overlapped Inflation

The pinned competitor's `analysis/artifact_handler.py` maps the original artifact in
`_get_worker_artifact_mm` and inflates selected entries in `_inflate_dex`; its repeated
reference workers do not retain our canonical expanded snapshot. Our private stored
snapshot avoids repeated decompression, but retains substantially more bytes. These are
different storage/lifetime choices, not evidence that either implementation wins overall.

The isolated prototype now copies source STORED/DEFLATED payload bytes into canonical ZIP
members without recompression. Existing expanded DEX SHA-256/SHA-1/Adler, ZIP CRC, strict
class checks and final original-archive hash checks remain active. A temporary stored ZIP
holds one member for directory validation, then is unlinked before proceeding. The copied
compressed range is SHA-256 checked against a readback before its directory entry is added.
Failure rolls back unpublished output. The source ZIP lock also serializes direct payload
reads with the existing prefetch readers.

The copier passes 25 local Python 3.13 cases: STORED/DEFLATED, data descriptors, ZIP64,
prefixed archives, Unicode original names, canonical target names, simultaneous stdlib
reads, local/central mismatches, overlap, short writes, corrupt/truncated readback, rollback
and mixed standard/raw writes. Receipt: `raw-payload-tests.xml`. This is not Windows or a
complete container/normalization acceptance gate.

`compact-matched-three-apks-cpu4.json` passes all 27 fresh direct-worker trials, rotating
three variants over three rounds per APK with a common four-CPU affinity. The baseline
uses the unchanged stored snapshot; `compact` preserves original compressed payloads;
`compact2` adds two-slot, ordered query inflation. All complete ownership rows, metadata,
expanded DEX hashes and first field pages (including two direct repeats) agree across
variants. All temporary roots and helper threads are gone before each child returns.
The receipt binds inputs, runtime and helper hashes. These are not MCP/competitor timings,
OS-cache-cold measurements or independent all-reference accuracy results.

| Input | Variant | Median prepare seconds | Median first field seconds | Median prepare + field seconds | Retained file bytes | Median first-field process RSS bytes |
| --- | --- | --- | --- | --- | --- | --- |
| Taobao | Stored | 0.8051 | 0.1714 | 0.9741 | 117,596,620 | 45,875,200 |
| Taobao | Compact | 0.9559 | 0.6570 | 1.6263 | 48,067,868 | 59,109,376 |
| Taobao | Compact, two-slot inflation | 0.9561 | 0.4463 | 1.4023 | 48,067,868 | 83,968,000 |
| WeChat | Stored | 1.5069 | 0.2720 | 1.7853 | 181,485,807 | 51,236,864 |
| WeChat | Compact | 1.7618 | 1.0510 | 2.8129 | 77,179,740 | 68,116,480 |
| WeChat | Compact, two-slot inflation | 1.8635 | 0.6312 | 2.5027 | 77,179,740 | 96,325,632 |
| Douyin | Stored | 3.4264 | 0.8735 | 4.2999 | 477,077,924 | 50,561,024 |
| Douyin | Compact | 3.9500 | 2.7224 | 6.6724 | 189,261,777 | 63,143,936 |
| Douyin | Compact, two-slot inflation | 4.0302 | 1.8368 | 5.8213 | 189,261,777 | 84,328,448 |

The sum column is the median of paired prepare-plus-query observations, not the sum of
independently selected medians. Peak compact preparation file bytes reach 57,602,967 /
88,867,464 / 197,508,485 respectively; temporary validation storage is included rather
than hidden. These direct defaults still differ from real-MCP budgets. File bytes on
this host's tmpfs remain a separate cost from process RSS.

Reject this as a default replacement: retained files fall about 57-60%, but preparation,
first use and both repeated scans are slower on all three inputs; query RSS increases.
Two-slot inflation reduces the sequential decompression penalty but does not eliminate it.
The two-slot count is not a general worker-memory bound for very large individual members;
production adoption would additionally need byte-budgeted streaming/mapping, reservation
accounting, error/cancellation tests and Windows/source-handoff/041 coverage. None is
claimed from this pilot, and no runtime change or dependency is retained.

Remaining work must improve the actual preparation/query/storage tradeoff, not move
decompression costs outside the reported first use or rename storage savings as RSS gains.

## Bounded In-Memory Compact Pilot

`compact-memory-wechat-pilot.json` is a single four-CPU direct-worker feasibility trial
on the e3f3819 runtime. Instead of an intermediate validation file, a child-only helper
validates one original DEX in a 32-MiB bounded buffer, with stored-file fallback for larger
members. Optional two-slot query inflation reserves at most 64 MiB of expanded bytes.
All 233,555 class/owner rows, metadata, expanded snapshot hashes and first/repeated field
pages agree; input/runtime/helper identity and complete temporary/thread cleanup pass.

| Variant | Prepare seconds | First field seconds | Retained file bytes | First-field process RSS bytes |
| --- | --- | --- | --- | --- |
| Stored | 1.4732 | 0.2761 | 181,485,807 | 51,212,288 |
| Compact, bounded memory validation | 1.8576 | 1.0658 | 77,179,740 | 67,973,120 |
| Compact, bounded validation and two-slot inflation | 1.8456 | 0.6518 | 77,179,740 | 107,913,216 |

The largest validation buffer is 13,688,452 bytes and scheduled query expansion peaks at
25,651,164 bytes. This pilot rejects removing the intermediate validation file as a
sufficient solution: it does not establish faster first use. It is neither an independent
all-reference oracle nor Windows/041/source-handoff acceptance. The prototype also waits
for the previous ownership insertion before copying the next member, unlike the product;
restoring that overlap is a separate, untested hypothesis. No production format is adopted.

## Prefetch Block-Size Sweep

`prefetch-chunks-three-apks-cpu4.json` passes 27 fresh direct-worker trials: 64/128/256-KiB
blocks, three rotating rounds on each original APK, identical four-CPU affinity, unchanged
one-block queues and at most two active member streams. All complete ownership rows,
metadata, expanded DEX bytes and first/repeated field pages agree, with cleanup and stable
input/runtime/helper hashes. The runtime is the e3f3819 candidate; only the diagnostic child
substitutes the block size. Preparation medians for 64 -> 256 KiB are 0.7774 -> 0.7734,
1.7407 -> 1.4654 and 3.7637 -> 3.1406 seconds for Taobao/WeChat/Douyin. Sampled preparation
RSS increases by about 1.9/2.3/2.5 MB; retained files are unchanged. These internal timings
do not establish a product startup improvement.

The subsequent `prefetch-matched-three-apks-cpu4.json` exercises the actual source revisions
over stdio, with only containers.py changed. All 18 alternating trials pass complete
open/cold/warm response equality except session IDs and explicit cache state. Both revisions
use Python 3.13.11, four inherited CPUs, 2048-MiB process-tree RSS and 8192-MiB temporary
file budgets; all measured input/runtime/helper hashes stay unchanged.

| Input | First result seconds, 64 / 256 KiB | Open seconds, 64 / 256 KiB | Peak process-tree RSS bytes, 64 / 256 KiB |
| --- | --- | --- | --- |
| Taobao | 2.0556 / 1.9738 | 0.9741 / 0.9402 | 112,947,200 / 112,021,504 |
| WeChat | 2.7585 / 2.9559 | 1.6455 / 1.7811 | 117,436,416 / 116,682,752 |
| Douyin | 5.4270 / 5.6979 | 3.6008 / 3.4185 | 133,615,616 / 136,253,440 |

These are medians, not independent full-reference or competitor comparisons. WeChat and
Douyin each regress at first result in two of three pairs. Reject the block-size change:
the product retains 64-KiB member prefetch, rather than adopting the direct-worker result.
A small first-result gain on one input does not overcome regressions on the other two.

The added two-case regression abandons both prefetched members with full queues, before
or after taking one block. It checks one queued/one producer block per inactive stream,
bounded reads, closed original streams and joined threads. Together with all container and
preparation-directory tests it passes 68 cases, zero skips:
`prefetch-retained-targeted-zero-skips.xml`. The initial invocation lacked optional fixture
configuration (52 passed/14 skipped); it is not acceptance. Two initial test-development
receipts are retained separately, including an overstrict assertion on the independent
snapshot extractor's final short read. No runtime modification remains from this experiment;
the new test cases do not retroactively increase the e3f3819 CI test count.

## Fresh Candidate Comparison

The standalone-DEX candidate runtime at `f144c0849eb3bab878b79d8fe6472ef1c87b7d25`
has fresh real-stdio field receipts: `raw-entry-{taobao,wechat,douyin}-affinity4-field.json`.
All three pass three alternating rounds against the pinned competitor, on the same Python
3.13.11 interpreter, four inherited logical CPUs, 2-GiB process-tree RSS and 8192-MiB
session-disk budgets. These use timing version 2 and CPU-budget version 1. "Cold" means
the first query in a fresh session, not evicted OS page caches. Exact cold/warm pages agree
within each implementation; that alone does not prove independent full-reference accuracy.

| Input | First result seconds, ours / competitor | Cold field seconds, ours / competitor | Peak process-tree RSS bytes, ours / competitor | Peak temporary file bytes, ours / competitor |
| --- | --- | --- | --- | --- |
| Taobao | 2.0022 / 2.3947 | 0.2847 / 1.5135 | 112,959,488 / 727,613,440 | 117,598,385 / 0 |
| WeChat | 3.0194 / 2.4458 | 0.4002 / 1.3808 | 118,435,840 / 715,849,728 | 181,487,568 / 0 |
| Douyin | 5.7325 / 5.9380 | 1.0766 / 4.4453 | 134,287,360 / 1,053,171,712 | 477,079,695 / 0 |

All columns are medians of per-trial measurements. Temporary files are sampled in each
supervised temporary root; zero is an observation there, not a claim of zero system-wide
writes. File bytes on this host's tmpfs are additional to the reported process RSS. Query
speed and process RSS therefore do not establish lower total memory. WeChat's first result
is still 0.5736 seconds slower. Douyin's first-result advantage is small and one round loses;
no universal startup win or causal speedup over earlier revisions is claimed.

Separate current-runtime receipts `raw-entry-{taobao,wechat,douyin}-full-ownership.json`
independently verify all 884,805 original class/owner identities and every expanded snapshot
byte. `raw-entry-large-summary-parity.json` checks actual-MCP summaries against original
ZIP/manifest/hash evidence and the pinned competitor. Neither is an all-reference oracle.

The full selected-reference oracle initially failed because its native subprocess supplied
a string after the native snapshot reader adopted a Path contract. The driver now constructs
Path explicitly; two unit cases execute that actual child command with a contract-checking
query stub, including alternating order. The fresh real-APK rerun
`raw-entry-full-reference-pathfix.json` passes all 12 comparisons: complete ordered rows
and diagnostics for 24,461 method sites and 332 field sites across 12,495,817 instructions,
three rounds each. Input, runtime and both scanner source hashes remain unchanged. This is
direct-backend accuracy for the selected descriptors, not MCP latency or all possible queries.
The initial failed receipts are retained, not overwritten or counted as passing evidence.

## Current Concurrent Corpus

`current-concurrency-corpus.json` and its six `current-{taobao,wechat,douyin}-affinity{2,4}-concurrent.json`
receipts pass all 36 real-stdio trials, three alternating rounds per input/CPU budget.
Both implementations use the same Python 3.13.11 interpreter/dependencies, original APK,
two/four configured workers, inherited two/four logical CPUs, 4096-MiB aggregate
process-tree RSS and 8192-MiB temporary-file budgets. Product runtime, installed pinned
competitor sources, input and harness hashes stay unchanged; every trial checks descendant
affinity, measured temporary storage, successful close and complete cold/warm response
equality within the implementation. OS caches are retained. This is the current e3f3819
runtime, not a measured speedup caused by a new product revision.

The concurrent workload requests exact String.equals method sites and Build.MODEL field
sites together. "First batch" ends only when both decoded responses arrive; it is not
the earlier of the two responses. All values below are per-trial medians, ours / competitor.
Both APIs request limit=100, but ours returns individual sites and the competitor returns
caller groups containing evidence sites. Reply payloads therefore are not normalized to
an equal number of instruction sites; these are API-workload timings, not matched complete
collection costs. Independent complete-site accuracy is recorded separately in VALIDATION.md.

| Input | CPU budget | Cold batch seconds | Process start to complete first batch seconds | First / second repeat batch seconds, ours | First / second repeat batch seconds, competitor |
| --- | --- | --- | --- | --- | --- |
| Taobao | 2 | 0.5963 / 5.4608 | 2.5357 / 6.3921 | 0.0832 / 0.0725 | 5.1525 / 0.0977 |
| Taobao | 4 | 0.5366 / 3.4640 | 2.7376 / 4.7029 | 0.0947 / 0.0763 | 3.2429 / 0.1404 |
| WeChat | 2 | 0.8531 / 7.0102 | 4.8982 / 8.1849 | 0.0810 / 0.0728 | 6.4205 / 0.1300 |
| WeChat | 4 | 0.9594 / 5.1281 | 4.6865 / 6.8618 | 0.1403 / 0.1089 | 4.6597 / 0.1531 |
| Douyin | 2 | 1.8291 / 19.1680 | 6.6270 / 20.4622 | 0.0785 / 0.0807 | 19.7875 / 0.5056 |
| Douyin | 4 | 1.9058 / 12.4801 | 6.9793 / 14.3093 | 0.0940 / 0.1008 | 12.2616 / 0.7104 |

| Input | CPU budget | Peak process-tree RSS bytes, ours / competitor | Peak temporary logical file bytes, ours / competitor |
| --- | --- | --- | --- |
| Taobao | 2 | 147,562,496 / 958,418,944 | 117,599,473 / 0 |
| Taobao | 4 | 147,419,136 / 1,483,137,024 | 117,599,473 / 0 |
| WeChat | 2 | 153,862,144 / 1,057,697,792 | 181,488,656 / 0 |
| WeChat | 4 | 153,411,584 / 1,446,535,168 | 181,488,656 / 0 |
| Douyin | 2 | 149,753,856 / 1,341,374,464 | 477,080,783 / 0 |
| Douyin | 4 | 148,525,056 / 2,080,415,744 | 477,080,783 / 0 |

These selected concurrent workloads favor the product in all reported latency medians and
process RSS. They do not close the separate WeChat single-field first-result deficit, graph
comparison, full-site independent accuracy or storage requirement. Temporary files are
sampled inside the supervised trial root; zero is not a system-wide write claim, and files
on this host's tmpfs are additional to process RSS. The competitor's first repeat remains
substantially slower than its second repeat; without traced worker routing this is an
observation, not proof of a specific cache/process-pool cause. No failed round is omitted.

## Complete Reference Collection Baseline

The 2026-10-23/24 full-page pilot extends scripts/benchmark_competitor_runtime.py with
full_method/full_field and adds scripts/verify_reference_page_benchmark.py. Each API follows
its actual continuation until the complete result is collected; response_limit recovery
retries the same offset with a smaller page and its cost remains in the measurement.
The measured endpoint is the last decoded response, not the first page. Offline acceptance
normalizes original DEX names, exact caller/target, byte offset, opcode and access, retaining
duplicate sites. Our complete ordered rows and every scanner diagnostic are additionally
compared with the frozen independent JVM scanner over independently inventoried original bytes.
Oracle work is outside both servers' measured costs.

These are one fresh paired round per APK, two complete collections per selected query,
not multi-round acceptance. Both servers share Python 3.13.11/dependencies, four configured
workers, the same inherited four logical CPUs, 4096-MiB aggregate process RSS, 8192-MiB
temporary-file caps and 180-second per-call limits. Requested page size is 1000. Our method
response exceeds the unchanged 256-KiB cap and retries at 500 sites; competitor pages contain
caller groups, but the complete selected method-site corpus is independently equal. OS caches
are retained. Product sources remain byte-identical to e3f3819; installed competitor sources
match pinned 848c711f, freshly rechecked against GitHub main.

| Input | Complete method sites | Product successful pages | First complete collection seconds, ours / competitor | Second complete collection seconds, ours / competitor | Process start to complete first collection seconds, ours / competitor |
| --- | --- | --- | --- | --- | --- |
| Taobao | 24461 | 49 | 27.1845 / 5.3954 | 25.8598 / 4.1029 | 29.6298 / 6.3633 |
| WeChat | 26184 | 53 | 36.6546 / 6.6087 | 36.3356 / 3.9139 | 39.5336 / 7.9801 |
| Douyin | 47005 | 95 | 158.3533 / 14.4882 | 177.8112 / 6.8126 | 163.8523 / 16.5657 |

All six product method collections have zero exact-page-cache hits, including second reads.
The PageCache key includes offset/limit, and its 32-entry/four-MiB LRU cannot retain a complete
49/53/95-page collection. Reading again from the beginning evicts later pages before reaching
them. The native _references path scans for every uncached offset; it does not stop after
selecting a page because complete counters/diagnostics must still be checked. This establishes
a real remaining architectural deficit, despite favorable earlier first-page measurements.
query_cache.py is a separate disk-page helper with no production caller; its presence does
not prove query-wide result reuse.

| Input | Method-trial peak process RSS bytes, ours / competitor | Method-trial peak temporary-file bytes, ours / competitor |
| --- | --- | --- |
| Taobao | 124440576 / 818905088 | 117598393 / 0 |
| WeChat | 128290816 / 945487872 | 181487576 / 0 |
| Douyin | 134668288 / 1099501568 | 477079703 / 0 |

Receipts: full-pages-{taobao,wechat,douyin}-baseline-pilot.json and their -accuracy.json
files under the evidence root. The remaining-input orchestrator distinguishes process
completion from accuracy success. Taobao's overall accuracy receipt intentionally fails:
product method/field pages and competitor method pages pass, but the competitor's field
evidence has 429 sites versus the independently verified 332, with zero missing and 97 extra.
WeChat and Douyin pass complete method and field content for both implementations. Do not
report the Taobao field workload as an equal-correct-result speed comparison.

full-pages-taobao-field-mismatch-examples.json independently decodes five discrepant original
sites with Androguard. All five claimed offsets lie beyond the named caller's instruction
stream, not at valid field instructions: for example, offset 22 in a 12-byte constructor.
The pinned InsnLocator keeps method starts but no exact ends; bucket conflicts collect
multiple method IDs, validate the first member and later expand evidence to every member.
This is source-backed evidence of unsafe caller association, not justification to copy its
byte-filter shortcuts. The five-example diagnosis does not claim to classify all 97 extras.

The benchmark/normalizer/oracle replay selection passes 95 local tests with zero skips:
full-page-benchmark-targeted-final.xml. Cases reject equal-count target/caller/offset/opcode/
access/source corruption, duplicate loss, changed diagnostics/provenance, empty continuations,
wrong cursors and unaccounted responses. A real trial-loop stub also requires timing through
the final page and inclusion of retry costs. This is test-harness acceptance, not a new full
source, Windows or distribution gate. No product runtime change is retained from this baseline.

## Selected-Result Spool Feasibility

Two isolated source copies test a targeted alternative without retaining a full-APK object.
reference-spool-prototype/droidasc_mcp streams every matching row into a private SQLite
file while the existing checked instruction scan runs. It retains only the requested page
in Python, then atomically publishes complete scan diagnostics and final target definitions.
The query key excludes pagination. A file is capped at 32 MiB, the sequential pilot's retained
spools at 64 MiB, and SQLite's page cache at two MiB. Readback uses rowid ranges and restores
the exact target-resolution fields; the original 256-KiB response cap remains unchanged.

The worker-read Taobao pilot collects all method sites in 9.7513 / 9.1797 seconds on first /
second reads, versus 6.9999 / 4.5568 for its matched competitor. It removes repeated scans
but still starts a worker for each new page. Its independent oracle receipt passes every
product row/diagnostic and competitor method row; the same competitor field mismatch is
retained as failed evidence. This is not a sufficient implementation by itself.

reference-spool-host-prototype adds a host-side page read for a published selected result,
avoiding that fresh-worker cost. Each input again has one fresh paired round and two complete
collections, with the baseline's interpreter/CPU/RSS/temp/page budgets. All preparation,
first scan, spool construction, oversized-response retry and readback costs are included.

| Input | First complete method collection seconds, prototype / competitor | Second complete method collection seconds, prototype / competitor | Process start to complete first collection seconds, prototype / competitor | Peak process RSS bytes, prototype / competitor | Peak temporary-file bytes, prototype / competitor |
| --- | --- | --- | --- | --- | --- |
| Taobao | 4.9700 / 5.9328 | 4.4509 / 3.9490 | 7.0098 / 6.9469 | 117575680 / 826818560 | 125273205 / 0 |
| WeChat | 5.2038 / 7.5940 | 4.4645 / 4.8209 | 7.9419 / 8.7487 | 121196544 / 930377728 | 189114325 / 0 |
| Douyin | 10.4062 / 13.1900 | 8.2802 / 6.5125 | 15.6735 / 14.9850 | 133959680 / 1107787776 | 491501716 / 0 |

Receipts: full-pages-{taobao,wechat,douyin}-host-spool-pilot.json and -accuracy.json.
All product ordered rows and diagnostics and every competitor method site match the frozen
independent original-byte oracle. WeChat/Douyin competitor field results also agree; Taobao
still fails with the same 97 extra sites. File costs include the extra spool, separately from
RSS; tmpfs bytes are not free memory. These are sequential pilots, not alternating before/after
revision trials, multi-round speedup proof or universal superiority. Although each first
collection query beats its paired competitor, Taobao/Douyin still lose from process start
and on the second full collection. Neither source copy modifies the production runtime.

This evidence selects a direction, not a releasable cache. Production work must bind each
publication to input/runtime/settings identity, handle cache replacement/corruption and
index lifecycle changes, coordinate concurrent writers/eviction, reserve combined pending/
retained/index bytes under the session budget, and enforce bounded metadata/readback with
cancellation. Selector resolution, fuzzy unions, 041 mappings, engine changes, source handoff,
cleanup and Windows behavior need focused coverage before final matched multi-round gates.
The prototype's sequential eviction, simplified identity and separate file caps do not prove
those invariants; it must not be copied directly into the shipped worker or host.

The separate host-spool-reference-pages-corpus.json accuracy/cleanup exercise passes all
three inputs, all 98581 selected ordered rows, 200 successful pages and every diagnostic.
Each session closes without cleanup_pending, owned temporary files disappear, and inputs,
prototype runtime and oracle files remain unchanged. This validates those sequential paths,
not untested concurrent cancellation or corrupted-cache behavior. full-page-experiment-summary.json
binds the baseline/prototype/accuracy/cleanup/test receipts and explicitly records
eligible_for_publication=false; the Taobao competitor field failure is not relabelled green.
