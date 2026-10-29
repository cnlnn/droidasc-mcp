# Local ASC Source-Fix Preparation

This checkout-local evaluation bundle prepares a separate, installable-source
candidate. It does not install a package, replace the MCP dependency, download
inputs, create a public contribution, or publish a release.

## Sources

- Upstream: [MG1937/ASC](https://github.com/MG1937/ASC), base
  `9216fe234e1fc80f3148ca42e361e67e3174d0e2`.
- Official base: `droidasc-0.1.2.post3.tar.gz`, SHA-256
  `0e292a2756db85c5fd3fda0a397f2ad544c8de016135a79ed5ed739ecbb89230`.
  The exact original download URL is recorded in `manifest.json`.
  Its source declaration `0.1.2-post3` is also locked separately from the
  normalized official distribution version `0.1.2.post3`.
- `0001-lazy-method-annotations.patch`: local contribution commit
  `51e2b31707d47ab28e3e78c4e8c52cd21da54900`, two runtime lines and four
  generated-fixture regressions.
- `0002-source-type-links.patch`: local contribution commit
  `140b05cd3a62a1603e4a70f35631adbd841cfe90`, original field/return/parameter
  types, array Writer tokens, and twelve regressions.

Both patches are preserved byte-for-byte, including authorship. They are prepared
contributions, not commits published by upstream. The source remains Apache-2.0;
the original upstream `LICENSE` is included unchanged. The array Writer adaptations
follow the existing ASC extension pattern and retain the rendering sequence from
bundled dadguard/Androguard. The prepared README records these local modifications.

The official sdist, rather than a Git-tree copy, preserves the released dadguard
fixes. All 23 bundled dadguard Python files retain their original bytes. Among the
80 dependency Python files, only `droidasc/asc_core/utils/decompiler.py` changes.
Its final SHA-256 is locked to the previously evaluated sourcefixes.2 candidate.
The local project version and README notice are the only other allowed changes.

The full contribution patches target the upstream Git tree, whose generated-test
helpers differ from the official sdist. In particular, the official sdist does
not contain `tests/dex_fixture.py`. Preparation therefore applies only runtime
hunks with `git apply --include=droidasc/asc_core/utils/decompiler.py`; it never
overwrites or supplements the released test tree to make a patch apply. The four
annotation and twelve source-type regressions remain in the unmodified full
patches for upstream review, not as tests installed by this preparation tool.

## Offline Preparation

Requirements: this repository checkout, Python 3.10 or newer, Git, and the exact
official sdist already available locally. All commands below use the repository
root as the working directory. Output paths are examples, not required locations.

```sh
python scripts/upstream_sourcefixes/prepare.py \
  --sdist /path/to/droidasc-0.1.2.post3.tar.gz \
  --output /tmp/asc-sourcefixes-evaluation
```

Preparation uses the repository's standard-library `scripts/verify_dist.py` safe
sdist extractor, then Git's ordinary offline runtime-hunk application. It rejects changed
inputs/patches, changed runtime boundaries and existing output directories. The
original archive is read-only. `receipt.json` records hashes and the precise scope;
`source/` contains the separate candidate. No dependency or toolchain is installed.

A separate build can use the normal upstream backend:

```sh
uv build --offline --out-dir /tmp/asc-sourcefixes-dist \
  /tmp/asc-sourcefixes-evaluation/source
```

That optional command requires an available cached build backend. Wheel/sdist
identity, normal isolated installation, real transport workflows and portable
changed-dependency acceptance remain separate verification steps. This bundle does
not make those claims, and `0.1.2.post3+sourcefixes.2` identifies a local candidate,
not an official upstream release or an adopted MCP default.
