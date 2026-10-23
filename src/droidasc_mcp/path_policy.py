"""Shared path checks without importing the host configuration framework."""

from pathlib import Path


class ApkPathError(ValueError):
    """Raised when an input path is outside the configured policy."""


class PathPolicy:
    def validate_entry_input(self, value: str) -> Path:
        if Path(value).expanduser().resolve().suffix.lower() == ".dex":
            return self.validate_dex_paths([value])[0]
        return self.validate_artifact(value)

    def validate_apk(self, value: str) -> Path:
        return self.validate_artifact(value, extensions={".apk"})

    def validate_artifact(self, value: str, *, extensions=None) -> Path:
        path = Path(value).expanduser().resolve()
        extensions = extensions or {".apk", ".jar", ".aar", ".aab", ".apks", ".xapk", ".zip"}
        if path.suffix.lower() not in extensions:
            raise ApkPathError("Only " + ", ".join(sorted(extensions)) + " files are accepted")
        if not path.is_file():
            raise ApkPathError(f"APK file does not exist: {path}")
        if not any(path.is_relative_to(root) for root in self.allowed_roots):
            roots = ", ".join(str(root) for root in self.allowed_roots)
            raise ApkPathError(f"APK path is outside allowed roots: {roots}")
        size = path.stat().st_size
        if size > self.max_apk_bytes:
            raise ApkPathError(f"APK exceeds configured size limit: {size} bytes")
        return path

    def validate_dex_paths(self, values: list[str]) -> list[Path]:
        if not 1 <= len(values) <= 64:
            raise ApkPathError("Provide between 1 and 64 DEX paths")
        paths = []
        total = 0
        for value in values:
            path = Path(value).expanduser().resolve()
            if path.suffix.lower() != ".dex":
                raise ApkPathError("Only .dex files are accepted for DEX analysis")
            if not path.is_file():
                raise ApkPathError(f"DEX file does not exist: {path}")
            if not any(path.is_relative_to(root) for root in self.allowed_roots):
                raise ApkPathError(f"DEX path is outside allowed roots: {path}")
            if path in paths:
                raise ApkPathError(f"Repeated DEX path: {path}")
            total += path.stat().st_size
            if total > self.max_apk_bytes:
                raise ApkPathError("Combined DEX size exceeds configured size limit")
            paths.append(path)
        return paths
