"""APK metadata worker; binary parsing stays outside the MCP host process."""

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path


def main():
    apk = Path(sys.argv[1])
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
    result = {
        "apk_path": str(apk),
        "size_bytes": apk.stat().st_size,
        "dex_entries": sorted(
            name for name in names if re.fullmatch(r"classes(?:\d+)?\.dex", name)
        ),
        "has_manifest": "AndroidManifest.xml" in names,
    }
    if sys.argv[2] == "sha256":
        digest = hashlib.sha256()
        with apk.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        result["sha256"] = digest.hexdigest()
    print(json.dumps(result))


if __name__ == "__main__":
    main()
