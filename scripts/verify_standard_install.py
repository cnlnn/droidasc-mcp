"""Verify ordinary pip consumers of canonical distributions (Linux, Python 3.13)."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import resource
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
import xml.etree.ElementTree as ET
import zipfile
from contextlib import suppress
from email.parser import BytesParser
from pathlib import Path

SOURCE_URL = "https://github.com/cnlnn/droidasc-mcp.git"
SOURCE_SUBDIRECTORY = "third_party/droidasc_sourcefixes"
TEST_FILES = ("test_upstream_engine_source.py", "test_installed_upstream_identity.py")
TEST_NAMES = {
    "test_lazy_method_throws_annotation_survives_both_source_paths",
    "test_original_field_return_and_parameter_type_links",
    "test_array_and_super_tokens_keep_original_type_and_member_links",
    "test_complete_pages_preserve_source_identity_and_global_token_spans",
    "test_installed_upstream_matches_reviewed_source_candidate",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def probe(project: Path, identity_path: Path, source_sha: str) -> dict:
    """This branch runs with -I inside the fresh installed consumer, not checkout."""
    prefix = Path(sys.prefix).resolve()
    manifest = json.loads((project / SOURCE_SUBDIRECTORY / "manifest.json").read_text())
    identity = json.loads(identity_path.read_text())
    engine = importlib.metadata.distribution("droidasc")
    adapter = importlib.metadata.distribution("droidasc-mcp")
    direct_url = json.loads(engine.read_text("direct_url.json"))
    assert direct_url["url"] == SOURCE_URL
    assert direct_url["subdirectory"] == SOURCE_SUBDIRECTORY
    assert direct_url["vcs_info"] == {
        "vcs": "git",
        "requested_revision": source_sha,
        "commit_id": source_sha,
    }
    assert engine.version == manifest["version"]
    assert adapter.version == identity["version"]
    assert sorted(adapter.metadata.get_all("Requires-Dist", [])) == identity["requires_dist"]

    def files(distribution, prefixes, suffixes):
        result = {}
        for item in distribution.files:
            name = str(item).replace("\\", "/")
            if name.startswith(prefixes) and Path(name).suffix in suffixes:
                path = Path(distribution.locate_file(item)).resolve()
                assert path.is_relative_to(prefix), path
                result[name] = digest(path)
        return result

    expected_engine = {
        name: item["sha256"]
        for name, item in manifest["files"].items()
        if name.startswith(("droidasc/", "dadguard/")) and name.endswith(".py")
    }
    installed_engine = files(engine, ("droidasc/", "dadguard/"), {".py"})
    assert len(expected_engine) == len(installed_engine) == 80
    assert installed_engine == expected_engine
    original_dadguard = {
        name: item["official_sdist_sha256"]
        for name, item in manifest["files"].items()
        if name.startswith("dadguard/") and name.endswith(".py")
    }
    assert len(original_dadguard) == 23
    assert {name: installed_engine[name] for name in original_dadguard} == original_dadguard
    installed_mcp = files(adapter, ("droidasc_mcp/",), {".py", ".java", ".c", ".json"})
    assert len(installed_mcp) == 69
    assert installed_mcp == identity["runtime_sources_sha256"]
    from droidasc.asc_core.utils import decompiler

    from droidasc_mcp import _dexscan

    origins = {"engine": decompiler.__file__, "native_accelerator": _dexscan.__file__}
    assert all(Path(value).resolve().is_relative_to(prefix) for value in origins.values())
    assert _dexscan.__file__.endswith(".so")
    return {
        "status": "installed_provenance_and_bytes_verified",
        "prefix": str(prefix),
        "python": sys.version,
        "engine_version": engine.version,
        "mcp_version": adapter.version,
        "engine_direct_url": direct_url,
        "requires_dist": identity["requires_dist"],
        "engine_runtime_sha256": installed_engine,
        "original_dadguard_sha256": original_dadguard,
        "mcp_runtime_sha256": installed_mcp,
        "origins": origins,
    }


def verify(args) -> None:
    # Reuse the existing portable, traversal/link-rejecting archive extractor.
    from verify_dist import distribution_identity, extract_sdist

    assert sys.platform == "linux" and sys.version_info[:2] == (3, 13)
    assert re.fullmatch(r"[0-9a-f]{40}", args.source_sha)
    sdist, wheel = args.sdist.resolve(strict=True), args.wheel.resolve(strict=True)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    script = Path(__file__).resolve()
    cpus = sorted(os.sched_getaffinity(0))[:4]
    os.sched_setaffinity(0, cpus)
    resource.setrlimit(resource.RLIMIT_AS, (8 * 1024**3, 8 * 1024**3))
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("PIP_", "UV_", "GIT_", "ASC_TEST_"))
        and (
            not key.startswith("DROIDASC_MCP_")
            or key in {"DROIDASC_MCP_JADX_HOME", "DROIDASC_MCP_JAVA"}
        )
        and key
        not in {
            "PYTHONPATH",
            "PYTHONHOME",
            "VIRTUAL_ENV",
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "ALL_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
        }
    }
    env.update(
        PIP_CONFIG_FILE=os.devnull,
        PIP_INDEX_URL="https://pypi.org/simple",
        PIP_NO_INPUT="1",
        PIP_DISABLE_PIP_VERSION_CHECK="1",
        PYTHONDONTWRITEBYTECODE="1",
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_COUNT="1",
        GIT_CONFIG_KEY_0="http.sslVerify",
        GIT_CONFIG_VALUE_0="true",
        GIT_TERMINAL_PROMPT="0",
        _JAVA_OPTIONS="-Xms32m -Xmx512m -XX:ActiveProcessorCount=4 "
        "-XX:ReservedCodeCacheSize=64m -XX:CompressedClassSpaceSize=64m",
    )
    report = {
        "status": "running",
        "scope": "Linux Python 3.13 ordinary pip sdist and native-wheel consumers",
        "source_sha": args.source_sha,
        "helper_commit": os.getenv("GITHUB_SHA"),
        "inputs": {"sdist": digest(sdist), "wheel": digest(wheel)},
        "commands": [],
        "consumers": {},
        "limits": {"cpus": cpus, "address_space_bytes": 8 * 1024**3, "seconds": 1500},
        "no_seed_no_dependency_suppression_no_overlay": True,
        "https_certificate_validation": True,
        "local_proxy_used": False,
    }
    if args.provenance:
        provenance = json.loads(args.provenance.read_text())
        assert provenance["conclusion"] == "success" and provenance["status"] == "completed"
        assert provenance["repository"]["full_name"] == "cnlnn/droidasc-mcp"
        report["canonical_package_run"] = {
            "id": provenance["id"],
            "head_sha": provenance["head_sha"],
            "receipt_sha256": digest(args.provenance),
        }
    started = time.monotonic()

    def command(label, argv, cwd, timeout=600):
        stdout, stderr = output / f"{label}.stdout.log", output / f"{label}.stderr.log"
        row = {"label": label, "argv": [str(value) for value in argv], "cwd": str(cwd)}
        report["commands"].append(row)
        print(f"Running {label}", flush=True)
        with stdout.open("xb") as out, stderr.open("xb") as err:
            process = subprocess.Popen(
                row["argv"], cwd=cwd, env=env, stdout=out, stderr=err, start_new_session=True
            )
            try:
                remaining = 1500 - (time.monotonic() - started)
                row["exit_code"] = process.wait(timeout=max(1, min(timeout, remaining)))
                assert row["exit_code"] == 0, f"{label} failed; see {stderr}"
            finally:
                # Kill only this command's own process group, including stray workers.
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        return stdout.read_text()

    try:
        with tempfile.TemporaryDirectory(prefix="standard-consumer-") as directory:
            work = Path(directory)
            source = work / "source"
            source.mkdir()
            with tarfile.open(sdist) as archive:
                members = archive.getmembers()
                assert len(members) <= 10000
                assert sum(member.size for member in members) <= 512 * 1024**2
                assert all(member.size <= 64 * 1024**2 for member in members)
                extract_sdist(archive, source)
            (project,) = source.iterdir()
            assert project.is_dir()
            with zipfile.ZipFile(wheel) as archive:
                entries = archive.infolist()
                assert len(entries) == len({entry.filename for entry in entries}) <= 10000
                assert sum(entry.file_size for entry in entries) <= 512 * 1024**2
            version, package_hashes = distribution_identity(project, wheel)
            metadata = BytesParser().parsebytes((project / "PKG-INFO").read_bytes())
            requirements = sorted(metadata.get_all("Requires-Dist", []))
            engine_requirements = [item for item in requirements if re.match(r"droidasc\s*@", item)]
            expected_requirement = (
                f"droidasc @ git+{SOURCE_URL}@{args.source_sha}#subdirectory={SOURCE_SUBDIRECTORY}"
            )
            assert len(engine_requirements) == 1
            assert engine_requirements[0].replace(" ", "") == expected_requirement.replace(" ", "")
            runtime = {
                "droidasc_mcp/" + name: value
                for name, value in package_hashes.items()
                if Path(name).suffix in {".py", ".java", ".c", ".json"}
            }
            assert len(runtime) == 69
            checkout_source = script.parents[1] / "src/droidasc_mcp"
            assert all(
                digest(checkout_source / name.removeprefix("droidasc_mcp/")) == value
                for name, value in runtime.items()
            )
            identity = {
                "version": version,
                "requires_dist": requirements,
                "runtime_sources_sha256": runtime,
            }
            identity_path = output / "canonical-identity.json"
            identity_path.write_text(json.dumps(identity, indent=2) + "\n")
            for name in TEST_FILES:
                assert (project / "tests" / name).is_file(), name
            for label, artifact in (("sdist", sdist), ("wheel", wheel)):
                prefix = work / f"{label}-env"
                command(f"{label}-venv", [sys.executable, "-m", "venv", prefix], work)
                python = prefix / "bin/python"
                command(
                    f"{label}-empty",
                    [
                        python,
                        "-I",
                        "-c",
                        "import importlib.util; "
                        "assert importlib.util.find_spec('droidasc') is None; "
                        "assert importlib.util.find_spec('droidasc_mcp') is None; "
                        "print('Fresh venv: engine and MCP absent')",
                    ],
                    work,
                )
                command(
                    f"{label}-install",
                    [
                        python,
                        "-m",
                        "pip",
                        "install",
                        "--report",
                        output / f"{label}-pip-report.json",
                        artifact,
                    ],
                    work,
                )
                command(f"{label}-pip-check", [python, "-m", "pip", "check"], work)
                installed = json.loads(
                    command(
                        f"{label}-identity",
                        [
                            python,
                            "-I",
                            script,
                            "--probe",
                            project,
                            "--identity",
                            identity_path,
                            "--source-sha",
                            args.source_sha,
                        ],
                        work,
                    )
                )
                command(
                    f"{label}-pytest-tool",
                    [python, "-m", "pip", "install", "pytest>=8.3"],
                    work,
                    timeout=180,
                )
                junit = output / f"{label}-tests.xml"
                command(
                    f"{label}-tests",
                    [
                        python,
                        "-I",
                        "-m",
                        "pytest",
                        "-q",
                        "--import-mode=prepend",
                        *[project / "tests" / name for name in TEST_FILES],
                        f"--junitxml={junit}",
                        f"--basetemp={work / (label + '-tests')}",
                        "-o",
                        f"cache_dir={work / (label + '-pytest-cache')}",
                    ],
                    work,
                    timeout=180,
                )
                cases = ET.parse(junit).getroot().findall(".//testcase")
                assert len(cases) == 5 and {case.get("name") for case in cases} == TEST_NAMES
                assert not any(
                    case.find(tag) is not None
                    for case in cases
                    for tag in ("failure", "error", "skipped")
                )
                report["consumers"][label] = {
                    "identity": installed,
                    "real_worker_regressions": 4,
                    "installed_identity_tests": 1,
                    "tests": 5,
                    "failures": 0,
                    "errors": 0,
                    "skipped": 0,
                }
            report["status"] = "ordinary_pip_sdist_and_native_wheel_consumers_verified"
        report["owned_temporary_directory_removed"] = not work.exists()
    except BaseException as exc:
        report.update(status="failed", error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        report["elapsed_seconds"] = time.monotonic() - started
        report["helper_sha256"] = digest(script)
        report["extractor_sha256"] = digest(script.with_name("verify_dist.py"))
        report["evidence_sha256"] = {
            path.name: digest(path) for path in output.iterdir() if path.is_file()
        }
        with (output / "receipt.json").open("x") as stream:
            stream.write(json.dumps(report, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sdist", nargs="?", type=Path)
    parser.add_argument("wheel", nargs="?", type=Path)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, default=Path("standard-install-results"))
    parser.add_argument("--provenance", type=Path)
    parser.add_argument("--probe", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--identity", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.probe:
        assert args.identity
        print(json.dumps(probe(args.probe, args.identity, args.source_sha), indent=2))
    else:
        if args.sdist is None or args.wheel is None:
            parser.error("sdist and wheel are required")
        verify(args)


if __name__ == "__main__":
    main()
