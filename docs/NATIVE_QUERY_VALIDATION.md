# Native-query validation, v0.3.0

The native implementation formerly released as v0.5.0 is republished as v0.3.0 at the
maintainer's request. Runtime code is unchanged; distribution metadata and installation
links are rebuilt for 0.3.0. The former v0.3.0, v0.4.0, v0.4.1 and v0.5.0 releases/tags
are withdrawn. Historical receipt filenames and source hashes below remain unchanged
so the original measurements stay traceable; they do not describe new package bytes.

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
competitor partitions DEX decoding across its resident process pool (default four).

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
Index disk usage is reported separately: on this machine `/tmp` is tmpfs, so index
bytes also consume system memory outside descendant RSS. This is not zero-cost RAM.

## Accuracy and release gate

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
