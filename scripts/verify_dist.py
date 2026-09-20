"""Verify an sdist and its wheel in a clean environment (Python 3.12+ and uv)."""

import argparse
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdist", type=Path)
    parser.add_argument("wheel", type=Path)
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    env = os.environ.copy()
    for name in ("ASC_TEST_APK", "ASC_TEST_ROOT", "PYTHONPATH", "VIRTUAL_ENV"):
        env.pop(name, None)
    with tempfile.TemporaryDirectory(prefix="droidasc-dist-") as directory:
        root = Path(directory)
        with tarfile.open(args.sdist) as archive:
            members = archive.getnames()
            required = (
                "tests/conftest.py",
                "tests/process_fixture.py",
                "README.zh-CN.md",
                "docs/VALIDATION.md",
                "uv.lock",
                "scripts/verify_dist.py",
            )
            for name in required:
                assert any(item.endswith("/" + name) for item in members), name
            assert not any(
                "/artifacts/" in item or item.endswith((".apk", ".xapk")) for item in members
            )
            archive.extractall(root, filter="data")
        (project,) = root.iterdir()

        def run(command, cwd=project):
            subprocess.run(command, cwd=cwd, env=env, check=True, timeout=240)

        run(["uv", "sync", "--locked", "--extra", "dev", "--python", sys.executable])
        python = project / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        run([str(python), "-m", "pytest", "-q"])
        # Replace editable installation with the built wheel; never import the original checkout.
        run(
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(python),
                "--no-deps",
                "--reinstall",
                str(wheel),
            ]
        )
        run(
            [
                str(python),
                "-c",
                "import droidasc_mcp; "
                "assert 'site-packages' in droidasc_mcp.__file__; print(droidasc_mcp.__file__)",
            ],
            root,
        )
        run([str(python), "-m", "pytest", "-q"])
        run([str(python), "-m", "droidasc_mcp", "--help"], root)
    print("sdist and wheel acceptance passed")


if __name__ == "__main__":
    main()
