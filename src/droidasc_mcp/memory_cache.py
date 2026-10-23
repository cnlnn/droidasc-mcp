"""Small serialized page cache for pinned immutable sessions in the MCP host."""

import json
import shutil
import threading
from collections import OrderedDict
from importlib.metadata import version
from pathlib import Path

from .reference_page import OPERATIONS, reference_page

MAX_BYTES = 4 * 1024**2
MAX_PAGE_BYTES = 256 * 1024
MAX_ENTRIES = 32


def signature(settings, root):
    """Track local implementation, engine and index replacement before reusing a page."""
    home = settings.jadx_home
    java = shutil.which(settings.java_executable or "java")
    jars = sorted((home / "lib").glob("*.jar")) if home else []
    source = Path(__file__).parent
    paths = [
        *sorted(source.glob("*.py")),
        *sorted(source.glob("*.java")),
        *sorted(source.glob("_dexscan.*")),
        *jars,
    ]
    if java:
        paths.append(Path(java))
    for name in ("analysis.apk", "prepared.json", "owners.sqlite", "xrefs.sqlite", "calls.sqlite"):
        index = root / name
        if index.exists():
            paths.append(index)
    try:
        identities = []
        for path in paths:
            stat = path.stat()
            identities.append(
                (
                    str(path),
                    stat.st_dev,
                    stat.st_ino,
                    stat.st_size,
                    stat.st_mtime_ns,
                    stat.st_ctime_ns,
                )
            )
        return (version("droidasc"), settings, tuple(identities))
    except OSError:
        return None


class PageCache:
    def __init__(self):
        self.identity = None
        self.pages = OrderedDict()
        self.used = 0
        self.lock = threading.RLock()

    def execute(self, settings, root, query, execute):
        with self.lock:
            cached, identity, key = self._get(settings, root, query)
        if cached is not None:
            return cached
        result = execute()
        with self.lock:
            return self._put(settings, root, identity, key, result)

    def _get(self, settings, root, query):
        identity = signature(settings, root)
        if identity != self.identity:
            self.pages.clear()
            self.used = 0
            self.identity = identity
        key = json.dumps(query, sort_keys=True, separators=(",", ":"))
        if identity is not None and key in self.pages:
            encoded = self.pages.pop(key)
            self.pages[key] = encoded
            result = json.loads(encoded)
            result["query_cache"] = {"hit": True, "scope": "exact_query_page"}
            if query.get("operation") in OPERATIONS:
                result = reference_page(result, settings.max_output_bytes)
            return result, identity, key
        return None, identity, key

    def _put(self, settings, root, identity, key, result):
        # A first index build has one-shot 'reused=false' provenance, not a reusable page.
        if (
            identity is None
            or result.get("status") != "ok"
            or result.get("index", {}).get("reused") is False
            or identity != signature(settings, root)
        ):
            return result
        encoded = json.dumps(result, separators=(",", ":")).encode()
        if len(encoded) <= min(MAX_PAGE_BYTES, MAX_BYTES, settings.max_output_bytes):
            old = self.pages.pop(key, None)
            if old is not None:
                self.used -= len(old)
            while self.pages and (
                self.used + len(encoded) > MAX_BYTES or len(self.pages) >= MAX_ENTRIES
            ):
                _, old = self.pages.popitem(last=False)
                self.used -= len(old)
            self.pages[key] = encoded
            self.used += len(encoded)
        return result
