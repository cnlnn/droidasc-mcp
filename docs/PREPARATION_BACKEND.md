# Optional preparation backends

Install the optional dependency with `pip install 'droidasc-mcp[preparation]'`
or use `uv sync --locked --extra dev --extra preparation` for development.
The extra pins `zlib-ng==1.0.0`; the base installation retains standard-library
checksums and does not require a platform-specific compression package.

Before processing input, optional CRC32 must match standard-library vectors,
seeds and chunk continuation. A missing, different-version or incompatible
backend leaves standard-library CRC32 selected. Adler32 is separately checked
for diagnostic compatibility, but remains standard-library in this stage.
The selected implementation and reason are exposed as `CRC_BACKEND_NAME`,
`CRC_BACKEND_REASON`, `ADLER_BACKEND_NAME` and `ADLER_BACKEND_REASON` in the private
preparation backend module.

The pinned zlib-ng Adler32 implementation differs from stdlib for empty input
with seed `0xffffffff`; this compatibility check is retained, so Adler32 stays
standard-library while separately compatible CRC32 may use zlib-ng. There is no
seed-normalizing wrapper or weakened preflight.
Failures during actual processing propagate: partially consumed input is never
retried under another backend.

DEX Adler32 calls remain unchanged standard-library calls. Native snapshot CRC
validation, when using an explicitly supplied checksum function, must still read
and validate every byte through bounded owned chunks. No integrity check is
removed, stored snapshot bytes are unchanged, and no performance claim follows
from backend availability alone.

## Preparation ZIP inflation

The optional inflater has an independent bounded preflight for raw deflate,
output limits, remaining input, end-of-stream state, flush behavior and malformed
input. Unsupported stdlib function shapes, closures or bindings retain ordinary
stdlib readers before an optional member decoder consumes input. Adapter selection
is bound to each preparation archive before its directory is read; importing the
inventory class for ordinary resource operations does not select the backend.

Compatible unencrypted stored/deflated preparation members use private copies of
the current stdlib function code with isolated decoder/checksum bindings. Header,
overlap, CRC, read-size and seek behavior retain the stdlib implementation;
ordinary ZIP readers, writers and module globals are not modified. Other member
compression methods and encrypted members retain the ordinary reader.

`INFLATE_BACKEND_NAME` and `INFLATE_BACKEND_REASON` in the private preparation
inflater module identify selection or fallback. Qualification must additionally
verify the actual selected decoder, not merely the label or installed package.
Backend decompression errors are normalized to the stdlib exception type; other
runtime failures propagate. A partially consumed stream is never retried with a
different decoder. Truncation behavior is compared with stdlib rather than
assuming every truncated raw-deflate stream must raise before ZIP validation.

Optional-platform installation and correctness remain subject to the supported
Python/OS test matrix. See [dependency notices](../THIRD_PARTY_NOTICES.md).
