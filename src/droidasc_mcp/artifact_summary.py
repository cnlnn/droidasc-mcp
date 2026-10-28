"""Compact container triage from the inventory's checked archive handle."""

from .archive_errors import ArchiveError
from .archive_worker import MAX_XML_BYTES, _read, xml_document
from .manifest import header

MAX_SUMMARY_ABIS = 100


def manifest_header(archive, entries, entry, remaining_bytes, *, module=None):
    manifest = {"entry": entry}
    if module is not None:
        manifest["module"] = module
    info = entries.get(entry)
    consumed = 0
    if info is None:
        manifest.update(status="not_applicable", code="manifest_not_found")
    else:
        try:
            if info.file_size > MAX_XML_BYTES:
                raise ArchiveError("xml_limit", "Manifest exceeds the 4 MiB XML byte budget")
            if info.file_size > remaining_bytes:
                raise ArchiveError("container_limit", "Manifest exceeds remaining expansion budget")
            consumed = info.file_size
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
            if module is not None and exc.code == "invalid_xml":
                manifest["message"] += "; AAB protobuf XML is not decoded"
    return manifest, consumed


def summarize(archive, entries, kind, modules, remaining_bytes):
    prefixes = [f"{module}/" for module in modules] if kind == "aab" else [""]
    selected = set(modules)
    scoped_entries = (
        (
            (name.partition("/")[2], info)
            for name, info in entries.items()
            if name.partition("/")[0] in selected
        )
        if kind == "aab"
        else entries.items()
    )
    libraries = [
        name.split("/")
        for name, info in scoped_entries
        if name.startswith("lib/") and name.endswith(".so") and not info.is_dir()
    ]
    libraries = [parts for parts in libraries if len(parts) == 3]
    abis = sorted({parts[1] for parts in libraries})
    manifests = []
    for prefix in prefixes:
        module = prefix[:-1] if kind == "aab" else None
        entry = prefix + "manifest/AndroidManifest.xml" if kind == "aab" else "AndroidManifest.xml"
        manifest, consumed = manifest_header(
            archive, entries, entry, remaining_bytes, module=module
        )
        remaining_bytes -= consumed
        manifests.append(manifest)
    result = {
        "entry_count": len(entries),
        "native_scope": ("selected_module" if len(modules) == 1 else "selected_modules")
        if kind == "aab"
        else "archive",
        "native_library_count": len(libraries),
        "native_abis": abis[:MAX_SUMMARY_ABIS],
        "native_abi_count": len(abis),
        "native_abis_truncated": len(abis) > MAX_SUMMARY_ABIS,
    }
    if kind != "aab" or len(modules) == 1:
        result["manifest"] = manifests[0]
    else:
        result["manifests"] = manifests
    return result
