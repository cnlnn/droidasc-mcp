"""Optional stable-ABI accelerator; source installs retain the Python fallback."""

from setuptools import Extension, setup

setup(
    ext_modules=[
        Extension(
            "droidasc_mcp._dexscan",
            ["src/droidasc_mcp/_dexscan.c"],
            define_macros=[("Py_LIMITED_API", "0x030A0000")],
            py_limited_api=True,
            optional=True,
        )
    ],
    options={"bdist_wheel": {"py_limited_api": "cp310"}},
)
