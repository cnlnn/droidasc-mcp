# Changelog

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
