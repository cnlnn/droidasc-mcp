"""Bounded, benign subprocess workloads for supervisor integration tests."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    mode, directory = sys.argv[1:3]
    root = Path(directory)
    if mode == "child":
        (root / "child.pid").write_text(str(os.getpid()))
        time.sleep(15)
        return
    if mode == "orphan":
        subprocess.Popen([sys.executable, "-m", "process_fixture", "child", str(root)])
        return
    if mode in {"stdout", "stderr"}:
        stream = sys.stdout.buffer if mode == "stdout" else sys.stderr.buffer
        # Finite producer: even a broken supervisor cannot run this indefinitely.
        for _ in range(256):
            stream.write(b"x" * 8192)
            stream.flush()
            time.sleep(0.001)
        return
    if mode == "refs":
        count_file = root / "count"
        count = int(count_file.read_text()) + 1 if count_file.exists() else 1
        count_file.write_text(str(count))
        lines = [f"classes{i}.dex | LExample;->run | matched=(hello)" for i in range(6)]
        if count % 2:
            lines.reverse()
        print("\n".join(lines))
        return
    if mode == "info":
        print(json.dumps({"pid": os.getpid()}))


if __name__ == "__main__":
    main()
