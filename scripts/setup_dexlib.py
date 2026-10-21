"""Install standalone dexlib2 for DEX 041 import, never a JADX distribution."""

import hashlib
import os
import tempfile
import urllib.request
from pathlib import Path

ARTIFACTS = (
    (
        "https://dl.google.com/dl/android/maven2/com/android/tools/smali/smali-dexlib2/3.0.9/"
        "smali-dexlib2-3.0.9.jar",
        "8b547506f62f91d74b70f4beb4989b99e1ff61fc50b2525e9796ca35f0a351dc",
    ),
    (
        "https://repo.maven.apache.org/maven2/com/google/guava/guava/33.4.8-android/"
        "guava-33.4.8-android.jar",
        "a1f8a4bafe5a77232d333356843e194599b30837574a7f4be1063daaaaab102c",
    ),
    (
        "https://repo.maven.apache.org/maven2/com/google/guava/failureaccess/1.0.3/"
        "failureaccess-1.0.3.jar",
        "cbfc3906b19b8f55dd7cfd6dfe0aa4532e834250d7f080bd8d211a3e246b59cb",
    ),
    (
        "https://repo.maven.apache.org/maven2/com/google/code/findbugs/jsr305/3.0.2/"
        "jsr305-3.0.2.jar",
        "766ad2a0783f2687962c8ad74ceecc38a28b9f72a2d085ee438b7813e928d0c7",
    ),
)


def main():
    home = Path("artifacts/dexlib-3.0.9").resolve()
    library = home / "lib"
    library.mkdir(parents=True, exist_ok=True)
    for url, expected in ARTIFACTS:
        target = library / url.rsplit("/", 1)[1]
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
            continue
        with tempfile.TemporaryDirectory(dir=home) as directory:
            partial = Path(directory) / "download.jar"
            with urllib.request.urlopen(url, timeout=120) as source, partial.open("wb") as output:
                digest, size = hashlib.sha256(), 0
                while block := source.read(1024 * 1024):
                    size += len(block)
                    if size > 8 * 1024**2:
                        raise RuntimeError("Standalone dexlib2 artifact exceeds download limit")
                    digest.update(block)
                    output.write(block)
            if digest.hexdigest() != expected:
                raise RuntimeError("Standalone dexlib2 artifact SHA256 mismatch")
            partial.replace(target)
    if os.getenv("GITHUB_ENV"):
        with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as output:
            output.write(f"DROIDASC_MCP_DEXLIB_HOME={home}\n")
    print(f"Verified standalone dexlib2 3.0.9: {home}")


if __name__ == "__main__":
    main()
