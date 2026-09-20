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

Python 3.10 or newer is required. CI checks Linux and native Windows runners on Python 3.10-3.13, including
all six tools over stdio/HTTP against a source-built [acceptance APK](tests/fixtures/android/README.md)
and package installation. macOS remains unverified.

Install the version-pinned GitHub release on Linux:

```bash
python -m venv .venv
.venv/bin/python -m pip install https://github.com/cnlnn/droidasc-mcp/releases/download/v0.1.2/droidasc_mcp-0.1.2-py3-none-any.whl
```

Windows (PowerShell):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install https://github.com/cnlnn/droidasc-mcp/releases/download/v0.1.2/droidasc_mcp-0.1.2-py3-none-any.whl
```

Windows uses `.venv\Scripts\droidasc-mcp.exe` for the server command. For development,
clone this repository and run `uv sync --locked --extra dev` instead.

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

Results include `total`, `offset`, `limit`, `truncated`, and `next_offset`. Use `next_offset` for the
next request (`null` means done): the response budget can shorten a page. A single line
that exceeds the budget produces an explicit error rather than silent truncation.

Reference fields are best-effort parsing of ASC CLI text. Embedded newlines can split records;
`total` counts output lines, not semantic references. Reference lines are sorted before pagination.
Snapshots are decoded and sorted once, then cached for 60 seconds (up to 8 entries). The cache
budget accounts for Python strings and tuple pointers, not just original output bytes. Identical
concurrent queries share a single computation; unrelated queries and cache hits do not wait on
a global computation lock. Snapshots are
keyed by query and file identity/size/timestamps. Cache misses rerun ASC; this is not an immutable
content-addressed evidence store. Do not modify APK files between pages.

## Configuration

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `DROIDASC_MCP_ALLOWED_ROOTS` | current directory | Allowed roots, separated by `os.pathsep` (`:` on Unix, `;` on Windows) |
| `DROIDASC_MCP_TIMEOUT_SECONDS` | `180` | Per-operation timeout |
| `DROIDASC_MCP_MAX_APK_BYTES` | `2147483648` | Maximum accepted APK size |
| `DROIDASC_MCP_MAX_OUTPUT_BYTES` | `67108864` | Captured stdout limit and aggregate decoded snapshot budget |
| `DROIDASC_MCP_MAX_PAGE_SIZE` | `1000` | Maximum lines returned by one call |
| `DROIDASC_MCP_MAX_PARALLEL` | `2` | Maximum concurrent ASC subprocesses |

## Design

- Uses the public `droidasc` CLI module entry point; it does not import ASC private internals.
- Never invokes a shell and does not expose a generic command tool.
- Drains stdout and stderr concurrently with hard capture caps; no bulk output files are created.
- Caps stderr at 64 KiB and budgets page content conservatively within 256 KiB.
- Runs ZIP inspection and hashing in a supervised worker under the same concurrency budget.
- On POSIX, kills the operation's process group on completion or failure, even if its leader exited.
- On Windows, assigns the worker to a kill-on-close Job Object before starting ASC. Cleanup
  includes descendants even after the worker exits; Job setup failure prevents analysis from starting.
- Bounds queue waits and process waits. Client cancellation does not yet immediately stop sync tools.
- Resolves symlinks before checking the allowed-root policy.

ASC and its dependencies still parse untrusted binary input. Use a container or disposable VM for
hostile APKs. This adapter is a process boundary, not a malware sandbox.

Native Windows CI checks live-parent and orphan cleanup, including grandchildren, successful
completion, output overflow, reader termination, and repeated-operation handle counts.
There is no worker memory limit; use OS/container resource limits for hostile samples.
Capture buffers, snapshots being built, and active pages can coexist with the cache; this budget
is not a hard total-RSS cap. Dense outputs may hit the decoded-memory budget before the wire cap.

## Development

See [local acceptance checks](docs/VALIDATION.md) for real-process tests, optional APK transport
checks, measured outcomes, and the remaining verification limits.

```bash
uv sync --locked --extra dev
uv run ruff check .
uv run pytest --cov --cov-report=term-missing
uv build
# Python 3.12+; use fresh dist outputs matching the current version:
uv run python scripts/verify_dist.py dist/droidasc_mcp-0.1.2.tar.gz dist/droidasc_mcp-0.1.2-py3-none-any.whl
```

## License

Apache License 2.0. Droid ASC is a separate upstream project and retains its own copyright and
license.
