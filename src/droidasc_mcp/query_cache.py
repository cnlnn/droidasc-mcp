"""Bounded page-result reuse for immutable DEX sessions, without resident workers."""

import hashlib
import json
import os
import time
from pathlib import Path

from .xref_index import backend_identity

MAX_BYTES = 4 * 1024 * 1024
MAX_ENTRIES = 32
MAX_PAGE_BYTES = 256 * 1024


def clear_cache(root):
    for path in (root / "query-cache").glob("*.json"):
        path.unlink()


def _touch(path):
    # Advance by at least 1 ms so LRU order survives Windows timestamp rounding.
    stamp = max(
        time.time_ns(), max(p.stat().st_mtime_ns for p in path.parent.glob("*.json")) + 1_000_000
    )
    os.utime(path, ns=(stamp, stamp))


def cached_query(settings, bundle, common, query, workspace, execute):
    root = bundle.parent / "query-cache"
    index = bundle.parent / "xrefs.sqlite"
    remaining = settings.max_xref_index_bytes - (index.stat().st_size if index.exists() else 0)
    budget = max(0, min(MAX_BYTES, remaining))
    identity = backend_identity(
        settings,
        (
            "MethodBridge.java",
            "DiscoveryBridge.java",
            "StructureBridge.java",
            "method_backend.py",
            "query_cache.py",
        ),
    )
    if not identity or not budget:
        return execute()
    key = hashlib.sha256(
        json.dumps(
            [common["input_id"], identity, settings.max_page_size, query], sort_keys=True
        ).encode()
    ).hexdigest()
    path = root / (key + ".json")
    page_budget = min(budget, MAX_PAGE_BYTES, settings.max_output_bytes)
    if path.is_file():
        try:
            if path.stat().st_size <= page_budget:
                result = json.loads(path.read_bytes())
                if isinstance(result, dict) and result.get("status") == "ok":
                    _touch(path)
                    return {**result, "query_cache": {"hit": True, "scope": "exact_query_page"}}
        except (ValueError, UnicodeError):
            pass
        path.unlink()
    result = execute()
    if result.get("status") != "ok":
        return result
    encoded = json.dumps(result, separators=(",", ":")).encode()
    stored = False
    if len(encoded) <= page_budget:
        root.mkdir(exist_ok=True)
        pages = sorted(root.glob("*.json"), key=lambda p: (p.stat().st_mtime_ns, p.name))
        used = sum(p.stat().st_size for p in pages)
        while pages and (used + len(encoded) > budget or len(pages) >= MAX_ENTRIES):
            old = pages.pop(0)
            used -= old.stat().st_size
            old.unlink()
        temporary = Path(workspace) / "query-cache.partial.json"
        temporary.write_bytes(encoded)
        os.replace(temporary, path)
        _touch(path)
        stored = True
    return {
        **result,
        "query_cache": {"hit": False, "stored": stored, "scope": "exact_query_page"},
    }
