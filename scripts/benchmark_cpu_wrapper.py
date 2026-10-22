"""Apply an inherited CPU budget before importing either real benchmark server."""

import argparse
import runpy
import sys

import psutil


def select_cpus(workers, process=None):
    process = process or psutil.Process()
    if not hasattr(process, "cpu_affinity"):
        raise RuntimeError("Matched CPU budgets require process CPU affinity support")
    allowed = sorted(process.cpu_affinity())
    if not 1 <= workers <= len(allowed):
        raise ValueError("Worker CPU budget exceeds the available affinity set")
    return allowed[:workers]


def configure_affinity(cpus, process=None):
    process = process or psutil.Process()
    if (
        not cpus
        or len(cpus) != len(set(cpus))
        or any(type(cpu) is not int or cpu < 0 for cpu in cpus)
    ):
        raise ValueError("CPU affinity requires unique nonnegative processor numbers")
    if not hasattr(process, "cpu_affinity"):
        raise RuntimeError("Matched CPU budgets require process CPU affinity support")
    if not set(cpus) <= set(process.cpu_affinity()):
        raise ValueError("Requested CPU affinity is not available")
    process.cpu_affinity(cpus)
    if set(process.cpu_affinity()) != set(cpus):
        raise RuntimeError("Could not apply the complete benchmark CPU affinity")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cpus", required=True)
    parser.add_argument("module", choices=["droidasc_mcp", "asc_mcp"])
    args = parser.parse_args()
    configure_affinity([int(value) for value in args.cpus.split(",")])
    sys.argv = [args.module]
    # alter_sys matches python -m semantics for multiprocessing spawn children.
    runpy.run_module(args.module, run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()
