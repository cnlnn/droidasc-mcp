"""Start a Python module only after its supervisor has attached lifetime controls."""

import os
import sys


def main():
    if sys.stdin.buffer.read(1) != b"\x01":
        raise SystemExit("Worker startup handshake failed")
    sys.stdin.close()
    with open(os.devnull, encoding="utf-8") as stdin:
        sys.stdin = sys.__stdin__ = stdin
        # Restore the argv and module search path of `python -m target ...`.
        sys.argv = sys.argv[1:]
        sys.path[0] = os.getcwd()
        import runpy

        runpy.run_module(sys.argv[0], run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
