# Droid ASC source compatibility candidate

This directory is a source-only downstream compatibility build of Droid ASC,
named `droidasc` and versioned `0.1.2.post3+sourcefixes.2`. It is not an official
upstream release or a newly published droidasc-mcp version.

## Origin

- Upstream repository: https://github.com/MG1937/ASC
- Reviewed upstream base: `9216fe234e1fc80f3148ca42e361e67e3174d0e2`
- Released source distribution: `droidasc-0.1.2.post3.tar.gz`
- Source URL: https://files.pythonhosted.org/packages/61/2c/107e0054d1501e3890e859eb671f5a2df5b1da94b86fcd5db13fe7b39d94/droidasc-0.1.2.post3.tar.gz
- Original source SHA-256: `0e292a2756db85c5fd3fda0a397f2ad544c8de016135a79ed5ed739ecbb89230`
- License: the original upstream `LICENSE` is retained byte-for-byte.

The release sdist, rather than the upstream Git tree, is the base. In particular,
all 23 released bundled dadguard Python files are unchanged. Existing upstream
copyright, license notices and public source tests are retained.

## Local modifications

Prepared on 2026-10-29 for the cnlnn/droidasc-mcp development branch:

1. `droidasc/asc_core/utils/decompiler.py`: reuse the existing class-manager
   accessor to load lazy method annotation directories before source rendering.
   Prepared upstream contribution commit:
   `51e2b31707d47ab28e3e78c4e8c52cd21da54900`.
2. The same file: preserve original field/parameter/return/array type identities
   in source class links using existing upstream token and Writer extensions;
   display-only types without original context and this/super keywords have no
   guessed class identity. Prepared upstream contribution commit:
   `140b05cd3a62a1603e4a70f35631adbd841cfe90`.
3. `pyproject.toml`: identify this downstream build with the local version above.
4. `README.md`: add the compatibility-build and source-link modification notice.
5. On 2026-10-30, add prominent ASCII downstream-change comments at the start of
   the modified decompiler and `pyproject.toml`, naming cnlnn/droidasc-mcp, the
   modification date, and the specific runtime fixes or local-version change.

These contributions are prepared locally; their commit IDs do not imply an
upstream merge or published release. Of the 80 runtime Python files, 79 exactly
match the evaluated `droidasc-0.1.2.post3+sourcefixes.2-py3-none-any.whl`, SHA-256
`0faa06b46dc25e12d93e18e8c2e47ab302943f56b9d2774fe69b6eafa3d96aee`.
The sole difference is the decompiler's downstream comment prefix; removing that
exact prefix reproduces the evaluated file SHA-256
`81fc8edff8881949441bcdeb3ed6b54bb371203aaf6bd99c028af5236d9d8836`.
With the notice, its SHA-256 is
`ccc302d8b5d980a8e2254f1eaa228a11600d01f002938f6a29ec32738d4ebf82`.
The executable Python AST is unchanged by the notice. All 23 released dadguard
files remain byte-identical. Only the decompiler runtime file differs from the
original released sdist.

## Contents

`manifest.json` hashes the 96 carried source/build-input files, including 80
runtime Python files, 12 public upstream tests and four source metadata/license
files. It also records the corresponding original sdist file hashes.
This directory adds only this provenance document and that manifest.

Generated root `PKG-INFO` and `droidasc.egg-info/` are omitted: they contain old
release metadata and setuptools regenerates them from the included build inputs.
No package resource from the official sdist is omitted. There are no APKs,
compiled binaries, environments, private verification inputs or build caches.

The ordinary setuptools backend, `droidasc` entry point, package discovery and
runtime dependency declarations remain upstream's packaging path. Dependency
selection in the parent project and changed-dependency platform acceptance are
separate from carrying these sources.
