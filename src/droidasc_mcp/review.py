"""Declaration comparison and candidate search through the pinned dexlib2 backend."""

from __future__ import annotations

import json
from pathlib import Path

from .method_backend import _execute_java, java_command

PATTERNS = {
    "all",
    "aws_access_key_id",
    "github_classic_token",
    "google_api_key",
    "private_key_marker",
    "credential_assignment",
    "jwt_like",
}


def query_review(settings, bundle, common, query, workspace):
    command = java_command(settings, workspace, "ReviewBridge.java")
    if isinstance(command, dict):
        return command
    offset, limit = query["offset"], query["limit"]
    if query["operation"] == "revision_diff":
        other = Path(query["other_prepared_root"])
        metadata = json.loads((other / "prepared.json").read_text(encoding="utf-8"))["common"]
        if metadata["engine_version"] != common["engine_version"]:
            return {"status": "error", "code": "engine_changed"}
        command += [
            "diff",
            str(bundle),
            str(other / "analysis.apk"),
            query["kind"],
            query["change"],
            str(min(offset, 2**63 - 1)),
            str(limit),
        ]
        result = _execute_java(settings, command, workspace, offset, limit)
        result.update(
            old_input_id=common["input_id"],
            new_input_id=metadata["input_id"],
            old_sources=common["sources"],
            new_sources=metadata["sources"],
        )
        for key in ("artifact_sha256", "artifact_path"):
            if key in common:
                result["old_" + key] = common[key]
            if key in metadata:
                result["new_" + key] = metadata[key]
        return result
    command += [
        "secrets",
        str(bundle),
        query["pattern"],
        str(min(offset, 2**63 - 1)),
        str(limit),
        str(query["max_scan_bytes"]),
        str(query.get("include_values", False)).lower(),
    ]
    return _execute_java(settings, command, workspace, offset, limit)
