# APK archive workflow (candidate, unreleased)

This slice adds `asc_list_apk_entries`, `asc_read_apk_entry` and
`asc_manifest_summary` on the candidate branch. It does not complete every item in
the [competitor workflow comparison](AIMARD_COMPARISON.md).

## Investigation path

1. Establish scope and identity with `asc_ping` and `asc_apk_info`.
2. Page the manifest summary; retain raw attributes, permission sources, decoder warnings
   and unresolved resource/default values alongside component names.
3. Locate resources/assets/native libraries by category or literal ZIP prefix.
4. Read selected entries. Distinguish complete, CRC-verified inputs from bounded raw prefixes,
   decoded XML from raw fallback, and output truncation from decoder warnings.
5. Match APK hashes, then use component class names, resource paths and observed strings as
   starting points for class/source/reference queries. Resource-table ID resolution and
   automatic resource-to-code joins are not implemented.

## Contract and limits

Every successful read/list/summary includes the input SHA-256 and size. The worker opens
one file, checks file identity before/after analysis and rehashes it before returning.
A detected modification discards the result as `input_changed`. There is no extraction.
No archive result cache is introduced.
Path binding is checked by reopening the path and comparing handle-based metadata;
it does not compare `stat(path)` timestamps directly against `fstat(fd)`. Windows
can expose creation/change time differently through those APIs, as reflected in
[CPython's Windows stat implementation](https://github.com/python/cpython/blob/3.12/Modules/posixmodule.c)
and [handle implementation](https://github.com/python/cpython/blob/3.12/Python/fileutils.c).

The archive worker uses the existing bounded subprocess, process-tree cancellation,
timeout, memory/output limits and shared concurrency semaphore. Temporary request storage
belongs to the parent. Archive-specific bounds are 100,000 entries, 128 KiB returned
content before encoding, 4 MiB complete XML input/decoded XML, 20,000 XML nodes and
256 KiB serialized response. Server page limits still apply. A response that does not fit
returns `response_limit`, rather than silently omitting declarations or list entries.

Inventory excludes directories and classifies manifest/resource/asset/native/dex/metadata/other.
Native ABI is inferred from the `lib/<abi>/<file>.so` path only. Duplicate names, traversal,
absolute/drive/backslash paths, NUL names and non-regular entries are rejected. Encrypted
entries can be inventoried but not read. CRC values in inventory remain unverified metadata;
complete entry reads validate CRC through `ZipExtFile`. Partial raw reads report otherwise.

Binary XML uses the directly declared `axml` dependency. Chunk bounds and balanced
start/end tag identifiers are checked before decoding, so an
unclosed or mismatched binary document is not silently repaired into a complete result.
The library's packing flag is heuristic: unknown newer Android attributes also trigger
it on ordinary source-built APKs. Both the
flag and warning/error logs are reflected in decoding warnings, not turned into a packing
or lossless-decoding claim. Invalid XML falls back to bounded raw content with a decoding
diagnostic; a manifest summary instead returns an error. Text XML disables DTD/entity
resolution and network access, and DTD-bearing documents are rejected.

## Permission semantics

Raw declarations and computed permission requirements remain separate. Ordinary components
inherit application permission when their own attribute is absent. An explicit empty value
clears the inherited permission. An activity alias without an explicit permission requires
none: it does not inherit its target/application permission. Target declaration ordering is
reported separately. Provider read/write attributes override its component/application
permission; path permissions and URI grants remain separate declarations, not flattened
into one access decision. Resource references and placeholders are marked unresolved.

These rules are checked against the Android references for
[activity aliases](https://developer.android.com/guide/topics/manifest/activity-alias-element),
[application permission](https://developer.android.com/guide/topics/manifest/application-element)
and [providers](https://developer.android.com/guide/topics/manifest/provider-element).
Absent exported defaults are left unresolved because platform/target SDK and intent-filter
conditions matter. Effective enabled values describe application/component declarations,
not dynamic PackageManager state, alias target state or runtime accessibility.

## Independent acceptance

`tests/test_archive.py` exercises categories, literal filters, pagination, permission
precedence/clearing, aliases, intent filters, provider rules, unresolved values, malformed XML,
DTD rejection, oversized XML, ZIP traversal/duplicates/special files, CRC failure, changed
input, response/entry bounds and cleanup after worker failure. It also tests the independent
`aapt2` output parser against application metadata that must not overwrite a component name.
Real stdio and HTTP tests exercise all three tools, argument bounds and compiled binary
Manifest decoding alongside the existing ASC raw manifest operation.
The focused archive/server selection passed 51 tests locally; full native/package gates
are separate from this narrow result.

The locally retained Taobao 10.62.0 APK was checked through a real stdio MCP server:

| Evidence | Result |
| --- | --- |
| Input SHA-256 | `2d8844a2cefecb8b99f5e8dc83e3eabba39391b02e2dc27c562d8ba3d0755348` |
| Full ZIP inventory | 6,219 files, exact names/sizes/compressed sizes/CRC metadata match |
| Categories | 5,350 resources; 563 assets; 118 native libraries; 12 DEX; 37 metadata; 138 other; 1 manifest |
| Full component pagination | 741 components, exact kind/name order matches official `aapt2 dump xmltree` |
| Component kinds | 492 activities, 176 services, 61 receivers, 11 providers, 1 alias |
| Compiled resource | `res/--_.xml`, `RelativeLayout`, all 12 element tags match `aapt2` |
| Decoder caveat | Packing/format and log warnings retained on both manifest and resource |
| Input preservation | SHA-256 unchanged after all operations |

Local machine-readable evidence: `artifacts/reverse-acceptance/taobao-archive-workflow.json`.
This checks inventory, component identity/order and one resource element tree, not all
resource attribute values, Android runtime access or every APK format. The APK is not
redistributed. Reproduce with:

```bash
uv run python scripts/verify_archive_workflow.py /path/to/app.apk \
  --aapt2 /path/to/android-sdk/build-tools/35.0.0/aapt2 \
  --output artifacts/validation/archive-workflow.json
```

Bounded multi-hop call exploration is implemented by `get_call_graph`. Signing metadata,
additional container formats and revision inventories are implemented in the same unreleased
batch, with coverage described in [REVERSE_WORKFLOW.md](REVERSE_WORKFLOW.md). Their combined
acceptance is recorded separately. Native decoding, signing verification, dynamic
instrumentation and resource-table resolution are not claimed by these tools.
