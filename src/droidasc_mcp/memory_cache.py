"""Small serialized page cache for pinned immutable sessions in the MCP host."""

import json
import shutil
from collections import OrderedDict
from importlib.metadata import version
from pathlib import Path

MAX_BYTES = 4 * 1024**2
MAX_PAGE_BYTES = 256 * 1024
MAX_ENTRIES = 32


def signature(settings, root):
    """Track local implementation, engine and index replacement before reusing a page."""
    home = settings.jadx_home
    java = shutil.which(settings.java_executable or "java")
    if not home or not java:
        return None
    jars = sorted((home / "lib").glob("*.jar"))
    if not jars:
        return None
    source = Path(__file__).parent
    paths = [*sorted(source.glob("*.py")), *sorted(source.glob("*.java")), *jars, Path(java)]
    index = root / "xrefs.sqlite"
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

    def execute(self, settings, root, query, execute):
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
            return result
        result = execute()
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
            while self.pages and (
                self.used + len(encoded) > MAX_BYTES or len(self.pages) >= MAX_ENTRIES
            ):
                _, old = self.pages.popitem(last=False)
                self.used -= len(old)
            self.pages[key] = encoded
            self.used += len(encoded)
        return result
