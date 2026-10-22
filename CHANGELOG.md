# Changelog

## 0.2.6

- Recheck original, reopened and freshly reopened container handles after the final complete
  input hash. Reject content changes or path replacement occurring at the end of that hash,
  for both DEX preparation and archive/manifest/resource reads.
- Compare identities consistently through fstat, preserving Windows timestamp semantics.
  Both complete input hashes, DEX checksums, duplicate checks and immutable sessions remain.
- Add mutation, path-replacement, handle-timestamp and cleanup regressions. The initial-hash
  overlap experiment is not included: alternating large-APK diagnostics show no stable gain.
  This is an integrity fix, not a startup/storage improvement; full release gates still apply.

## 0.2.5

- Avoid constructing discarded ZIP member metadata during validated DEX preparation.
  Resource names, duplicates, special file modes, directory/member bounds and extraction
  versions remain checked. Common timestamp extra fields keep their structural validation;
  ZIP64, Unicode paths and unknown extensions retain the standard ZipInfo decoder.
- Add independent retained-metadata/extra-field regressions and large-APK before/after
  diagnostics. Directory-only CPU reductions do not establish universal startup, retained
  storage or total-memory improvements. Complete release acceptance is still required.

## 0.2.4

- Add native literal `find_string_refs` navigation from discovered string values to
  const-string/jumbo use sites, without client-side regex escaping or index construction.
  Preserve case selection, global pagination, bounded session caching, checked 32-bit
  jumbo IDs and independent Python fallback. Legacy `find_refs` keeps its existing semantics.
- Match validated ASCII pool entries natively with linear-time substring matching; retain
  strict modified UTF-8 decoding for Unicode and malformed entries and the Python fallback.
  This removes per-entry Python decoding from the common literal-string query path.
- Extend real stdio/HTTP investigation handoffs, full-site independent string oracles,
  malformed-input/jumbo-ID regressions and clean canonical-package acceptance for this path.
  Candidate publication remains gated on fresh cross-platform and clean-package acceptance.

## 0.2.3

The maintainer switched to accepted 0.2.x increments. The original 0.3.0, 0.4.0, 0.4.1
and 0.5.0 releases and remote tags were backed up, verified and withdrawn on 2026-10-23;
0.2.2 and earlier releases were retained. Git history and historical evidence are preserved.
This candidate keeps the native implementation and adds bounded-frontier/preparation work;
it is not a runtime rollback or a claim that all competitor gaps have been closed.

- Move core DEX references, discovery, structure and streaming indexes to checked native
  decoding. Core queries require neither JADX nor Java; ASC remains the public Smali engine.
  Java source decompilation requires explicit opt-in. DEX 041 uses a separately configured
  standalone dexlib2 3.0.9 normalizer, not JADX.
- Ship an optional stable-ABI C accelerator with independent Python fallback, strict modified
  UTF-8 handling, exact instruction/payload boundaries, bounded per-DEX identity caches and
  sparse caller decoding. Reject malformed scans instead of claiming complete coverage.
- Add immutable hash-bound DEX sessions with explicit close, idle TTL, count/disk limits,
  concurrent preparation reservations, active-query pinning and lifecycle cleanup.
- Add exact method/field references with original DEX offsets, cross-DEX provenance,
  read/write filters and dynamic/unresolved diagnostics. These are declared instruction
  operands, not resolved virtual dispatch, reflection or JNI targets.
- Add one-pass fuzzy reference unions with literal owner/name filters, optional member names,
  exact prototype/type filters, read/write selection and global pagination.
- Add literal declaration/string discovery, class search, typed outlines, hierarchy/cycle
  diagnostics, string use sites, decoded instruction search/disassembly and source-token links.
- Traverse bounded incoming/outgoing/both call-graph frontiers without a mandatory full
  index, filtering incoming operands before they cross into Python. Retain call-only SQLite
  indexes for dense-frontier fallback or explicit durable reuse, with
  bounded depth/nodes/sites/output, explicit truncation and unresolved dynamic diagnostics.
- Allow independent immutable-session queries to run concurrently. Keep completed-page
  caching bounded without resident analysis workers; add optional hash-bound durable xref
  caching with independent budgets, process locks, checksums and TTL/LRU eviction.
- Report actual snapshot/class-directory preparation progress while preserving integrity and
  duplicate-class validation. Keep startup and first-query costs separate in comparisons.
- Stream and prefetch at most two DEX entries into validated immutable snapshots, with bounded
  queues, short-lived mapped directories and disk-backed UTF-16-ordered ownership metadata.
  Compile source/version-bound MCP schemas and defer CLI infrastructure until requested;
  strict SDK validation and independent Python decoding remain active.
- Add signing-container/certificate inventories with malformed/unsupported diagnostics,
  separately from cryptographic signature validity.
- Inventory APK/JAR/ZIP/AAR/AAB/APKS/XAPK capabilities, direct DEX artifacts and first-level
  nested JAR JVM classes. Preserve container/member hashes and explicit inventory-only limits
  for JVM decompilation, split reconstruction and unsupported container operations.
- Compare bounded, sorted revision identities and return redacted fixed-pattern secret
  candidates with pool provenance; matched values require explicit opt-in.
- Add resumable archive byte pages, manifest/class resources, investigation/revision prompts,
  typed output schemas and a source-traceable competitor map covering 25 tools, two resource
  templates, three prompts and 87 parameters with an AST inventory regression guard.
