"""Install the pinned optional acceptance backend; verify upstream release SHA256."""

import hashlib
import os
import tempfile
import urllib.request
import zipfile
from pathlib import Path

URL = "https://github.com/skylot/jadx/releases/download/v1.5.5/jadx-1.5.5.zip"
SHA256 = "38a5766d3c8170c41566b4b13ea0ede2430e3008421af4927235c2880234d51a"


def main():
    home = Path("artifacts/jadx-1.5.5").resolve()
    home.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "jadx.zip"
        with urllib.request.urlopen(URL, timeout=120) as source, archive.open("wb") as target:
            digest = hashlib.sha256()
            while block := source.read(1024 * 1024):
                target.write(block)
                digest.update(block)
        if digest.hexdigest() != SHA256:
            raise RuntimeError("JADX release digest mismatch")
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(home)
    if os.getenv("GITHUB_ENV"):
        with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as output:
            output.write(f"DROIDASC_MCP_JADX_HOME={home}\n")
    print(f"Verified JADX 1.5.5: {home}")


if __name__ == "__main__":
    main()
