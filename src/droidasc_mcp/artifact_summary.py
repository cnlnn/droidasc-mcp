"""Compact container triage from the inventory's checked archive handle."""

from .archive_errors import ArchiveError
from .archive_worker import MAX_XML_BYTES, _read, xml_document
from .manifest import header

MAX_SUMMARY_ABIS = 100


def summarize(archive, entries, kind, module, remaining_bytes):
    prefix = f"{module}/" if kind == "aab" else ""
    libraries = [
        name[len(prefix) :].split("/")
        for name, info in entries.items()
        if name.startswith(prefix + "lib/") and name.endswith(".so") and not info.is_dir()
    ]
    libraries = [parts for parts in libraries if len(parts) == 3]
    abis = sorted({parts[1] for parts in libraries})
    entry = prefix + "manifest/AndroidManifest.xml" if kind == "aab" else "AndroidManifest.xml"
    manifest = {"entry": entry}
    info = entries.get(entry)
    if info is None:
        manifest.update(status="not_applicable", code="manifest_not_found")
    else:
        try:
            if info.file_size > MAX_XML_BYTES:
                raise ArchiveError("xml_limit", "Manifest exceeds the 4 MiB XML byte budget")
            if info.file_size > remaining_bytes:
                raise ArchiveError("container_limit", "Manifest exceeds remaining expansion budget")
            data, complete = _read(archive, info, min(MAX_XML_BYTES, remaining_bytes))
            if not complete:
                raise ArchiveError("invalid_archive", "Manifest entry is incomplete")
            root, xml_format, warnings = xml_document(data)
            manifest.update(
                status="ok",
                xml_format=xml_format,
                decoding_warnings=warnings,
                **header(root),
            )
        except ArchiveError as exc:
            manifest.update(status="error", code=exc.code, message=str(exc))
            if kind == "aab" and exc.code == "invalid_xml":
                manifest["message"] += "; AAB protobuf XML is not decoded"
    return {
        "entry_count": len(entries),
        "native_scope": "selected_module" if kind == "aab" else "archive",
        "native_library_count": len(libraries),
        "native_abis": abis[:MAX_SUMMARY_ABIS],
        "native_abi_count": len(abis),
        "native_abis_truncated": len(abis) > MAX_SUMMARY_ABIS,
        "manifest": manifest,
    }
