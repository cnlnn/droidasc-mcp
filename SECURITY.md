# Security Policy

## Reporting

Please report vulnerabilities through GitHub private vulnerability reporting. Do not open a public
issue for path traversal, command execution, denial-of-service, or sensitive APK disclosure bugs.

## Runtime boundary

`droidasc-mcp` analyzes untrusted APK files by launching Droid ASC in a separate process group. It
does not claim to be a complete malware sandbox. For hostile samples, run the MCP server inside a
container or disposable VM without network access.

The server only accepts APKs under `DROIDASC_MCP_ALLOWED_ROOTS`. The default is the server's current
working directory. Resolved paths are checked after symlink resolution.

