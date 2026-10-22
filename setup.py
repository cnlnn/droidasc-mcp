"""Optional native accelerator with the public buffer API on Python 3.10+."""

import sys

from setuptools import Extension, setup

stable = sys.version_info >= (3, 11)

setup(
    ext_modules=[
        Extension(
            "droidasc_mcp._dexscan",
            ["src/droidasc_mcp/_dexscan.c"],
            define_macros=[("Py_LIMITED_API", "0x030B0000")] if stable else [],
            py_limited_api=stable,
            optional=True,
        )
    ],
    options={"bdist_wheel": {"py_limited_api": "cp311"}} if stable else {},
)
