"""Structured application service exposed by MCP tools."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from . import __version__
from .config import Settings
from .runner import DroidAscRunner, ReferenceKind


class DroidAscService:
    def __init__(self, settings: Settings, runner: DroidAscRunner | None = None) -> None:
        self.settings = settings
        self.runner = runner or DroidAscRunner(settings)

    def ping(self) -> dict[str, object]:
        try:
            engine_version = version("droidasc")
        except PackageNotFoundError:
            engine_version = "not-installed"
        return {
            "status": "ok",
            "server": "droidasc-mcp",
            "server_version": __version__,
            "droidasc_version": engine_version,
            "allowed_roots": [str(path) for path in self.settings.allowed_roots],
            "timeout_seconds": self.settings.timeout_seconds,
            "max_page_size": self.settings.max_page_size,
        }

    def apk_info(self, apk_path: str, *, include_sha256: bool = True) -> dict[str, object]:
        apk = self.settings.validate_apk(apk_path)
        return self.runner.apk_info(apk, include_sha256)

    def get_manifest(self, apk_path: str, *, offset: int, limit: int) -> dict[str, object]:
        apk = self.settings.validate_apk(apk_path)
        page = self.runner.get_manifest(apk, offset=offset, limit=limit)
        result = page.as_dict()
        result.update({"apk_path": str(apk), "xml": "\n".join(page.items)})
        result.pop("items")
        return result

    def list_classes(
        self,
        apk_path: str,
        *,
        prefix: str | None,
        threads: int,
        offset: int,
        limit: int,
    ) -> dict[str, object]:
        apk = self.settings.validate_apk(apk_path)
        page = self.runner.list_classes(
            apk,
            prefix=prefix,
            threads=threads,
            offset=offset,
            limit=limit,
        )
        result = page.as_dict()
        result["apk_path"] = str(apk)
        return result

    def get_class_source(
        self,
        apk_path: str,
        *,
        class_name: str,
        threads: int,
        offset: int,
        limit: int,
    ) -> dict[str, object]:
        apk = self.settings.validate_apk(apk_path)
        descriptor = _normalize_class_name(class_name)
        page = self.runner.get_class_source(
            apk,
            class_name=descriptor,
            threads=threads,
            offset=offset,
            limit=limit,
        )
        result = page.as_dict()
        result.update(
            {
                "apk_path": str(apk),
                "class_name": descriptor,
                "source": "\n".join(page.items),
            }
        )
        result.pop("items")
        return result

    def find_refs(
        self,
        apk_path: str,
        *,
        kind: ReferenceKind,
        value: str | None,
        class_name: str | None,
        fuzzy_class: bool,
        threads: int,
        offset: int,
        limit: int,
    ) -> dict[str, object]:
        apk = self.settings.validate_apk(apk_path)
        result = self.runner.find_refs(
            apk,
            kind=kind,
            value=value,
            class_name=class_name,
            fuzzy_class=fuzzy_class,
            threads=threads,
            offset=offset,
            limit=limit,
        )
        result["apk_path"] = str(apk)
        result["kind"] = kind
        return result


def _normalize_class_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("class_name cannot be empty")
    if value.startswith("L") and value.endswith(";"):
        return value
    value = value.replace(".", "/")
    return f"L{value};"
