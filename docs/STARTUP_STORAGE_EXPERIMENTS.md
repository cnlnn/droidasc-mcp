# Startup And Storage Experiments

Development evidence, 2026-10-23. None of the experimental runtime changes below is
retained. The retained runtime is byte-identical to the workflow candidate at
`b02c18092c7d5283a215b2d96fa441f2fe30ded0`; only tests and documentation are added.
These receipts neither approve publication nor close the startup/storage objective.

The retained Linux Python 3.13 source suite passes 1,231 tests in 190.59 seconds,
zero failures, errors or skips: `source-full-retained-runtime.xml` under the evidence
root below. This includes the 18 added opcode regressions and real stdio/HTTP flows.
`diff -qr --exclude=__pycache__` confirms the complete runtime tree, including the C
source and loaded native extension, exactly matches the frozen before snapshot.
Windows and clean-package acceptance of this development branch remain pending.

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

## Next Structural Experiment

The pinned competitor's `analysis/artifact_handler.py` maps the original artifact in
`_get_worker_artifact_mm` and inflates selected entries in `_inflate_dex`; its repeated
reference workers do not retain our canonical expanded snapshot. Our private stored
snapshot avoids repeated decompression, but retains substantially more bytes. These are
different storage/lifetime choices, not evidence that either implementation wins overall.

The next prototype should preserve already-compressed source member payloads, avoiding
recompression, and test bounded overlapped query inflation. It must include normalization,
directory preparation, temporary decoded buffers, all source/member integrity checks,
concurrent readers, cancellation and Windows handle cleanup. Measure complete first use,
repeats and process RSS plus retained/peak file bytes before selecting a new default.
Uncompressed input fallback and public-CLI source handoff also require explicit coverage.
This structural prototype is not implemented or accepted by these component experiments.
