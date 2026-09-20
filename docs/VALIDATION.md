# Local acceptance checks

## Reproduce

```bash
uv sync --locked --extra dev
uv run pytest -q -s --junitxml=artifacts/validation/tests.xml -o junit_logging=all
ASC_TEST_APK=/absolute/path/to/a/local.apk uv run pytest -q -s \
  --junitxml=artifacts/validation/with-apk.xml -o junit_logging=all
uv run ruff check .
uv build
uv run python scripts/verify_dist.py dist/droidasc_mcp-0.1.2.tar.gz dist/droidasc_mcp-0.1.2-py3-none-any.whl
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

- RSS sampling measures the host process, not a hard whole-process-tree memory limit. These small
  synthetic workloads are regression checks, not an arbitrary-malformed-APK stress benchmark.
- A killed Linux child may remain a zombie until its reaper runs; the test checks that it cannot
  execute, not that the PID instantly disappears.
- The order test uses controlled output; it does not demonstrate a real ASC scheduling race.
- Immediate client cancellation, immutable content-addressed pagination,
  and lossless parsing of embedded newlines in ASC text remain unsupported or unverified.
- HTTP is loopback-only in these tests; there is no authenticated remote-deployment acceptance.
- Local measurements do not imply remote CI success; inspect the commit's GitHub Actions checks.
