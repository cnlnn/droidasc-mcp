"""Launch a configured native CLI under the existing bootstrap and process-tree limits."""

import subprocess
import sys


def main():
    # Windows children inherit the bootstrap's Job Object; POSIX children inherit its group/rlimit.
    raise SystemExit(subprocess.call(sys.argv[1:], stdin=subprocess.DEVNULL))


if __name__ == "__main__":
    main()
