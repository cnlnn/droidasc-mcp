"""Bounded declaration comparison and redacted string-pool candidates, without Java."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .native_dex import dex_entries, page_result, utf16_key

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
    if query["operation"] == "revision_diff":
        other = Path(query["other_prepared_root"])
        metadata = json.loads((other / "prepared.json").read_text(encoding="utf-8"))["common"]
        if metadata["engine_version"] != common["engine_version"]:
            return {"status": "error", "code": "engine_changed"}
        result = _diff(bundle, other / "analysis.apk", query)
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
    else:
        result = _secrets(bundle, query)
    return page_result(result, query, settings)


def _diff(old, new, query):
    inventory, used = {}, 0
    for side, bundle in enumerate((old, new)):
        for entry, dex in dex_entries(bundle):
            for owner, cls in dex.classes():
                rows = [("class", owner)] if query["kind"] in {"all", "class"} else []
                if query["kind"] != "class":
                    fields, methods = dex.members(cls)
                    if query["kind"] in {"all", "field"}:
                        rows.extend(("field", name) for name, *_ in fields)
                    if query["kind"] in {"all", "method"}:
                        rows.extend(("method", name) for name, *_ in methods)
                for kind, name in rows:
                    used += len(name.encode("utf-8", "replace")) + len(entry) + 32
                    if used > 64 * 1024**2 or len(inventory) >= 1_000_000 and name not in inventory:
                        return {
                            "status": "error",
                            "code": "inventory_or_scan_error",
                            "diagnostic": "inventory_limit",
                        }
                    row = inventory.setdefault(name, [kind, None, None])
                    if row[side + 1] is not None:
                        return {
                            "status": "error",
                            "code": "inventory_or_scan_error",
                            "diagnostic": "duplicate_declaration",
                        }
                    row[side + 1] = entry
    counts = {"added": 0, "removed": 0, "unchanged": 0}
    items, total = [], 0
    offset, limit = query["offset"], query["limit"]
    for name in sorted(inventory, key=utf16_key):
        kind, before, after = inventory[name]
        state = "added" if before is None else "removed" if after is None else "unchanged"
        counts[state] += 1
        if state == "unchanged" or query["change"] not in {"all", state}:
            continue
        if offset <= total < offset + limit:
            items.append(
                {
                    "kind": kind,
                    "descriptor": name,
                    "change": state,
                    "old_dex_entry": before,
                    "new_dex_entry": after,
                }
            )
        total += 1
    return {
        "status": "ok",
        "items": items,
        "total": total,
        "counts": counts,
        "ordering": "full_descriptor_lexicographic",
        "scope": "class_and_member_identity_inventory_only",
        "behavior_comparison": "not_performed",
        "declaration_attributes_comparison": "not_performed",
    }


EXPRESSIONS = {
    "aws_access_key_id": r"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])",
    "github_classic_token": r"(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{36}(?![A-Za-z0-9])",
    "google_api_key": r"(?<![A-Za-z0-9_])AIza[0-9A-Za-z_-]{35}(?![A-Za-z0-9_-])",
    "private_key_marker": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED )?PRIVATE KEY-----",
    "credential_assignment": (
        r"(?i)(?:api[_-]?key|client[_-]?secret|access[_-]?token|"
        r"""secret|password|token)\s*[:=]\s*["']?([^\s'"]{8,})"""
    ),
    "jwt_like": (
        r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{8,2048}\."
        r"[A-Za-z0-9_-]{8,4096}\.[A-Za-z0-9_-]{8,2048}(?![A-Za-z0-9_-])"
    ),
}
COMPILED = {name: re.compile(pattern, re.ASCII) for name, pattern in EXPRESSIONS.items()}


def _secrets(bundle, query):
    total = scanned = size = skipped = capped = 0
    items = []
    for entry, dex in dex_entries(bundle):
        for index in range(dex.tables[0][0]):
            value = dex.string(index)
            scanned += 1
            size += len(value.encode("utf-8", "replace"))
            if scanned > 2_000_000 or size > query["max_scan_bytes"]:
                return {
                    "status": "error",
                    "code": "inventory_or_scan_error",
                    "diagnostic": "secret_scan_limit",
                }
            if len(value.encode("utf-16-le", "surrogatepass")) > 131072:
                skipped += 1
                continue
            for name, pattern in COMPILED.items():
                if query["pattern"] not in {"all", name}:
                    continue
                for count, match in enumerate(pattern.finditer(value)):
                    if count >= 20:
                        capped += 1
                        break
                    group = 1 if name == "credential_assignment" else 0
                    token = match.group(group)
                    if query["offset"] <= total < query["offset"] + query["limit"]:
                        row = {
                            "pattern": name,
                            "dex_entry": entry,
                            "string_index": index,
                            "utf16_offset": len(
                                value[: match.start(group)].encode("utf-16-le", "surrogatepass")
                            )
                            // 2,
                            "length_utf16": len(token.encode("utf-16-le", "surrogatepass")) // 2,
                            "candidate_sha256": hashlib.sha256(
                                token.encode("utf-8", "replace")
                            ).hexdigest(),
                            "redacted": "[REDACTED]",
                            "confidence": "candidate",
                        }
                        if query.get("include_values"):
                            row["value"] = token
                        items.append(row)
                    total += 1
    return {
        "status": "partial" if skipped or capped else "ok",
        "items": items,
        "total": total,
        "scanned_strings": scanned,
        "scanned_utf8_bytes": size,
        "skipped_oversize_strings": skipped,
        "capped_pattern_string_pairs": capped,
        "coverage_complete": not (skipped or capped),
        "scope": "dex_string_pool_fixed_patterns_only",
        "values_included": query.get("include_values", False),
        "credential_validity": "not_checked",
        "instruction_use_sites": "not_resolved",
        "pattern_version": 2,
    }
