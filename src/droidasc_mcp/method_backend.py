"""Optional version-pinned JADX public API and dexlib2 bridge, inside the DEX worker."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from .runner import DroidAscError


def java_command(settings, workspace, source="MethodBridge.java"):
    home = settings.jadx_home
    java = settings.java_executable or shutil.which("java")
    if not home or not java:
        return {
            "status": "error",
            "code": "backend_unavailable",
            "message": "Configure DROIDASC_MCP_JADX_HOME (JADX 1.5.5) and a Java 17+ JDK",
        }
    jars = sorted((home / "lib").glob("*.jar"))
    if not jars:
        return {
            "status": "error",
            "code": "backend_unavailable",
            "message": "JADX home must contain its distribution lib/*.jar",
        }
    temporary = workspace / "jvm"
    temporary.mkdir()
    return [
        str(java),
        "-Xmx512m",
        "-Xss512k",
        "-XX:+UseSerialGC",
        "-XX:CompressedClassSpaceSize=64m",
        "-XX:ReservedCodeCacheSize=64m",
        "-XX:-CreateCoredumpOnCrash",
        f"-XX:ErrorFile={os.devnull}",
        f"-Djava.io.tmpdir={temporary}",
        f"-Duser.home={temporary}",
        "-Dfile.encoding=UTF-8",
        "--class-path",
        os.pathsep.join(map(str, jars)),
        str(Path(__file__).with_name(source)),
    ]


def query_methods(settings, bundle, entry, query, workspace=None):
    workspace = workspace or bundle.parent
    command = java_command(settings, workspace)
    if isinstance(command, dict):
        return command
    offset, limit = query["offset"], min(query["limit"], settings.max_page_size)
    command += [
        str(bundle),
        entry,
        query["class_name"],
        query["operation"],
        (
            query.get("field_descriptor")
            if query["operation"] == "find_field_refs"
            else query.get("method_descriptor")
        )
        or "",
        query.get("source_format", "auto"),
        str(min(offset, 2**31 - 1)),
        str(min(limit, 2**31 - 1)),
        query.get("field_access", "all"),
    ]
    return _execute_java(settings, command, workspace, offset, limit)


def query_discovery(settings, bundle, query, workspace):
    command = java_command(settings, workspace, "DiscoveryBridge.java")
    if isinstance(command, dict):
        return command
    offset, limit = query["offset"], min(query["limit"], settings.max_page_size)
    command += [
        str(bundle),
        query["operation"],
        query.get("kind") or "",
        query.get("value") or "",
        query.get("class_name") or "",
        str(min(offset, 2**63 - 1)),
        str(limit),
    ]
    return _execute_java(settings, command, workspace, offset, limit)


def _execute_java(settings, command, workspace, offset, limit):
    # The caller's supervisor owns this descendant, including cancellation and Job limits.
    try:
        process = subprocess.Popen(
            command, cwd=workspace, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE
        )
    except OSError as exc:
        raise DroidAscError("Could not start configured Java executable") from exc
    with process:
        output = process.stdout.read(settings.max_output_bytes + 1)
        if len(output) > settings.max_output_bytes:
            process.kill()
            raise DroidAscError("Method backend output exceeds configured stream limit")
        if process.wait() != 0:
            raise DroidAscError("Method backend failed; check configured JADX and Java versions")
    try:
        result = json.loads(output)
    except (ValueError, UnicodeError) as exc:
        raise DroidAscError("Method backend returned invalid JSON") from exc
    if not isinstance(result, dict) or "status" not in result:
        raise DroidAscError("Method backend returned an invalid result")
    result.update(offset=offset, limit=limit)
    if "total" in result:
        result["has_more"] = offset + limit < result["total"]
        result["truncated"] = result["has_more"]
        result["next_offset"] = offset + limit if result["has_more"] else None
    return result
