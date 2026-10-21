# Optional Rust backend

Candidate integration, not a release or a universal replacement for Python ASC.
Pinned upstream [rust_ASC 236dd096](https://github.com/MG1937/rust_ASC/tree/236dd096669c99eb30f6e1af0b24e668eff55dd5),
radguard submodule `290de20c925c4a2c7642b1a63c9997185a06e130`.
The source is Apache-2.0; no upstream implementation is vendored into this package.

`scripts/setup_rust.py` builds `--release --locked --no-default-features`, checks the
submodule revision, and exports the binary path in GitHub Actions. Set
`DROIDASC_MCP_RUST_ASC` explicitly outside CI. The adapter invokes public CLI verbs
`getmanifest`, `listclass`, `getclass` and `findrefs`, not the upstream MCP listener.
It translates only the positional thread option to `--thread`; user query strings
are not rewritten as command-line flags. No `--version` contract exists upstream.

A Python bootstrap launches the native child so the existing supervisor still owns
the complete process tree. Allowed roots, byte/output limits, global concurrency,
timeouts, aggregate memory and cancellation remain shared with the Python path.
Unsupported hierarchy queries and missing configuration fail explicitly; nothing
silently switches backend. Native Rust dependencies are optional, not wheel contents.

Upstream `findrefs` discards some per-DEX scan failures. Therefore each Rust reference
result reports `coverage=not_verified` and `instruction_scan_complete=false`, even
when fixtures have expected hits. This is not repaired by matching one fixture or
the class count. Manifest/source formatting and line counts may differ by backend.
Our descriptor-exact method/field/type index remains a separate dexlib2 facility.

Python ASC at `9216fe234e1fc80f3148ca42e361e67e3174d0e2` does not ship an MCP server.
Rust ASC does, but connecting to our server uses the supervised CLI adapter above.
Neither this integration nor static xrefs establish runtime dispatch, reflection,
JNI execution, loaded DEX completeness or debugger control. A future dynamic
connector must be separately scoped to an explicit device/process and preserve
runtime evidence separately from static operands; none is implemented here.

Reproduce large local samples through actual stdio MCP with
`scripts/benchmark_backends.py sample.apk --output artifacts/benchmark.json`.
Use `--backends-only` to omit DEX/index tests. Reports retain elapsed time, sampled
descendant RSS, counts and original-file hashes, never application source bodies.
Do not upload private APKs. Results are host/sample-specific, not a blanket speed claim.
