"""Apply worker limits, then start a Python module under supervisor control."""

import os
import sys

MEMORY_ERROR_MARKER = b"DROIDASC_MCP_MEMORY_LIMIT_EXCEEDED\n"


def _apply_memory_limit():
    raw = os.getenv("DROIDASC_MCP_WORKER_MEMORY_BYTES")
    if raw is None or os.name == "nt":
        return
    limit = int(raw)
    import resource

    current_soft, current_hard = resource.getrlimit(resource.RLIMIT_AS)
    del current_soft
    if current_hard != resource.RLIM_INFINITY:
        limit = min(limit, current_hard)
    resource.setrlimit(resource.RLIMIT_AS, (limit, limit))


def main():
    if os.getenv("DROIDASC_MCP_START_GATE") == "1":
        if sys.stdin.buffer.read(1) != b"\x01":
            raise SystemExit("Worker startup handshake failed")
        sys.stdin.close()
    _apply_memory_limit()
    with open(os.devnull, encoding="utf-8") as stdin:
        sys.stdin = sys.__stdin__ = stdin
        # Restore the argv and module search path of `python -m target ...`.
        sys.argv = sys.argv[1:]
        sys.path[0] = os.getcwd()
        try:
            import runpy

            runpy.run_module(sys.argv[0], run_name="__main__", alter_sys=True)
        except MemoryError:
            os.write(2, MEMORY_ERROR_MARKER)
            raise SystemExit(122) from None


if __name__ == "__main__":
    main()
