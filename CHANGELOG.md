# Changelog

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
