"""Explicit opt-in CLI adapter; never treats Rust text search as exact xrefs."""

from .runner import DroidAscError, DroidAscRunner

TESTED_COMMIT = "236dd096669c99eb30f6e1af0b24e668eff55dd5"
LIMITATION = (
    "rust_ASC CLI may suppress per-DEX scan errors. Coverage is not verified; "
    "empty results do not prove absence of references. Use exact DEX operations for validation."
)


class RustAscRunner(DroidAscRunner):
    def _command(self, args, module_name):
        if module_name is not None:
            return super()._command(args, module_name)
        executable = self.settings.rust_asc_executable
        if executable is None or not executable.is_file():
            raise DroidAscError("Configure DROIDASC_MCP_RUST_ASC with an existing rust_ASC binary")
        if args[0] not in {"getmanifest", "listclass", "getclass", "findrefs"}:
            raise ValueError("Operation is not supported by the rust_ASC adapter")
        translated = list(args)
        # Only rewrite the known option position, never a user-supplied search value.
        if len(translated) > 2 and translated[1] == "--threads":
            translated[1] = "--thread"
        return super()._command([str(executable), *translated], "droidasc_mcp.native_worker")

    def find_refs(self, apk, **query):
        if query["kind"] in {"extends", "impl"}:
            raise ValueError("rust_ASC does not support hierarchy queries; use backend=droidasc")
        if query["kind"] == "type" and query.get("value"):
            query["value"] = query["value"].replace(".", "/")
        result = super().find_refs(apk, **query)
        result.update(coverage="not_verified", instruction_scan_complete=False)
        result["warning"] += " " + LIMITATION
        return result
