# Container and revision review

Current candidate feature boundaries. The combined Linux/Windows, real stdio/HTTP,
independent-tool and clean sdist/wheel results establish acceptance, not this document.

## Artifact routing

Call `asc_inspect_artifact(artifact_path=...)` before opening unfamiliar containers.
It hashes the original file and pages sorted capability entries. Capability flags are
separate from entry inventory: a `.class` filename is not verified JVM bytecode.

| Input | DEX analysis coverage | Other contents |
| --- | --- | --- |
| APK / JAR / ZIP | Any directly embedded `.dex` path, case-insensitive suffix | No recursive nested-archive extraction |
| JVM JAR | No DEX analysis without direct DEX entries | Class-entry inventory only |
| AAR | Direct outer DEX and DEX in `classes.jar`, including arbitrary paths | First-level JAR JVM entries inventory-only; no DEX from `libs/*.jar` |
| AAB | Direct DEX in one selected module's `dex/` directory | Defaults to `base`; inspect `modules`, select exact `module` |
| APKS / XAPK | Direct DEX entries only, no reconstruction or nested APK analysis | Nested APK-entry inventory only |

`asc_open_artifact_session` returns the normal session ID. Existing query and close
tools work unchanged. The session stores validated DEX only, not a reconstructed app:
`has_manifest=false` applies to that analysis bundle even when the original has a manifest.
Source rows retain `path`, `container_entry`, original DEX SHA-256 and normalized
`dex_entry`. Top-level `artifact_sha256` binds the original container; `input_id` binds
the selected ordered DEX content and engine, not all container resources.

`max_uncompressed_bytes` defaults to 128 MiB and covers expanded `classes.jar` plus
selected DEX bytes. Its maximum is also capped by the configured input-file byte limit.
Opening reserves seven times that budget for snapshots, normalization and bundles, plus
bounded metadata and an optional xref-index
allocation before starting the worker. Raising the budget can exhaust session capacity.
ZIP names, duplicates, special entries, CRC, input stability, DEX integrity and duplicate
class definitions are checked. Extraction uses generated filenames only, inside private
parent-owned temporary storage. Cancellation and failed imports release the reservation.

## Signing inventory

`asc_signing_inventory(apk_path=...)` reports container presence independently for v1,
v2, v3 and v3.1. It extracts X.509 metadata and SHA-256/SHA-1 fingerprints from v1
PKCS7 certificate bags and v2/v3 signer chains. SHA-1 is an identity compatibility field,
not an integrity recommendation. Certificate chains and their order are unverified.
v1 bag certificates are not mapped to PKCS7 SignerInfo identities.

