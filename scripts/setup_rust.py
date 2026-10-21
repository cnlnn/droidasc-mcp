"""Build the pinned, optional Rust CLI for acceptance; never run on server startup."""

import argparse
import os
import subprocess
from pathlib import Path

COMMIT = "236dd096669c99eb30f6e1af0b24e668eff55dd5"
RADGUARD = "290de20c925c4a2c7642b1a63c9997185a06e130"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--existing", type=Path)
    args = parser.parse_args()
    if args.existing:
        directory = args.existing.resolve()
    else:
        root = Path("artifacts/rust_ASC").resolve()
        if not root.exists():
            subprocess.run(
                ["git", "clone", "https://github.com/MG1937/rust_ASC.git", str(root)],
                check=True,
                timeout=180,
            )

        def run(*command):
            return subprocess.check_output(command, cwd=root, timeout=600).decode().strip()

        run("git", "checkout", "--detach", COMMIT)
        run("git", "submodule", "update", "--init", "--recursive")
        assert run("git", "rev-parse", "HEAD") == COMMIT
        assert run("git", "-C", "radguard", "rev-parse", "HEAD") == RADGUARD
        run("cargo", "build", "--release", "--locked", "--no-default-features")
        directory = root / "target" / "release"
    binary = directory / ("rust_ASC.exe" if os.name == "nt" else "rust_ASC")
    assert binary.is_file(), binary
    if os.name != "nt":
        binary.chmod(binary.stat().st_mode | 0o100)
    if os.getenv("GITHUB_ENV"):
        with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as output:
            output.write(f"DROIDASC_MCP_RUST_ASC={binary}\n")
    print(f"Rust acceptance binary: {binary}")


if __name__ == "__main__":
    main()
