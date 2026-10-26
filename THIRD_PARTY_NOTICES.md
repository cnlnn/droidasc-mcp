# Optional preparation dependency

The `preparation` extra installs `zlib-ng==1.0.0` from PyPI. It is not vendored
into this project's source or wheel. The base installation does not require it.

- Python bindings: [python-zlib-ng 1.0.0](https://pypi.org/project/zlib-ng/1.0.0/),
  developed by Ruben Vorderman and contributors at Leiden University Medical
  Center; PSF-2.0 license. See the
  [upstream license](https://github.com/pycompression/python-zlib-ng/blob/v1.0.0/LICENSE).
- Its separately distributed native library is
  [zlib-ng](https://github.com/zlib-ng/zlib-ng), licensed under the zlib license;
  the dependency distribution carries its applicable notices.

This project's Apache-2.0 license does not replace dependency licenses.
