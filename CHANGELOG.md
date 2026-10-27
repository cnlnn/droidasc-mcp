# Changelog

## 0.2.4

- Reuse complete selected method, field, outgoing-call and fuzzy-reference sets across
  pages, with bounded session storage, verified publication, invalidation and cleanup.
  Oversized sets and unavailable cache space retain the normal scan path.
- Return byte-bounded complete reference prefixes with exact `next_offset` continuations
  instead of requiring an oversized-page retry. `limit` remains the maximum row count.
- Reduce nullable output-schema validation overhead while preserving the accepted value
  types and supporting older Pydantic schema generation.
- Add optional compact manifest/native summaries, standalone DEX entry browsing and
  exact class/name selectors in method-tracing prompts.
- Preserve original-byte reference accuracy checks and complete-collection/concurrency
  measurements. Timing changes are workload-specific; universal startup, repeated-query
  and total-memory improvements are not claimed.

## 0.2.3

- Add checked native DEX references, declaration/string discovery, class outlines,
  hierarchy, disassembly, instruction search and bounded incoming/outgoing call graphs.
  Ship native Linux/Windows wheels with an independent Python decoder fallback.
- Accept exact class and method names in source, disassembly, reference and call-graph
  queries. Return full identities; reject ambiguous overloads and support prototype filters.
- Add literal string-reference navigation, fuzzy member filters, read/write selection,
  original instruction offsets, cross-DEX provenance and global pagination.
- Add immutable hash-bound DEX sessions, concurrent bounded queries, cancellation,
  lifecycle cleanup, optional durable indexes and actual preparation progress.
- Reduce preparation metadata and query allocations with compact class-owner dictionaries,
  bounded DEX prefetching and shared read-only native input mappings. Recheck input
  identities after the final complete hash, including path replacement.
- Add archive capability inventories, resumable resource pages, structured manifests,
  certificate inventories, revision comparison, redacted secret candidates, resource
  templates and investigation prompts. Support bare DEX and selected container DEX inputs.
- Add optional Rust ASC integration, strict DEX 041 normalization and cross-platform
  package checks for Python 3.10-3.13, including canonical-source/native-wheel identity,
  original-DEX accuracy oracles, real stdio/HTTP workflows and signing/stability fixtures.

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
