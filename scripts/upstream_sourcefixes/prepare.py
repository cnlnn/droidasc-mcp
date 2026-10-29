"""Prepare an offline, hash-locked local ASC source-fix candidate (Python 3.10+)."""

from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
BUNDLE = Path(__file__).resolve().parent
RUNTIME_NOTICE = (
    b"# Modified by cnlnn/droidasc-mcp on 2026-10-30.\n"
    b"# Downstream fixes: load lazy method annotations; preserve original field,\n"
    b"# parameter, return, and array class links; exclude this/super keyword links.\n\n"
)
BUILD_NOTICE = (
    b"# Modified by cnlnn/droidasc-mcp on 2026-10-30.\n"
    b"# Downstream build: local sourcefixes.2 version for annotation and type-link fixes.\n\n"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(
        name for name in before.keys() | after.keys() if before.get(name) != after.get(name)
    )


def prepare_source(sdist: Path, output: Path, *, bundle: Path = BUNDLE) -> dict:
    """Apply reviewed runtime hunks to the locked official source archive copy."""
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))
    from verify_dist import extract_sdist

    manifest_path = bundle / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["schema"] != 1:
        raise ValueError("Unsupported source-fix manifest schema")
    sdist = sdist.resolve(strict=True)
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError("Output path already exists")
    expected_size = manifest["sdist"]["size_bytes"]
    with sdist.open("rb") as stream:
        snapshot = stream.read(expected_size + 1)
    if (
        len(snapshot) != expected_size
        or hashlib.sha256(snapshot).hexdigest() != manifest["sdist"]["sha256"]
    ):
        raise ValueError("Official sdist SHA-256 mismatch")
    patch_paths = []
    for patch in manifest["patches"]:
        path = bundle / patch["filename"]
        if path.parent != bundle or sha256(path) != patch["sha256"]:
            raise ValueError("Reviewed patch SHA-256 mismatch")
        patch_paths.append(path.resolve())
    if sha256(bundle / "LICENSE") != manifest["license_sha256"]:
        raise ValueError("Bundled upstream license SHA-256 mismatch")
    if not output.parent.is_dir():
        raise ValueError("Output parent directory must exist")
    with tempfile.TemporaryDirectory(prefix="asc-sourcefixes-", dir=output.parent) as temporary:
        stage = Path(temporary)
        with tarfile.open(fileobj=io.BytesIO(snapshot)) as archive:
            extract_sdist(archive, stage)
        entries = list(stage.iterdir())
        if (
            len(entries) != 1
            or entries[0].name != manifest["sdist"]["root"]
            or not entries[0].is_dir()
        ):
            raise ValueError("Unexpected official sdist root")
        source = entries[0]
        before = file_hashes(source)
        runtime_path = manifest["runtime_path"]
        if before.get(runtime_path) != manifest["original_runtime_sha256"]:
            raise ValueError("Official ASC runtime SHA-256 mismatch")
        if before.get("LICENSE") != manifest["license_sha256"]:
            raise ValueError("Official upstream license SHA-256 mismatch")
        python_files = {
            name: digest
            for name, digest in before.items()
            if name.startswith(("droidasc/", "dadguard/")) and name.endswith(".py")
        }
        dadguard_files = {
            name: digest for name, digest in python_files.items() if name.startswith("dadguard/")
        }
        if (
            len(python_files) != manifest["python_files"]
            or len(dadguard_files) != manifest["dadguard_python_files"]
        ):
            raise ValueError("Official dependency source inventory mismatch")
        env = os.environ.copy()
        for variable in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
            env.pop(variable, None)
        env["GIT_CEILING_DIRECTORIES"] = str(stage)
        commands = []
        for patch in patch_paths:
            for check in (True, False):
                command = [
                    "git",
                    "-c",
                    "core.autocrlf=false",
                    "apply",
                    "--whitespace=nowarn",
                    f"--include={runtime_path}",
                ]
                if check:
                    command.append("--check")
                command.append(str(patch))
                try:
                    subprocess.run(
                        command, cwd=source, env=env, check=True, capture_output=True, timeout=30
                    )
                except subprocess.CalledProcessError as error:
                    diagnostic = (error.stderr or b"").decode("utf-8", errors="replace").strip()
                    diagnostic = " | ".join(diagnostic.splitlines()) or "Git returned no stderr"
                    raise ValueError(f"{patch.name} failed: {diagnostic}") from error
                commands.append(
                    {
                        "patch": patch.name,
                        "included_path": runtime_path,
                        "check_only": check,
                        "exit_code": 0,
                    }
                )
        runtime = source / runtime_path
        if sha256(runtime) != manifest["evaluated_runtime_sha256"]:
            raise ValueError("Evaluated ASC runtime SHA-256 mismatch")
        evaluated = runtime.read_bytes()
        runtime.write_bytes(RUNTIME_NOTICE + evaluated)
        evaluated_ast = ast.dump(ast.parse(evaluated), include_attributes=False)
        prepared_ast = ast.dump(ast.parse(runtime.read_bytes()), include_attributes=False)
        if prepared_ast != evaluated_ast:
            raise ValueError("Downstream runtime notice changed executable AST")
        if sha256(runtime) != manifest["prepared_runtime_sha256"]:
            raise ValueError("Prepared ASC runtime SHA-256 mismatch")
        pyproject = source / "pyproject.toml"
        original = pyproject.read_bytes()
        old = f'version = "{manifest["original_source_version"]}"'.encode("ascii")
        new = f'version = "{manifest["local_version"]}"'.encode("ascii")
        if original.count(old) != 1:
            raise ValueError("Unexpected official project version declaration")
        pyproject.write_bytes(BUILD_NOTICE + original.replace(old, new))
        readme = source / "README.md"
        notice = (
            "# Local source compatibility build\n\n"
            f"This local {manifest['local_version']} candidate adds lazy method annotation\n"
            "directory resolution and preserves original class types in source tokens.\n"
            "Only the ASC decompiler runtime file changes; released dadguard files\n"
            "and the original Apache-2.0 license remain unchanged.\n\n"
        ).encode("ascii")
        readme.write_bytes(notice + readme.read_bytes())
        after = file_hashes(source)
        changes = changed_paths(before, after)
        if changes != manifest["expected_changed_paths"]:
            raise ValueError(f"Unexpected prepared source changes: {changes}")
        runtime_changes = changed_paths(python_files, {name: after[name] for name in python_files})
        if runtime_changes != [runtime_path] or any(
            after[name] != digest for name, digest in dadguard_files.items()
        ):
            raise ValueError("Prepared dependency runtime change boundary mismatch")
        if sha256(sdist) != manifest["sdist"]["sha256"]:
            raise ValueError("Official sdist changed during preparation")
        receipt = {
            "status": "offline_local_source_candidate_prepared",
            "source_directory": "source",
            "local_version": manifest["local_version"],
            "official_sdist_sha256": manifest["sdist"]["sha256"],
            "manifest_sha256": sha256(manifest_path),
            "tool_sha256": sha256(Path(__file__)),
            "patches": manifest["patches"],
            "patch_commands": commands,
            "application_scope": "runtime_hunks_only",
            "contribution_test_hunks_applied": False,
            "changed_source_paths": changes,
            "changed_runtime_paths": runtime_changes,
            "unchanged_released_dadguard_python_files": len(dadguard_files),
            "evaluated_runtime_sha256": manifest["evaluated_runtime_sha256"],
            "prepared_runtime_sha256": after[runtime_path],
            "runtime_ast_unchanged_by_notice": True,
            "runtime_ast_sha256": hashlib.sha256(evaluated_ast.encode()).hexdigest(),
            "runtime_ast_python_version": sys.version.split()[0],
            "source_files_sha256": after,
            "original_archive_unchanged": True,
            "built_or_installed": False,
            "default_dependency_changed": False,
        }
        output.mkdir()
        source.rename(output / "source")
        with (output / "receipt.json").open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, indent=2)
            stream.write("\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sdist", required=True, type=Path, help="Original official droidasc sdist"
    )
    parser.add_argument(
        "--output", required=True, type=Path, help="New output directory under an existing parent"
    )
    args = parser.parse_args()
    try:
        result = prepare_source(args.sdist, args.output)
    except (OSError, ValueError, tarfile.TarError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Preparation failed: {error}\n")
    print(
        json.dumps(
            {key: value for key, value in result.items() if key != "source_files_sha256"}, indent=2
        )
    )


if __name__ == "__main__":
    main()
