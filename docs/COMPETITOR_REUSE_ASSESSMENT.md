# Competitor Code Reuse Assessment

Date: 2026-10-28. Scope: acquire and evaluate reusable source before further product
changes. The B1-B6 goal remains paused. This assessment does not change its scope,
approve a release, or claim candidate acceptance.

## Acquired Source

Fetched `https://github.com/aimardcr/asc-mcp.git`; both local HEAD and freshly fetched
`origin/main` are `848c711f1d80a1c2577283f1fa5f475ff734aa40`. The existing comparator
checkout is clean. Exported all 72 tracked files, including tests and LICENSE, to:

- `artifacts/competitor-reuse-assessment-20261028/upstream/`
- `artifacts/competitor-reuse-assessment-20261028/asc-mcp-848c711f.tar`
- Archive SHA-256: `0da678b8a6c20f616ccd943e0d7e66cf08dbd919bf00d727bd1f8f5969301893`

`acquisition.json` in that directory binds every exported file to its SHA-256 and
the checked checkout. Both projects declare Apache-2.0. Keep the exported LICENSE,
original attribution and modification records when incorporating selected code;
the upstream tree has no separate NOTICE. Runtime copying does not require making
the whole competitor package a new product dependency.

The unmodified upstream suite passed **52 tests** on Python 3.13.11, MCP 2.2.0,
Pydantic 2.13.5 and Androguard 4.1.4. Test-reported time was 7.658 seconds; launcher
time was 10.136 seconds. `upstream-tests.json` and its stdout/stderr logs preserve
the command, versions, results and unchanged source hashes. This proves that this
checkout runs in this environment, not all-format correctness or Windows parity.

## Reuse Decisions

Paths in the upstream column are relative to the pinned export above. Existing
product paths refer to the current worktree, including the unfinished B3 port.

| Batch | Exact upstream source | Decision | Minimum adaptation |
| --- | --- | --- | --- |
| B3 identity | `asc_mcp/sessions.py:24` `AnalysisSession`; `:84` `SessionRegistry.open` | Copy the record and inventory/capability flow | Attach it to existing `DexSessions` ownership, snapshot bytes and lazy preparation; do not create another lifetime registry |
| B3 tools | `asc_mcp/server.py:223` through `:740`, `models.py` | Copy focused handle signatures and forwarding functions where semantics match | Route to existing services, retain bounded continuations and original identities, expose one profile, preserve callable old tools |
| B3 metadata | `service.py:357` `summary`; `server.py:629` entry/resource tools | Reuse the unified summary and handle workflow | Use existing checked archive/manifest/signing readers; preserve pagination, XML limitations and certificate-inventory wording |
| B3 resources | `server.py:747` manifest/class resources and `:762` prompts | Reuse handle-to-resource and trace flow | Preserve existing resource URIs; add handle links and profile-consistent instructions |
| B4 targeted lookup | `analysis/artifact_handler.py:69` `_find_type_idx`, `:107` `_class_defs_contains_type_idx`, `:340` `get_class_dex` | Candidate for direct helper/scheduling reuse, not a wholesale backend replacement | Feed checked bytes; preserve class ambiguity detection, cancellation and byte budgets; measure cold end-to-end effects before adoption |
| B4 cached work | `service.py:90-241` cache functions | Reuse only an identified missing computation, not global cache ownership | Existing selected-set caches already cover much of this work; keep immutable content keys and byte quotas |
| B5 module union | `analysis/artifact_handler.py:139` ZIP DEX enumeration and `:396` class enumeration | Reuse the all-DEX iteration behavior | Extend existing checked `containers.select` for explicit multiple/all selection; preserve default base, module provenance and duplicate diagnostics |
| B6 logical views | `analysis/dex_container.py:14`, `:71`, `:142` | Directly copy the active logical-offset/header-view/iteration helpers, about 40 lines | Authorize views with existing strict original-byte validation; adapt receiving readers to physical addresses; keep original hashes and explicit source compatibility route |

### B3 Remaining Work Is Mostly Integration

The worktree already contains the upstream-derived record/inventory logic in
`src/droidasc_mcp/analysis_session.py`, integrated into `sessions.py`. Seven
handle tools are registered at `server.py:865` onward. They are callable but are
intentionally absent from the still-legacy default advertisement. This is partial
implementation, not a finished profile. The prior 69-case focused receipt is
`artifacts/competitor-gap-b3-20261028/artifact-port-mcp.xml`; it includes stdio
calls and lifetime tests, not the missing model/cross-platform gates.

Finish the remaining upstream-focused wrappers rather than reimplement their
algorithms. Existing method/field/string/type/graph/source operations should remain
the receivers. Keep all 24 current DEX operations reachable: upstream's 25-tool
surface is not an instruction to remove our exact-method, broad-type, index or
source-metadata capabilities. Complete the profile setting, resources/prompts,
compatibility checks and the frozen four-task candidate comparison. The baseline
already exists; do not create another baseline program.

Dependency closure for the record/registry is Python standard library; tool wrappers
use the MCP/Pydantic stack already present. Importing the entire upstream service
would also import TinyDEX, the locator stack, process-global caches and optional
Androguard paths unnecessarily. Source bodies and interfaces can be ported without
that wholesale replacement. Sources: pinned `sessions.py`, `server.py:1-39`,
`service.py:1-15`, `pyproject.toml:15-19`; current `pyproject.toml`.

## Boundaries Confirmed By Fresh Probes

All probes are small local inputs, not a new performance baseline. Scripts, input
hashes and results are retained under the acquisition directory.

