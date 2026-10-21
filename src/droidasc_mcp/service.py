"""Structured application service exposed by MCP tools."""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, version

from . import __version__
from .config import Settings
from .runner import DroidAscRunner, ReferenceKind
from .sessions import DexSessions


class DroidAscService:
    def __init__(self, settings: Settings, runner: DroidAscRunner | None = None) -> None:
        self.settings = settings
        self.runner = runner or DroidAscRunner(settings)
        self.sessions = DexSessions(settings, self.runner)

    def close(self):
        self.sessions.shutdown()

    def open_dex_session(self, dex_paths):
        return self.sessions.open(self.settings.validate_dex_paths(dex_paths))

    def query_dex_session(self, session_id, **query):
        return self.sessions.query(session_id, _normalize_dex_query(query))

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
            "max_worker_memory_bytes": self.settings.max_worker_memory_bytes,
            "max_page_size": self.settings.max_page_size,
            "method_backend": {
                "configured": self.settings.jadx_home is not None,
                "required_jadx_version": "1.5.5",
                "required_java": "JDK 17+",
                "operations": [
                    "list_methods",
                    "get_method_source",
                    "find_method_refs",
                    "get_method_calls",
                ],
                "identity": "full_dex_method_descriptor",
                "explicit_smali_backend": "droidasc",
            },
            "dex_sessions": {
                "max_count": self.settings.max_dex_sessions,
                "idle_ttl_seconds": self.settings.dex_session_ttl_seconds,
                "max_disk_bytes": self.settings.max_dex_session_bytes,
                "reuse": "validated_dex_bundle",
            },
        }

    def apk_info(self, apk_path: str, *, include_sha256: bool = True) -> dict[str, object]:
        apk = self.settings.validate_apk(apk_path)
        return self.runner.apk_info(apk, include_sha256)

    def analyze_dex(self, dex_paths: list[str], **query) -> dict[str, object]:
        paths = self.settings.validate_dex_paths(dex_paths)
        return self.runner.analyze_dex(paths, _normalize_dex_query(query))

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
        if kind in {"method", "field"} and class_name is not None and not fuzzy_class:
            class_name = _normalize_class_name(class_name)
        value = _normalize_reference_value(kind, value)
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


def _normalize_dex_query(query):
    if query.get("operation") in {"get_method_source", "find_method_refs", "get_method_calls"}:
        descriptor = query.get("method_descriptor")
        owner_type = r"L[^;\[\]]+;"
        value_type = rf"\[*(?:[ZBCSIJFD]|{owner_type})"
        pattern = rf"({owner_type})->[^()/;\[\]]+\((?:{value_type})*\)(?:V|{value_type})"
        if not descriptor or not re.fullmatch(pattern, descriptor):
            raise ValueError(
                "method_descriptor requires the full DEX class->name(args)return identity"
            )
        owner = descriptor.split("->", 1)[0]
        if query.get("class_name") and _normalize_class_name(query["class_name"]) != owner:
            raise ValueError("class_name and method_descriptor refer to different classes")
        query["class_name"] = owner
    if query.get("source_format", "auto") not in {"auto", "java", "smali"}:
        raise ValueError("source_format must be auto, java, or smali")
    if query.get("debug_info") and (
        query.get("operation") != "get_method_source" or query.get("source_format") != "smali"
    ):
        raise ValueError("debug_info requires get_method_source with source_format=smali")
    if query.get("operation") == "find_refs":
        query["value"] = _normalize_reference_value(query.get("kind"), query.get("value"))
    if query.get("class_name") and (
        query.get("operation") in {"get_class_source", "list_methods", "get_method_source"}
        or not query.get("fuzzy_class", False)
    ):
        query["class_name"] = _normalize_class_name(query["class_name"])
    return query


def _normalize_reference_value(kind: str | None, value: str | None) -> str | None:
    if kind in {"extends", "impl"} and value is not None and value != "--gui":
        return _normalize_class_name(value)
    return value


def _normalize_class_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("class_name cannot be empty")
    if value.startswith("L") and value.endswith(";"):
        return value
    value = value.replace(".", "/")
    return f"L{value};"
