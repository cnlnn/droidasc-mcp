import mmap
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from droidasc.asc_client.apk.dex_reader import (
    _dex_defines_class as _defines_class,
    class_defines_prefix_len,
    list_dex_classes as _list_classes,
)
from droidasc.asc_client.apk.loader import (
    _inflate_dex as _load_dex,
    _inflate_dex_prefix,
    _parse_cd_dex_entries as _parse_entries,
)
from droidasc.asc_client.dex_container import iter_logical_dex_buffers


def _inflate_and_hit(
    mm : mmap.mmap,
    entry,
    target_bytes : bytes,
    stop_event,
    log,
):
    tid = threading.get_ident() & 0xFFFF
    name = entry[0]
    # Multi-DEX lookup shares this event so a hit stops queued inflates and
    # logical-DEX scans. The single-entry fast path passes None.
    if stop_event is not None and stop_event.is_set():
        return False, None, None

    t0 = time.perf_counter()
    prefix = _inflate_dex_prefix(
        mm,
        entry,
        lambda buf, full_size: class_defines_prefix_len(
            buf,
            target_bytes,
            full_size,
        ),
        stop_event,
    )
    if prefix is None:
        data = _load_dex(mm, entry, stop_event)
        if data is None:
            return False, None, None
    else:
        prefix_data, complete = prefix
        try:
            prefix_hit = _defines_class(prefix_data, target_bytes)
        except (IndexError, ValueError):
            prefix_hit = None
        if prefix_hit is False:
            return False, None, None
        if complete:
            data = prefix_data
        else:
            data = _load_dex(mm, entry, stop_event)
            if data is None:
                return False, None, None
    t1 = time.perf_counter()
    if stop_event is not None and stop_event.is_set():
        return False, None, None

    hit = False
    hit_name = None
    hit_data = None
    for dex_name, dex_buf in iter_logical_dex_buffers(name, data):
        if stop_event is not None and stop_event.is_set():
            return False, None, None
        if _defines_class(dex_buf, target_bytes):
            hit = True
            hit_name = dex_name
            hit_data = dex_buf
            break
    t2 = time.perf_counter()
    if hit and stop_event is not None:
        stop_event.set()
    log(
        f"[APK] [T{tid:04x}] '{name}' inflate={(t1 - t0) * 1000000:.2f} us "
        f"lookup={(t2 - t1) * 1000000:.2f} us hit={hit}"
    )
    return hit, hit_name, hit_data


