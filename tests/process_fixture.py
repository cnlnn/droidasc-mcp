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
    if mode == "getmanifest":
        (root.parent / "worker.pid").write_text(str(os.getpid()))
        time.sleep(15)
        print("<manifest />")
        return
    if mode == "memory":
        chunks = []
        while True:
            chunks.append(bytearray(8 * 1024 * 1024))
    if mode == "child":
        (root / "child.pid").write_text(str(os.getpid()))
        time.sleep(15)
        return
    if mode == "grandchild":
        (root / "grandchild.pid").write_text(str(os.getpid()))
        time.sleep(15)
        return
    if mode == "branch":
        (root / "child.pid").write_text(str(os.getpid()))
        subprocess.Popen([sys.executable, "-m", "process_fixture", "grandchild", str(root)])
        time.sleep(15)
        return
    if mode == "orphan-tree":
        (root / "parent.pid").write_text(str(os.getpid()))
        subprocess.Popen([sys.executable, "-m", "process_fixture", "branch", str(root)])
        return
    if mode in {"detached", "tree-stdout"}:
        (root / "parent.pid").write_text(str(os.getpid()))
        subprocess.Popen(
            [sys.executable, "-m", "process_fixture", "child", str(root)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 5
        while not (root / "child.pid").exists():
            if time.monotonic() >= deadline:
                raise RuntimeError("Child readiness timed out")
            time.sleep(0.01)
        if mode == "detached":
            print("ok")
            return
        mode = "stdout"
    if mode in {"orphan", "tree"}:
        (root / "parent.pid").write_text(str(os.getpid()))
        subprocess.Popen([sys.executable, "-m", "process_fixture", "child", str(root)])
        if mode == "tree":
            time.sleep(15)
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
    if mode == "touch":
        (root / "touched").write_text("started")
        assert sys.stdin.read() == ""


if __name__ == "__main__":
    main()