1. **Stat-only session identity is insufficient.** A valid DEX was changed while
   retaining size and mtime. Upstream `SessionRegistry.get` accepted it and returned
   the previous SHA-256. Copy the record/open flow, but retain our snapshot identity.
   Source: `sessions.py:153-165`; evidence: `b3-b4-probes.json`.
2. **The fast raw ZIP reader skips CRC validation.** With incorrect CRC fields,
   stdlib ZIP reading rejected the entry, but `_inflate_dex` returned its bytes.
   Reuse lookup/scheduling with our checked ZIP reader, not that reader unchanged.
   Source: `artifact_handler.py:139-173,231-254`; evidence: `b3-b4-probes.json`.
3. **AAB all-entry enumeration works; complete module policy is not upstream code.**
   A base/feature fixture enumerated both modules. The public class list collapsed
   a duplicate, and class outline chose base without ambiguity. Module manifests
   existed, but the manifest call required a root manifest and failed. Explicit
   module selection/routing in B5 is an extension beyond upstream behavior, not a
   preexisting module that can be copied whole. Sources: `service.py:175-187,216-223,
   291-294`; evidence: `probe-b5-b6.json`.
4. **DEX 041 physical views are genuinely reusable.** Two logical files enumerate
   correctly; unshared string-reference calls work. Initialized upstream workers
   also produce correct second-file source for shared and unshared fixtures. This
   supports copying the view code rather than inventing another parser. Sources:
   `analysis/dex_container.py:71-79,142-149`; evidence:
   `probe-b5-b6.json`, `source041-initialized-worker.json`.
5. **The entire 041 scanner stack is not safe to transplant unchanged.** The shared
   string fixture fails in the second logical file with `KeyError: 311`, reproduced
   in a fresh process at `core/findrefs/locator/string_locator.py:72`. Five malformed
   container/header/checksum cases were not rejected; corrupt second headers can
   silently hide the second class. Preserve our strict validator and per-ID string
   decoding. Evidence: `shared041-fresh-process.json`, `probe-b5-b6.json`.

The first direct 041 source probe omitted `initialize_worker()` and failed on
`http.client`. Its failure remains in the original receipt; the corrected worker
path succeeded. It is a probe setup error, not a claimed upstream source failure.

Do not transplant `runtime.py`'s resident pool and `service.py`'s process-global
LRUs into a second owner. They are bounded by item count, not our current byte and
lifetime budgets. Similarly, `core/utils/decompiler.py:15-95` installs module stubs
and an Adler32-error patch: any source handoff stays in an isolated worker after
original-input validation, not in the MCP host. These are source-backed adaptation
boundaries, not reasons to reject the useful independent functions above.

## Minimal Remaining Adaptation

- **B4:** First identify a missing computation from the existing phase profiles.
  The current code already has checked streaming ZIP inventory and selected-set
  reuse. Replacing them with an unchecked reader/global cache is not a performance
  fix. The new whole-artifact snapshot's copy/hash cost must remain visible.
- **B5:** Extend `containers.py:53` and existing union preparation; carry selected
  modules and original entry names into metadata and module-addressed reads. Reuse
  `test_containers.py:440` and `test_artifact_summary.py`; add cross-module reference,
  empty/invalid module and shared-quota cases. No new protobuf decoder is assumed.
- **B6:** Separate strict validation in `dex_container.py:26-58` from its Java loop;
  port the upstream physical views into `dex_worker.py` metadata and
  `native_dex.py:107` addressing. Adjust `native_snapshot.py`, `native_directory.py`
  and the standard-only C class-header gate at `_dexscan.c:741`; reuse existing
  instruction decoders. Existing `tests/test_dex_container.py:16,75` and
  `tests/dex041_fixture.py` supply independent original-byte parity and malformed
  cases. Add no-Java native-query runs; keep source handoff a separate acceptance
  condition rather than declaring full 041 support from class enumeration.

## Work Estimate

These are source-based planning estimates of **active engineering time**, not
measured execution times, deadlines or guarantees that every acceptance gate will
pass. Existing upstream tests and our already-built fixtures are reused.

| Scope | Planning range | Confidence and boundary |
| --- | --- | --- |
| Finish B3 wrappers, profiles and links, with targeted regression | 2-4 hours | Medium; core lifetime port is already present, model/cross-platform acceptance remains separate |
| B4 one measured reuse candidate and phase comparison | 1-3 hours | Low; bounds an experiment, not guaranteed performance parity; report residuals explicitly |
| B5 selector/routing extension and targeted tests | 2-4 hours | Medium; union preparation and duplicate enforcement already exist |
| B6 physical-view receiving-side integration and targeted parity | 4-8 hours | Low-medium; shared addresses and native class-header gates are real adaptations |
| Combined first acceptance round | 2-4 hours | Conditional on candidate readiness, provider/CI availability and no failures; repair cycles are additional |

The row sum is **11-23 active hours**, an initial planning envelope, not a promised
time to full B1-B6 acceptance. The central correction is architectural: this is a
small upstream view/interface port plus specific receiving-side adaptations, not a
new parser or independent product rewrite. B4 performance and B6 native/source
integration remain the largest uncertainties. Do not silently shrink B5/B6 to
upstream's narrower behavior merely to call the goal complete.

Supporting detail: `artifacts/competitor-reuse-assessment-20261028/b5-b6.md`.
No product code was changed during this assessment; the preexisting unfinished B3
worktree remains intact. Resume implementation only under the maintainer's direction.