class ApkHandler:
    def __init__(self, apk_path : str, debug : bool = False, max_workers : int = 8):
        self.apk_path = apk_path
        self.debug = debug
        self.max_workers = max_workers

    def _log(self, msg : str):
        if self.debug:
            print(msg)

    def _open_apk(self):
        fp = open(self.apk_path, "rb")
        mm = mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ)
        return fp, mm

    def get_class_dex(self, dalvik_class : str):
        # DEX string_data_item uses MUTF-8. Non-BMP descriptors therefore need
        # CESU-8 bytes to preserve the table's UTF-16 code-unit ordering.
        target_bytes = dalvik_class.encode("utf-8")
        if not dalvik_class.isascii() and any(
            ord(ch) > 0xFFFF for ch in dalvik_class
        ):
            from mutf8 import encode_modified_utf8

            target_bytes = encode_modified_utf8(dalvik_class)
        t_start = time.perf_counter()
        fp, mm = self._open_apk()
        try:
            entries = _parse_entries(mm)
            # Small compressed entries finish first, increasing the chance that
            # a hit cancels expensive inflates which have not started yet.
            entries.sort(key=lambda x: x[2])
            if self.debug:
                t_ready = time.perf_counter()
                self._log(
                    f"[APK] scan setup={(t_ready - t_start) * 1000000:.2f} us "
                    f"entries={len(entries)}"
                )
            if not entries:
                return None

            hit_name = None
            hit_data = None

            # A thread pool cannot parallelize one item. Skipping it also lets
            # Deflate use the faster non-cancellable one-shot path.
            if len(entries) == 1 and self.max_workers > 0:
                ok, hit_name, hit_data = _inflate_and_hit(
                    mm,
                    entries[0],
                    target_bytes,
                    None,
                    self._log,
                )
                if not ok:
                    hit_name = None
                    hit_data = None
            else:
                stop_event = threading.Event()
                # Limit outstanding inflates even when the configured executor
                # is large; decompressed DEX buffers can consume substantial RAM.
                cap = min(len(entries), max(6, min(self.max_workers, 12)))
                with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
                    inflight = {}
                    idx = 0
                    while idx < len(entries) or inflight:
                        while (
                            idx < len(entries)
                            and len(inflight) < cap
                            and not stop_event.is_set()
                        ):
                            entry = entries[idx]
                            idx += 1
                            fut = ex.submit(
                                _inflate_and_hit,
                                mm,
                                entry,
                                target_bytes,
                                stop_event,
                                self._log,
                            )
                            inflight[fut] = entry

                        if not inflight:
                            break

                        done, _pending = wait(
                            list(inflight.keys()),
                            return_when=FIRST_COMPLETED,
                        )
                        for fut in done:
                            inflight.pop(fut)
                            ok, dex_name, data = fut.result()
                            if ok:
                                hit_name = dex_name
                                hit_data = data
                                stop_event.set()
                                break

                        if hit_name is not None:
                            for fut in inflight:
                                fut.cancel()
                            break

            if self.debug:
                t_end = time.perf_counter()
                self._log(
                    f"[APK] getclass total={(t_end - t_start) * 1000000:.2f} us"
                )
            if hit_name is None:
                return None
            return hit_name, hit_data
        finally:
            mm.close()
            fp.close()

    def list_classes(self, prefix : str = None):
        if self.max_workers <= 0:
            raise ValueError("Worker count must be greater than zero")
        if prefix is not None:
            prefix = prefix.strip()
            if not prefix:
                raise ValueError("Class prefix cannot be empty")
            if not prefix.startswith("L"):
                prefix = "L" + prefix.replace(".", "/")
        prefix_bytes = prefix.encode("ascii") if prefix and prefix.isascii() else None

        t_start = time.perf_counter()
        fp, mm = self._open_apk()
        try:
            entries = _parse_entries(mm)
            if not entries:
                return []

            def list_entry(entry):
                data = _load_dex(mm, entry)
                names = []
                for _dex_name, dex_buf in iter_logical_dex_buffers(entry[0], data):
                    names.extend(
                        _list_classes(
                            dex_buf,
                            prefix=prefix,
                            prefix_bytes=prefix_bytes,
                        )
                    )
                return entry[0], names

            workers = min(len(entries), self.max_workers)
            if workers == 1:
                results = [list_entry(entry) for entry in entries]
            else:
                with ThreadPoolExecutor(max_workers=workers) as ex:
                    # map keeps central-directory order even when workers finish
                    # out of order, so CLI class listing stays deterministic.
                    results = list(ex.map(list_entry, entries))

            names = []
            for dex_name, dex_names in results:
                names.extend(dex_names)
                self._log(f"[APK] '{dex_name}' class_count={len(dex_names)}")

            if self.debug:
                t_end = time.perf_counter()
                self._log(
                    f"[APK] listclass total={(t_end - t_start) * 1000000:.2f} us "
                    f"count={len(names)} workers={workers}"
                )
            return names
        finally:
            mm.close()
            fp.close()

    def for_each_findrefs(self, find_type : str, find : dict):
        # Keep the process-pool import off the getclass startup path.
        from concurrent.futures import ProcessPoolExecutor
        from droidasc.asc_client.apk import worker as _worker

        t_start = time.perf_counter()
        fp, mm = self._open_apk()
        try:
            entries = _parse_entries(mm)
            entries.sort(key=lambda x: x[2])
        finally:
            mm.close()
            fp.close()

        if not entries:
            return

        # A forked child inherits pending stdio buffers, so flush before forking.
        sys.stdout.flush()
        sys.stderr.flush()
        with ProcessPoolExecutor(
            max_workers=self.max_workers,
            mp_context=_worker._process_pool_context(),
        ) as ex:
            futures = {}
            for entry in entries:
                fut = ex.submit(
                    _worker._findrefs_worker,
                    self.apk_path,
                    entry,
                    find_type,
                    find,
                )
                futures[fut] = entry[0]

            # Findrefs is intentionally streamed in completion order. The CLI
            # can print a finished DEX without waiting for slower siblings.
            while futures:
                done, _pending = wait(
                    list(futures.keys()),
                    return_when=FIRST_COMPLETED,
                )
                for fut in done:
                    futures.pop(fut)
                    dex_name, lines, inflate_us, process_us, pid = fut.result()
                    if self.debug:
                        self._log(
                            f"[APK] [P{pid}] '{dex_name}' "
                            f"inflate={inflate_us:.2f} us "
                            f"process={process_us:.2f} us"
                        )
                    yield dex_name, lines

        if self.debug:
            t_end = time.perf_counter()
            self._log(
                f"[APK] for_each_findrefs total={(t_end - t_start) * 1000000:.2f} us "
                f"count={len(entries)} workers={self.max_workers}"
            )
