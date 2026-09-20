# droidasc-mcp

A small, defensive MCP server for [Droid ASC](https://github.com/MG1937/ASC), the fast
on-demand Android APK decompiler.

`droidasc-mcp` exposes ASC's public CLI as six typed, read-only MCP tools. Every analysis runs in an
isolated subprocess group, accepts only APK paths under configured roots, and returns paginated
structured data instead of unbounded terminal output.

> Community project. Not affiliated with or endorsed by the Droid ASC maintainers.

[中文文档](README.zh-CN.md)

## Tools

| Tool | Purpose |
| --- | --- |
| `asc_ping` | Show adapter/engine versions and effective runtime limits |
| `asc_apk_info` | Return size, SHA-256, manifest presence, and DEX entries |
| `asc_get_manifest` | Decode `AndroidManifest.xml` with line pagination |
| `asc_list_classes` | List class descriptors with prefix filtering and pagination |
| `asc_get_class_source` | Decompile one class with line pagination |
| `asc_find_refs` | Find string, type, method, or field references across DEX files |

## Install

Python 3.10 or newer is required.

```bash
git clone https://github.com/cnlnn/droidasc-mcp.git
cd droidasc-mcp
python -m venv .venv
.venv/bin/pip install -e .
```

Windows uses `.venv\Scripts\python.exe` and `.venv\Scripts\droidasc-mcp.exe`.

## Connect

The default transport is stdio. Limit the server to directories that contain APKs:

```bash
export DROIDASC_MCP_ALLOWED_ROOTS=/absolute/path/to/apks
.venv/bin/droidasc-mcp
```

### Codex

```bash
codex mcp add droidasc \
  --env DROIDASC_MCP_ALLOWED_ROOTS=/absolute/path/to/apks \
  -- /absolute/path/to/droidasc-mcp/.venv/bin/droidasc-mcp
```

### Claude Desktop and compatible hosts

```json
{
  "mcpServers": {
    "droidasc": {
      "command": "/absolute/path/to/droidasc-mcp/.venv/bin/droidasc-mcp",
      "env": {
        "DROIDASC_MCP_ALLOWED_ROOTS": "/absolute/path/to/apks"
      }
    }
  }
}
```

### Streamable HTTP

```bash
DROIDASC_MCP_ALLOWED_ROOTS=/absolute/path/to/apks \
  .venv/bin/droidasc-mcp --transport streamable-http --host 127.0.0.1 --port 8000
```

The endpoint is `http://127.0.0.1:8000/mcp`. Keep it on loopback unless you add an authenticated,
TLS-terminating reverse proxy.

## Examples

Ask an MCP host to call:

```text
asc_apk_info(apk_path="/samples/app.apk")
asc_list_classes(apk_path="/samples/app.apk", prefix="com.example", limit=100)
asc_find_refs(apk_path="/samples/app.apk", kind="string", value="Authorization")
asc_get_class_source(apk_path="/samples/app.apk", class_name="com.example.MainActivity")
```

Results include `total`, `offset`, `limit`, and `truncated`. Request the next page by increasing
`offset`.

## Configuration

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `DROIDASC_MCP_ALLOWED_ROOTS` | current directory | Allowed roots, separated by `os.pathsep` (`:` on Unix, `;` on Windows) |
| `DROIDASC_MCP_TIMEOUT_SECONDS` | `180` | Per-operation timeout |
| `DROIDASC_MCP_MAX_APK_BYTES` | `2147483648` | Maximum accepted APK size |
| `DROIDASC_MCP_MAX_OUTPUT_BYTES` | `67108864` | Maximum temporary ASC output size |
| `DROIDASC_MCP_MAX_PAGE_SIZE` | `1000` | Maximum lines returned by one call |
| `DROIDASC_MCP_MAX_PARALLEL` | `2` | Maximum concurrent ASC subprocesses |

## Design

- Uses `python -m droidasc`; it does not import ASC private internals.
- Never invokes a shell and does not expose a generic command tool.
- Redirects bulk ASC output to a private temporary file, then returns one bounded page.
- Starts each operation in a process group and terminates the group on timeout.
- Resolves symlinks before checking the allowed-root policy.

ASC and its dependencies still parse untrusted binary input. Use a container or disposable VM for
hostile APKs. This adapter is a process boundary, not a malware sandbox.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run pytest --cov --cov-report=term-missing
```

## License

Apache License 2.0. Droid ASC is a separate upstream project and retains its own copyright and
license.

