import atexit
import mmap
import os
import sys
import threading
import time
import types

from droidasc.asc_client.apk.loader import _inflate_dex
from droidasc.asc_client.dex_container import iter_logical_dex_buffers


_WORKER_APK_PATH = None
_WORKER_APK_FP = None
_WORKER_APK_MM = None


def _process_pool_context():
    """Use fork only when the platform and parent process make it safe."""
    if os.name == "nt":
        return None
    try:
        import multiprocessing

        # Startup shims may leave a module-like placeholder in sys.modules.
        # ProcessPoolExecutor can hang if that object is accepted as a context.
        if (
            not isinstance(multiprocessing, types.ModuleType)
            or not hasattr(multiprocessing, "get_context")
        ):
            return None
        if threading.active_count() != 1:
            return None
        return multiprocessing.get_context("fork")
    except (ImportError, ValueError, OSError):
        return None


def _close_worker_apk():
    global _WORKER_APK_PATH, _WORKER_APK_FP, _WORKER_APK_MM

    mm = _WORKER_APK_MM
    fp = _WORKER_APK_FP
    _WORKER_APK_MM = None
    _WORKER_APK_FP = None
    _WORKER_APK_PATH = None

    if mm is not None:
        mm.close()
    if fp is not None:
        fp.close()


atexit.register(_close_worker_apk)


def _get_worker_apk_mm(apk_path : str):
    global _WORKER_APK_PATH, _WORKER_APK_FP, _WORKER_APK_MM

    mm = _WORKER_APK_MM
    if mm is not None and _WORKER_APK_PATH == apk_path:
        # One worker handles several DEX entries from the same APK. Reusing its
        # read-only mapping avoids reopening a large archive for every task.
        return mm

    _close_worker_apk()
    fp = open(apk_path, "rb")
    mm = mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ)
    _WORKER_APK_PATH = apk_path
    _WORKER_APK_FP = fp
    _WORKER_APK_MM = mm
    return mm


def _findrefs_worker(
    apk_path : str,
    entry,
    find_type : str,
    find : dict,
    aggregate : bool = True,
):
    # Keep the decompiler graph out of CLI getclass/listclass startup. Spawned
    # workers import it only after they receive a reference-search task.
    from droidasc.asc_client.asc_handler import AscHandler

    mm = _get_worker_apk_mm(apk_path)
    t0 = time.perf_counter()
    data = _inflate_dex(mm, entry)
    t1 = time.perf_counter()
    lines = []
    handler = AscHandler(False)
    # A physical classes*.dex entry may contain several logical DEX files in
    # the DEX 041 container format; each needs an independent reference scan.
    for dex_name, dex_buf in iter_logical_dex_buffers(entry[0], data):
        lines.extend(
            handler.findrefs(
                dex_name,
                dex_buf,
                find_type,
                find,
                aggregate=aggregate,
            )
        )
    t2 = time.perf_counter()
    return (
        entry[0],
        lines,
        (t1 - t0) * 1000000,
        (t2 - t1) * 1000000,
        os.getpid(),
    )