The signing block and aggregate v1 container budget is 8 MiB each; signer containers cap
at 32 and each certificate chain/bag at 64. Malformed blocks yield diagnostics, with
unknown presence where the block cannot be parsed. v3.1 certificate extraction,
rotation lineage, v4 sidecars, content digests, signatures and certificate trust are
explicitly unsupported or unevaluated. Presence is not evidence of a valid signature;
even tampered APKs can retain the same certificate inventory. Independent `apksigner`
verification is the acceptance oracle for validity, not this metadata parser.
The independent acceptance script checks v1-only signatures for Android API 24-27;
it does not claim that a v1-only APK meets modern target-SDK signing requirements.
The parser accepts the optional empty fourth v2 signed-data field emitted by
[AOSP apksig](https://android.googlesource.com/platform/tools/apksig/+/refs/heads/main/src/main/java/com/android/apksig/internal/apk/v2/V2SchemeSigner.java),
without accepting arbitrary trailing bytes or treating that extension as v3 data.

Format references: [AOSP v2](https://source.android.com/docs/security/features/apksigning/v2),
[AOSP v3](https://source.android.com/docs/security/features/apksigning/v3).

## Revision identities

Open baseline and candidate sessions, then call
`asc_diff_dex_sessions(old_session_id=..., new_session_id=..., kind="all", change="all")`.
The native DEX reader scans declarations without decoding instructions
or building the expensive xref index. Both sessions remain pinned during the comparison.
Results include both input IDs, source hashes and container hashes where applicable.

`kind` selects class/method/field/all; `change` selects added/removed/all before pagination.
Rows are sorted by full descriptor. Counts cover the selected declaration kind before
the change filter. Methods include argument/return types and fields include their type.
The limit is 1M distinct identities and 64 MiB of cumulative UTF-8 declaration records
across both inputs. Limit failures return errors rather than incomplete successful diffs.
Identical inventories do not establish identical behavior, flags, annotations, initializers,
resources or native libraries. DEX relocation alone is not an added/removed declaration.

## Candidate strings

`asc_secret_candidates(session_id=..., pattern="all")` scans DEX string pools using fixed
AWS access-ID, GitHub classic-token, Google API-key, private-key-marker, credential-assignment
and JWT-like patterns. It returns pattern family, normalized DEX entry, string-pool index,
UTF-16 match offset/length, SHA-256 of the candidate and `[REDACTED]`. Raw matched values
are returned only with explicit `include_values=true`; surrounding strings are never returned.
Existing source rows map the DEX entry to the original input.

These are candidates, including test values and public/restricted identifiers. Credentials
are never sent to providers for probing. The scan does not resolve instruction use sites,
assets, native code, runtime values, obfuscated encodings or arbitrary secret formats.
No Java backend is required. Defaults: 64 MiB cumulative decoded UTF-8 bytes,
2M strings, skip strings above 64K UTF-16 units, cap 20 matches per pattern/string.
Byte/string-count exhaustion is an error; oversize skips/match caps report partial coverage.
The maximum requested byte budget is 256 MiB. Candidate paging rescans pools but never
builds the full instruction index. An empty result is scoped to these patterns and limits.

## Structural investigation

Use `asc_query_dex_session` or `asc_analyze_dex` for `search_classes`, `get_class_outline`,
`get_class_hierarchy`, `get_string_constants`, `search_method_bodies`, `disassemble_method`
and `get_class_source_metadata`. Discovery accepts `case_sensitive=false`;
`search_members(member_match="name")` matches names rather than complete descriptors.
Exact method/field queries still require full returned identities, not guessed overloads.
Hierarchy is limited to supplied definitions; external ancestors and cycles are explicit.
Decoded instruction text includes registers, literals and switch/array payloads. Source token
links use Unicode code-point spans and are not instruction references. Follow all pages.

DEX 041 physical containers support multiple logical files and shared physical string data.
Strict validation precedes standalone Google Smali dexlib2 3.0.9 normalization. This uncommon
format requires JDK 17+ and `DROIDASC_MCP_DEXLIB_HOME`, not JADX. Run
`uv run python scripts/setup_dexlib.py` explicitly to install the pinned small JAR set.
Original container hashes,
logical header offsets and normalized DEX hashes are separate evidence fields. The aggregate
normalized-byte limit is the smaller of the input limit and twice the container size.

`asc_inspect_artifact(class_query=..., class_prefix=...)` filters JVM class entries, including
first-level nested JARs. `compare_to=...` compares JVM class identities with common counts;
mixed artifacts also need the DEX comparison. JVM decompilation and split reconstruction
are not implemented by either this product or the pinned competitor.

Entry tools accept all supported archive formats. `asc_read_apk_entry` returns at most
128 KiB per call; follow `next_byte_offset` with `byte_offset` to reconstruct larger entries.
Decoded XML uses UTF-8 byte offsets; raw binary uses original entry byte offsets. CRC status
is separate from page completeness. The two resource templates expose paged JSON envelopes:
`droidasc://artifact/manifest{?apk_path,offset,limit}` and
`droidasc://session/{session_id}/class{?class_name,offset,limit}`. Percent-encode query values,
including spaces and literal plus signs. The `compare_versions` prompt complements triage
and exact-method tracing. Full source traceability is in [COMPETITOR_API_AUDIT.md](COMPETITOR_API_AUDIT.md).
