# Changelog

## Unreleased

- Add an opt-in durable xref cache across sessions/server restarts, keyed by input/schema/backend
  hashes, with checksum verification, a separate byte/entry budget, TTL/LRU eviction, OS process
  locks and atomic publication. Keep default session cleanup and fresh-worker supervision.
  Verify restart reuse with Java unavailable, concurrent writers, corruption and killed writers.
- Make member discovery declaration-only rather than implicitly building the full xref index;
  add literal DEX string-pool discovery with entry/index provenance. Add bounded, hash-bound
  exact-page caching without retaining worker processes, and measure large-APK cold/warm costs.
- Add independently assembled field-reference boundary regressions: opcode-like bytes in
  adjacent code-item headers and array payloads must never become executable reference hits.
- Close the acceptance test's SQLite connection on Windows and retry transient JADX download
  failures with bounded backoff while retaining mandatory archive hash verification.
- Add bounded atomic session-lifetime SQLite xref indexes, exact type relationships across
  instructions/declarations/annotations, and literal method/field declaration discovery.
  Preserve streaming-query semantics, source identities and fail-closed incomplete scans.
- Add opt-in pinned Rust ASC APK backend with supervised native workers and explicit unverified
  coverage; keep Python ASC as the default and reject unsupported Rust hierarchy queries.
- Add MCP initialization guidance, an analysis-guide resource, two investigation prompts and
  explicit tool annotations. Record a source-backed competitor comparison and remaining gaps.
- Add `find_field_refs` for full `class->name:type` identities, read/write filters, static/instance
  access labels, exact instruction offsets and cross-DEX provenance. Same-name fields of different
  types remain distinct. Encoded initializers, reflection, inherited field resolution and handle
  targets are not represented as direct accesses. Verify both transports and malformed-scan failure.
- Upgrade the minimum and lock to ASC 0.1.2.post3. Explicit method Smali now uses its public
  `disassemble --method` CLI without a JVM, with optional debug directives and stable not-found errors.
- Add descriptor-exact incoming/outgoing method operands with DEX provenance, code-unit offsets,
  dynamic/unresolved diagnostics and bounded pagination through the optional dexlib2 backend.
  Decode opcodes according to each DEX version; reject unknown instructions instead of claiming
  complete coverage. These are static operands, not a resolved runtime call graph.
- Add cross-DEX and polymorphic-call instruction oracles, Smali reassembly, and a source-built
  Kotlin 2.1.0/R8 release fixture tested over both transports and clean package installations.
- Add immutable hash-bound DEX sessions with explicit close, idle TTL, count/disk limits,
  concurrent preparation reservations, active-query pinning and lifecycle cleanup.
- Add optional JADX 1.5.5/JDK 17 method queries: raw DEX full descriptors, exact Java lookup,
  exact-method baksmali fallback and explicit engine/fallback diagnostics. Existing ASC tools
  remain Java-independent. Existing `find_refs` remains best-effort ASC text.
- Add overload, constructor, synthetic bridge, Unicode, array/native method and real JVM
  cancellation acceptance over stdio/HTTP; package the Java source bridge in sdist and wheel.

- Add exact `extends` / `impl` queries for APK and DEX, with structured direct-declaration
  records, descriptor normalization and explicit rejection of inapplicable class filters.
- Hierarchy queries require Droid ASC 0.1.2.post2 or newer; the previous minimum 0.1.1.post1 lacks hierarchy
  commands and fails the new real-engine acceptance.
- Verify reference caller sets before and after decompilation through both MCP transports,
  forcing fresh queries so cached output cannot hide a call-order regression.
- Add `asc_analyze_dex` for explicit single/multi-DEX inputs through the public ASC entry point.
  Preserve original bytes and SHA-256 provenance; validate standard DEX headers, table bounds
  and integrity fields before creating private, temporary analysis containers.
- Reject duplicate class definitions, distinguish absent classes/empty searches/engine errors,
  and return an explicit not-applicable result for DEX manifest requests.
- Apply the existing allowed-root, concurrency, worker memory/time/output limits to DEX analysis.
  Parent-owned temporary directories are cleaned even after worker termination or cancellation.
- Add source-built DEX regression coverage, stdio/HTTP operations and bilingual usage boundaries.

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
