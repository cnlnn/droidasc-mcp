"""Upstream artifact identity and inventory, backed by a supervised private snapshot."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
import sys
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path

from .archive_errors import ArchiveError
from .archive_worker import MAX_ENTRIES, _digest, _entries, _identity


@dataclass(frozen=True)
class AnalysisSession:
    analysis_id: str
    path: Path
    size_bytes: int
    modified_ns: int
    sha256: str
    entry_count: int
    dex_files: tuple[str, ...]
    artifact_type: str
    capabilities: tuple[str, ...]

    def handle(self):
        return {
            "status": "ok",
            "analysis_id": self.analysis_id,
            "name": self.path.name,
            "artifact_type": self.artifact_type,
            "capabilities": list(self.capabilities),
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "entry_count": self.entry_count,
            "dex_count": len(self.dex_files),
        }


def inspect_snapshot(path, source, before, digest, max_dex_bytes):
    # Adapted from upstream SessionRegistry.open; snapshot ownership lives in DexSessions.
    artifact_type = path.suffix.lower()[1:]
    capabilities = []
    if artifact_type == "dex":
        if before.st_size > max_dex_bytes:
            raise ArchiveError("input_limit", "DEX exceeds the configured size limit")
        with path.open("rb") as stream:
            if stream.read(4) != b"dex\n":
                raise ArchiveError("invalid_magic", "File is not a valid DEX")
        dex_files = (path.name,)
        capabilities.append("dex")
        entry_count = 1
    else:
        with zipfile.ZipFile(path) as archive:
            entries = _entries(archive)
            infos = tuple(entries.values())
            if len(infos) > MAX_ENTRIES:
                raise ArchiveError("entry_limit", "Artifact exceeds the configured entry limit")
            if sum(info.file_size for info in infos) > 4 * 1024**3:
                raise ArchiveError(
                    "container_limit", "Artifact exceeds the uncompressed-size limit"
                )
            for info in infos:
                if info.filename.lower().endswith(".dex") and info.file_size > max_dex_bytes:
                    raise ArchiveError(
                        "input_limit", "Artifact contains a DEX above the size limit"
                    )
            names = set(entries)
            dex_files = tuple(
                info.filename
                for info in infos
                if info.filename.lower().endswith(".dex") and not info.is_dir()
            )
            if artifact_type == "aar" and "classes.jar" in entries:
                from .containers import capabilities as container_capabilities

                _, _, nested, _, selected, _ = container_capabilities(
                    archive, entries, artifact_type, None, max_dex_bytes
                )
                try:
                    dex_files = tuple(selected)
                finally:
                    nested.close()
            if dex_files:
                capabilities.append("dex")
            if any(name.lower().endswith((".class", ".jar")) for name in names):
                capabilities.append("jvm-class-inventory")
            if "AndroidManifest.xml" in names or (
                artifact_type == "aab"
                and any(name.endswith("/manifest/AndroidManifest.xml") for name in names)
            ):
                capabilities.append("manifest")
            if artifact_type == "apk":
                capabilities.append("signing")
            capabilities.append("archive")
            entry_count = len(infos)
    return AnalysisSession(
        analysis_id=secrets.token_urlsafe(18),
        path=source,
        size_bytes=before.st_size,
        modified_ns=before.st_mtime_ns,
        sha256=digest,
        entry_count=entry_count,
        dex_files=dex_files,
        artifact_type=artifact_type,
        capabilities=tuple(capabilities),
    )


def snapshot(request):
    from .config import Settings

    settings = Settings(
        allowed_roots=tuple(Path(root) for root in request["allowed_roots"]),
        max_apk_bytes=request["max_input_bytes"],
    )
    source = settings.validate_entry_input(request["path"])
    target = Path(request["root"]) / "input" / source.name
    target.parent.mkdir()
    with source.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > request["reserved_input_bytes"]:
            raise ArchiveError("input_changed", "Artifact changed before snapshot")
        digest = hashlib.sha256()
        copied = 0
        with target.open("xb") as output:
            while block := stream.read(min(1024**2, before.st_size - copied + 1)):
                copied += len(block)
                if copied > before.st_size:
                    raise ArchiveError("input_changed", "Artifact grew during snapshot")
                digest.update(block)
                output.write(block)
        if copied != before.st_size or digest.hexdigest() != _digest(stream):
            raise ArchiveError("input_changed", "Artifact changed during snapshot")
        with source.open("rb") as current:
            if any(
                _identity(before) != _identity(os.fstat(handle.fileno()))
                for handle in (stream, current)
            ):
                raise ArchiveError("input_changed", "Artifact replaced during snapshot")
    session = inspect_snapshot(
        target, source, before, digest.hexdigest(), min(settings.max_apk_bytes, 1024**3)
    )
    return {"status": "ok", "session": {**asdict(session), "path": str(source)}}


def main():
    request = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    try:
        result = snapshot(request)
    except ArchiveError as exc:
        result = {"status": "error", "code": exc.code, "message": str(exc)}
    except (OSError, ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as exc:
        result = {"status": "error", "code": "invalid_artifact", "message": str(exc)}
    encoded = json.dumps(result)
    if len(encoded.encode()) > min(request["max_output_bytes"], 256 * 1024):
        encoded = json.dumps(
            {
                "status": "error",
                "code": "response_limit",
                "message": "Artifact inventory exceeds the metadata budget",
            }
        )
    print(encoded)


if __name__ == "__main__":
    main()
