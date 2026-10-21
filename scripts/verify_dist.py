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
                "tests/conftest.py",
                "tests/process_fixture.py",
                "README.zh-CN.md",
                "docs/VALIDATION.md",
                "docs/COMPETITOR_API_AUDIT.md",
                "scripts/audit_competitor.py",
                "tests/test_competitor_audit.py",
                "uv.lock",
                "scripts/verify_dist.py",
                "scripts/verify_archive_workflow.py",
                "scripts/verify_signing.py",
                "scripts/benchmark_call_graph.py",
                "src/droidasc_mcp/archive_worker.py",
                "src/droidasc_mcp/manifest.py",
                "src/droidasc_mcp/call_graph.py",
                "src/droidasc_mcp/signing.py",
                "src/droidasc_mcp/containers.py",
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
                "scripts/stability_check.py",
                "scripts/stability_dex.py",
                "scripts/validate_corpus.py",
                "src/droidasc_mcp/MethodBridge.java",
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
            archive.extractall(root, filter="data")
        (project,) = root.iterdir()

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