- Add an opt-in pinned Rust ASC APK backend with supervised workers and explicit unverified
  coverage. Python ASC remains the default; unsupported Rust hierarchy requests are rejected.
- Preserve Windows SQLite readers during concurrent durable-cache restoration and make
  preparation progress Windows-safe. Validate cancellation and cleanup over stdio/HTTP.
- Handle recent zipfile ASCII-name encoding flags while verifying local filename bytes and
  all other flags. Keep cached SDK schema descriptions stable across Python docstring
  dedenting without changing live tool descriptions or strict validation.
- Preserve payload-overlap checks on older Python ZIP readers without the bound slot,
  and validate raw entry names before Windows path normalization.
- Add independent full method/field/fuzzy/call-index accuracy oracles, malformed-input,
  Unicode, payload, native/fallback and no-Java regressions, plus matched large-APK cold,
  warm, concurrent and bounded-graph comparisons. Workload-specific wins do not establish
  universal superiority. Verify actual inherited CPU masks despite the competitor's nested
  pools; retain failed graph operations without inventing speedup ratios. Startup-to-first-result
  and retained snapshot storage remain open deficits on measured workloads.
- Require full Linux/Windows Python 3.10-3.13, clean canonical-sdist/native-wheel, independent
  signing and stability acceptance before publishing the exact successful CI artifacts.
  Compare canonical source/data and metadata with each wheel, then verify the installed
  package bytes against that exact wheel. Pin LF source bytes across platform checkouts.

## 0.2.2

- Bind CLI option values explicitly and terminate option parsing before reference query values.
  Queries resembling output/help flags remain query data instead of changing CLI behavior;
  ASC's matching semantics, including string/type regular expressions, are unchanged.
  The upstream pre-parser reserves the exact `--gui` query; it now returns an explicit error.
- Normalize exact method/field reference class names consistently with source queries, including
  default-package names beginning with `L`; preserve fuzzy class patterns.
- Lock development/CI to the tested Droid ASC 0.1.2.post2 engine and its dependency graph.
- Add permanent argument-boundary regressions and a default-package `Login` fixture, including
  stdio/HTTP checks for outside-root sentinel preservation and method/field query equivalence.
  Use valid cross-platform output paths and verify explicit invalid-regex errors and recovery.
- Measure request cancellation after MCP initialization, excluding server startup from the
  cancellation latency assertion without changing the worker cleanup deadlines.

## 0.2.1

- Validate WeChat 8.0.74, Taobao 10.62.0, and Douyin 39.1.0 base APKs pulled read-only
  from an Android 16 device. The corpus includes a 348 MiB, 53-DEX APK with 551,538 classes.
- Add a 50 ms aggregate process-tree RSS watchdog on top of the inherited POSIX per-process
  address-space limit. Raise the default worker-tree budget to 2 GiB for current large APKs.
- Make `psutil` a direct runtime dependency for cross-platform worker-tree accounting.

## 0.2.0

- Propagate MCP request cancellation into queue waits, shared-snapshot waits, and active ASC
  workers. Cancellation tears down the supervised process tree and the same session remains usable.
- Add a configurable 1 GiB worker memory ceiling. Windows enforces it across the Job Object;
  POSIX workers apply an inherited `RLIMIT_AS` before importing Droid ASC.
- Add repeatable corpus and concurrent stability checks, plus native Linux/Windows stability CI.
- Validate all six operations against four open-source APKs pulled read-only from an Android 16
  device, covering large, five-DEX, Kotlin, Flutter/obfuscated, and native-library packages.

## 0.1.2

- Add native Windows and Linux Python 3.10-3.13 acceptance, using an original source-built APK
  for all six tools over both transports and after sdist/wheel installation.
- Replace Windows taskkill cleanup with a kill-on-close Job Object and a startup handshake;
  the CLI cannot start before assignment. Failed Job setup stops the waiting worker.
- Test orphan/grandchild cleanup, successful and failed operation cleanup, reader termination,
  startup failure paths, and repeated-operation resource release. Strict CI rejects skipped tests.
- Explicitly depend on the tested Windows-only pywin32 version; include the new worker modules
  in Python distributions. Reader-construction failure now also releases the worker and pipes.
- Build distributions once in CI and validate the same artifacts on Linux and Windows before
  publishing them to GitHub Releases. Add version-pinned installation commands for both platforms.

## 0.1.1

- Bound stdout/stderr capture during execution and propagate stream-reader failures. Recheck
  reader results at completion so late overflow cannot masquerade as a successful partial result.
- Clean up POSIX process groups after the leader exits, and bound queue and process waits.
- Run APK metadata inspection and hashing in a supervised worker.
- Cache decoded, sorted snapshots once. Account for Python string and tuple storage, coalesce
  identical concurrent queries, and let unrelated queries run up to the configured concurrency.
- Add response byte budgeting and `next_offset` (null at end). Fix `Login`-style class descriptors.
- Add real-process and loopback HTTP tests, optional local APK tests, and sdist/wheel acceptance.
- Ship complete test fixtures, Chinese documentation, validation notes, and the dependency lock.
- Declare Linux as the validated platform. Windows cleanup and immediate cancellation remain
  unverified/unsupported; snapshots are not immutable content-addressed evidence.

## 0.1.0

- Initial six-tool CLI adapter with stdio/Streamable HTTP transports and allowed APK roots.
