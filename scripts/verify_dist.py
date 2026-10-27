"""Verify an sdist and its wheel in a clean environment (Python 3.10+ and uv)."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from email.parser import BytesParser
from pathlib import Path


def extract_sdist(archive: tarfile.TarFile, root: Path) -> None:
    """Extract portable regular source files without version-specific tar filters."""
    members = archive.getmembers()
    seen = set()
    for member in members:
        name = member.name.removesuffix("/") if member.isdir() else member.name
        parts = name.split("/")
        if (
            not (member.isdir() or member.isfile())
            or "\\" in name
            or any(
                not part
                or part in {".", ".."}
                or ":" in part
                or part.endswith((".", " "))
                or any(ord(char) < 32 for char in part)
                for part in parts
            )
            or name.casefold() in seen
        ):
            raise ValueError(f"Unsafe or duplicate sdist member: {member.name!r}")
        seen.add(name.casefold())
    if any(root.iterdir()):
        raise ValueError("sdist extraction requires an empty directory")
    for member in members:
        target = root.joinpath(*member.name.removesuffix("/").split("/"))
        if member.isdir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as source, target.open("xb") as output:
                shutil.copyfileobj(source, output)


def distribution_identity(project: Path, wheel: Path) -> tuple[str, dict[str, str]]:
    """Bind packaged source/data and metadata to the canonical source archive."""
    source = project / "src" / "droidasc_mcp"
    source_files = {
        path.relative_to(source).as_posix(): path.read_bytes()
        for path in source.rglob("*")
        if path.is_file() and path.suffix in {".py", ".java", ".c", ".json"}
    }
    source_metadata = BytesParser().parsebytes((project / "PKG-INFO").read_bytes())
    with zipfile.ZipFile(wheel) as archive:
        metadata_names = [
            name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
        ]
        assert len(metadata_names) == 1, metadata_names
        metadata = BytesParser().parsebytes(archive.read(metadata_names[0]))
        for field in ("Name", "Version"):
            assert source_metadata[field] and source_metadata[field] == metadata[field], field
        package_files = {
            name.removeprefix("droidasc_mcp/"): archive.read(name)
            for name in archive.namelist()
            if name.startswith("droidasc_mcp/") and not name.endswith("/")
        }
    packaged_source = {
        name: data
        for name, data in package_files.items()
        if Path(name).suffix in {".py", ".java", ".c", ".json"}
    }
    assert packaged_source == source_files, "Wheel source/data differs from canonical sdist"
    native = [
        name
        for name in package_files
        if name.startswith("_dexscan.") and name.endswith((".so", ".pyd"))
    ]
    assert len(native) == 1, "Expected exactly one native accelerator in release wheel"
    return metadata["Version"], {
        name: hashlib.sha256(data).hexdigest() for name, data in package_files.items()
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdist", type=Path)
    parser.add_argument("wheel", type=Path)
    parser.add_argument("--fixture-apk", type=Path, help="Built public acceptance APK")
    parser.add_argument("--complex-apk", type=Path, help="R8/Kotlin release fixture")
    parser.add_argument("--complex-mapping", type=Path, help="R8 acceptance-side mapping")
    args = parser.parse_args()
    wheel = args.wheel.resolve()
    env = os.environ.copy()
    for name in (
        "ASC_TEST_APK",
        "ASC_TEST_COMPLEX_APK",
        "ASC_TEST_COMPLEX_MAPPING",
        "ASC_TEST_EXPECT_FIXTURE",
        "ASC_TEST_ROOT",
        "PYTHONPATH",
        "VIRTUAL_ENV",
    ):
        env.pop(name, None)
    if args.fixture_apk:
        fixture_apk = args.fixture_apk.resolve(strict=True)
        if not fixture_apk.is_file():
            parser.error("--fixture-apk must be a file")
        env["ASC_TEST_APK"] = str(fixture_apk)
        env["ASC_TEST_EXPECT_FIXTURE"] = "1"
        if not args.complex_apk or not args.complex_mapping:
            parser.error("--fixture-apk requires --complex-apk and --complex-mapping")
        env["ASC_TEST_COMPLEX_APK"] = str(args.complex_apk.resolve(strict=True))
        env["ASC_TEST_COMPLEX_MAPPING"] = str(args.complex_mapping.resolve(strict=True))
    with tempfile.TemporaryDirectory(prefix="droidasc-dist-") as directory:
        root = Path(directory)
        with tarfile.open(args.sdist) as archive:
            members = archive.getnames()
            required = (
                "NOTICE",
                "src/droidasc_mcp/reference_groups.py",
                "src/droidasc_mcp/reference_cursor.py",
                "src/droidasc_mcp/grouped_references.py",
                "tests/test_reference_groups.py",
                "tests/test_reference_cursor.py",
                "scripts/benchmark_reference_formats.py",
                "tests/conftest.py",
                "tests/process_fixture.py",
                "tests/preparation_worker.py",
                "README.zh-CN.md",
                "docs/VALIDATION.md",
                "docs/GOAL_02X.md",
                "docs/COMPETITOR_API_AUDIT.md",
                "docs/NATIVE_QUERY_VALIDATION.md",
                "scripts/audit_competitor.py",
                "tests/test_competitor_audit.py",
                "uv.lock",
                "scripts/verify_dist.py",
                "tests/test_distribution_identity.py",
                "scripts/verify_archive_workflow.py",
                "scripts/verify_signing.py",
                "scripts/benchmark_call_graph.py",
                "scripts/benchmark_competitor_runtime.py",
                "scripts/benchmark_revisions.py",
                "tests/test_revision_benchmark.py",
                "scripts/benchmark_cpu_wrapper.py",
                "scripts/verify_fuzzy_references.py",
                "scripts/verify_string_references.py",
                "scripts/verify_selected_set_parity.py",
                "scripts/verify_operand_page_benchmark.py",
                "scripts/verify_reference_page_benchmark.py",
                "scripts/verify_mcp_reference_pages.py",
                "tests/test_selected_set_parity.py",
                "scripts/verify_call_index.py",
                "scripts/verify_frontier_graph.py",
                "setup.py",
                "scripts/setup_dexlib.py",
                "src/droidasc_mcp/_dexscan.c",
                "src/droidasc_mcp/native_dex.py",
                "src/droidasc_mcp/native_scan.py",
                "src/droidasc_mcp/native_directory.py",
                "src/droidasc_mcp/native_snapshot.py",
                "src/droidasc_mcp/class_directory.py",
                "src/droidasc_mcp/preparation_directory.py",
                "tests/test_native_directory.py",
                "tests/test_mapped_queries.py",
                "tests/test_native_build.py",
                "tests/test_class_directory.py",
                "tests/test_preparation_directory.py",
                "scripts/verify_preparation_directory.py",
                "src/droidasc_mcp/tool_registry.py",
                "src/droidasc_mcp/output_schemas.json",
                "src/droidasc_mcp/input_schemas.py",
                "src/droidasc_mcp/input_schemas.json",
                "scripts/compile_output_schemas.py",
                "scripts/compile_input_schemas.py",
                "tests/test_tool_registry.py",
                "src/droidasc_mcp/worker_errors.py",
                "src/droidasc_mcp/worker_runtime.py",
                "src/droidasc_mcp/cli_worker.py",
                "src/droidasc_mcp/path_policy.py",
                "tests/test_worker_runtime.py",
                "src/droidasc_mcp/native_index.py",
                "src/droidasc_mcp/native_page.py",
                "src/droidasc_mcp/native_discovery.py",
                "src/droidasc_mcp/native_structure.py",
                "src/droidasc_mcp/native_strings.py",
                "tests/test_string_refs.py",
                "tests/fixtures/xrefs/string_refs/Caller.smali",
                "tests/test_native_dex.py",
                "tests/test_native_page.py",
                "src/droidasc_mcp/archive_worker.py",
                "src/droidasc_mcp/manifest.py",
                "src/droidasc_mcp/call_graph.py",
                "src/droidasc_mcp/signing.py",
                "src/droidasc_mcp/containers.py",
                "src/droidasc_mcp/preparation_zip.py",
                "tests/test_preparation_zip.py",
                "scripts/profile_zip_inventory.py",
                "tests/test_competitor_runtime.py",
                "tests/test_benchmark_cpu_wrapper.py",
                "src/droidasc_mcp/archive_errors.py",
                "src/droidasc_mcp/review.py",
                "src/droidasc_mcp/contracts.py",
                "src/droidasc_mcp/memory_cache.py",
                "tests/test_memory_cache.py",
                "src/droidasc_mcp/ReviewBridge.java",
                "tests/test_signing.py",
                "tests/test_containers.py",
                "tests/test_review.py",
                "tests/fixtures/xrefs/review_old/Review.smali",
                "tests/fixtures/xrefs/review_new/Review.smali",
                "tests/fixtures/xrefs/review_new/Added.smali",
                "tests/test_call_graph.py",
                "src/droidasc_mcp/native_graph.py",
                "tests/test_native_graph.py",
                "tests/test_call_graph_benchmark.py",
                "tests/fixtures/xrefs/oracle_polymorphic/Caller.smali",
                "scripts/stability_check.py",
                "scripts/stability_dex.py",
                "scripts/validate_corpus.py",
                "src/droidasc_mcp/MethodBridge.java",
                "tests/fixtures/java/InstructionCursorOracle.java",
                "tests/test_instruction_cursor.py",
                "tests/fixtures/xrefs/boundary/Ordering.smali",
                "scripts/benchmark_reference_scan.py",
                "src/droidasc_mcp/IndexBridge.java",
                "src/droidasc_mcp/DiscoveryBridge.java",
                "src/droidasc_mcp/StructureBridge.java",
                "tests/test_structure.py",
                "tests/fixtures/xrefs/structure/Base.smali",
                "tests/fixtures/xrefs/structure/Child.smali",
                "tests/fixtures/xrefs/structure/Contract.smali",
                "tests/fixtures/xrefs/structure/CycleA.smali",
                "tests/fixtures/xrefs/structure/CycleB.smali",
                "tests/fixtures/xrefs/structure/Payload.smali",
                "tests/fixtures/xrefs/structure/SecretPatterns.smali",
                "src/droidasc_mcp/source_metadata.py",
                "src/droidasc_mcp/DexContainerBridge.java",
                "src/droidasc_mcp/dex_container.py",
                "tests/test_dex_container.py",
                "tests/dex041_fixture.py",
                "src/droidasc_mcp/query_cache.py",
                "src/droidasc_mcp/durable_index.py",
                "src/droidasc_mcp/native_worker.py",
                "scripts/setup_rust.py",
                "tests/fixtures/xrefs/first/Types.smali",
                "tests/fixtures/xrefs/first/Caller.smali",
                "tests/fixtures/xrefs/graph_first/GraphA.smali",
                "tests/fixtures/xrefs/graph_second/GraphB.smali",
                "tests/fixtures/xrefs/boundary/Boundary.smali",
                "tests/fixtures/xrefs/memo_first/MemoA.smali",
                "tests/fixtures/xrefs/memo_second/MemoB.smali",
                "tests/fixtures/android/complex/src/main/java/org/example/complex/CoroutineCases.kt",
            )
            for name in required:
                assert any(item.endswith("/" + name) for item in members), name
            assert not any(
                "/artifacts/" in item or item.endswith((".apk", ".xapk", ".dex"))
                for item in members
            )
            extract_sdist(archive, root)
        (project,) = root.iterdir()
        version, package_hashes = distribution_identity(project, wheel)
        print(f"Canonical sdist/wheel source identity passed: {version}", flush=True)

        def run(command, cwd=project):
            subprocess.run(command, cwd=cwd, env=env, check=True, timeout=1800)

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
                "import hashlib, importlib.metadata, json, pathlib, sys; "
                "import droidasc_mcp, droidasc_mcp._dexscan; "
                "root = pathlib.Path(droidasc_mcp.__file__).parent; "
                "assert 'site-packages' in root.parts; "
                "assert importlib.metadata.version('droidasc-mcp') == sys.argv[1]; "
                "expected = json.loads(sys.argv[2]); "
                "actual = {p.relative_to(root).as_posix(): "
                "hashlib.sha256(p.read_bytes()).hexdigest() "
                "for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}; "
                "assert actual == expected, 'Installed package differs from accepted wheel'; "
                "assert pathlib.Path(droidasc_mcp._dexscan.__file__).parent == root; "
                "print('Installed wheel byte identity passed:', root)",
                version,
                json.dumps(package_hashes),
            ],
            root,
        )
        run([str(python), "-m", "pytest", "-q"])
        run([str(python), "-m", "droidasc_mcp", "--help"], root)
    print("sdist and wheel acceptance passed")


if __name__ == "__main__":
    main()
