# Startup And Storage Experiments

Development evidence, 2026-10-23. None of the experimental storage/runtime changes below
is retained. The comparisons used the workflow candidate at
`b02c18092c7d5283a215b2d96fa441f2fe30ded0`, before the separate standalone-DEX entry
reader addition. That addition does not replace the stored preparation/query path.
These receipts neither approve publication nor close the startup/storage objective.

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
