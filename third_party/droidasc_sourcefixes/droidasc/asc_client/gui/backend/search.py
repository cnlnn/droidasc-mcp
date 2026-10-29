import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

from droidasc.asc_client.apk.worker import _findrefs_worker


_MAX_UI_RESULTS = 5000
# Source decompilation temporarily changes sys.modules while process-pool
# submission imports multiprocessing internals. Serialize those two operations.
_GUI_MP_LOCK = threading.Lock()
_REF_SEARCH_TYPES = {
    "string refs": "string",
    "type refs": "type",
    "method refs": "method",
    "field refs": "field",
}


def _debug_log(enabled : bool, scope : str, msg : str):
    if not enabled:
        return
    tid = threading.get_ident() & 0xFFFF
    now = time.perf_counter()
    print(f"[GUI DEBUG] [{scope}] [T{tid:04x}] {now:.6f} {msg}")


def _multiprocessing_state() -> str:
    mp_mod = sys.modules.get("multiprocessing")
    red_mod = sys.modules.get("multiprocessing.reduction")
    return (
        f"multiprocessing={type(mp_mod).__name__}"
        f" reduction={type(red_mod).__name__}"
    )


def _snapshot_sys_modules():
    return dict(sys.modules)


def _restore_sys_modules(snapshot):
    # Dadguard/Androguard load optional modules dynamically. Restore both added
    # and replaced entries so a decompile cannot poison later process spawning.
    for name in tuple(sys.modules.keys()):
        if name not in snapshot:
            sys.modules.pop(name, None)
    sys.modules.update(snapshot)


def format_class_name(name : str) -> str:
    if not name:
        raise ValueError("Class name cannot be empty")
    if name.startswith("L") and name.endswith(";") and "/" in name:
        return name
    name = name.replace(".", "/")
    if not name.startswith("L"):
        name = f"L{name}"
    if not name.endswith(";"):
        name = f"{name};"
    return name


def dalvik_to_dot(name : str) -> str:
    if name.startswith("L") and name.endswith(";"):
        return name[1:-1].replace("/", ".")
    return name


def _normalize_class_query(name : str, fuzzy : bool):
    if name is None or name == "":
        return None
    if fuzzy:
        if "." in name and "/" not in name:
            return name.replace(".", "/")
        return name
    return format_class_name(name)


def build_find_query(
    find_type : str, value : str, class_name = None, fuzzy_class : bool = False,
    exact_member : bool = False,
):
    find_type = _REF_SEARCH_TYPES.get(find_type, find_type)
    if find_type == "string":
        return "string", {"string": value}
    if find_type == "type":
        return "type", {"type": value}

    class_name = _normalize_class_query(class_name, fuzzy_class)
    if class_name is None and not value:
        raise ValueError(f"{find_type} query needs at least one of class or {find_type} name")

    # FindRefManager uses [value, precise] for exact matching; a plain string is
    # intentionally fuzzy. Keep this protocol at the client/core boundary.
    member = [value, True] if exact_member and value else value or None
    if class_name is None:
        return find_type, {find_type: {"class": None, find_type: member}}
    return find_type, {find_type: {"class": [class_name, not fuzzy_class], find_type: member}}


def _split_member_text(text : str, member_type : str):
    class_name, member_text = text.split("->", 1)
    if member_type == "method":
        split_at = member_text.find("(")
    else:
        split_at = member_text.rfind(":")
    if split_at < 0:
        return class_name, member_text, ""
    if member_type == "method":
        return class_name, member_text[:split_at], member_text[split_at:]
    return class_name, member_text[:split_at], member_text[split_at + 1:]


def parse_result_line(line : str, find_type : str = ""):
    # Worker output is a stable text protocol shared by CLI, process-pool and
    # subprocess backends. Parse it once into the row model used by the GUI.
    dex_name, method_text, matched_text = line.split(" | ", 2)
    matched_text, sep, occurrence_text = matched_text.rpartition(" | occurrence=")
    occurrence = int(occurrence_text) if sep and occurrence_text.isdigit() else 0
    if not sep:
        matched_text = occurrence_text
    class_name, method_name, method_descriptor = _split_member_text(method_text, "method")
    matched_value = matched_text[len("matched=("):-1] if matched_text.startswith("matched=(") else matched_text
    target_class = ""
    target_name = matched_value
    target_descriptor = ""
    if find_type in ("method", "field"):
        target_class, target_name, target_descriptor = _split_member_text(matched_value, find_type)
    elif find_type == "type":
        target_class = matched_value
    return {
        "dex_name": dex_name,
        "class_name": class_name,
        "class_display": dalvik_to_dot(class_name),
        "method_text": method_text,
        "method_name": method_name,
        "method_descriptor": method_descriptor,
        "matched_text": matched_text,
        "target_type": "class" if find_type == "type" else find_type,
        "target_class": target_class,
        "target_name": target_name,
        "target_descriptor": target_descriptor,
        "occurrence": occurrence,
        "line": line,
    }


def is_member_search(find_type : str) -> bool:
    return find_type in ("method", "field")


def get_effective_search_workers(store, requested = None):
    cpu = os.cpu_count() or 4
    workers = requested if requested is not None else store.max_workers
    if workers is None or workers <= 0:
        workers = cpu
    if len(store.entries) > 1:
        workers = max(2, workers)
    return min(len(store.entries), workers)


def search_members(store, find_type : str, value : str, limit : int = _MAX_UI_RESULTS):
    keyword = (value or "").strip()
    dex_names = [entry[0] for entry in store.entries]

    def search_dex(dex_name):
        manager = store.findref_managers.get(dex_name)
        if manager is None:
            return 0, []
        dex = manager.dex
        dex_rows = []
        # Direct member search asks locator indexes for declarations. Reference
        # search takes the worker path below and scans containing methods.
        if find_type == "method":
            locator = manager._get_method_locator(True)
            member_idxs = locator.locate({"class": None, "method": keyword})
            for midx in sorted(member_idxs):
                method = dex.methods[midx]
                class_name = method.cls.fullname
                proto = method.prototype
                descriptor = "(" + "".join(item.descriptor for item in proto.parameters_type) + ")"
                descriptor += dex.get_type(proto.return_type_idx).descriptor
                method_text = f"{class_name}->{method.name}{descriptor}"
                dex_rows.append({
                    "dex_name": dex_name,
                    "class_name": class_name,
                    "class_display": dalvik_to_dot(class_name),
                    "method_text": method_text,
                    "method_name": method.name,
                    "method_descriptor": descriptor,
                    "matched_text": f"method=({method.name})",
                    "target_type": "method",
                    "target_class": class_name,
                    "target_name": method.name,
                    "target_descriptor": descriptor,
                    "occurrence": 0,
                    "line": method_text,
                })
            return len(member_idxs), dex_rows

        locator = manager._get_field_locator(True)
        member_idxs = locator.locate({"class": None, "field": keyword})
        for fidx in sorted(member_idxs):
            field = dex.fields[fidx]
            class_name = field.cls.fullname
            method_text = f"{class_name}->{field.name}"
            dex_rows.append({
                "dex_name": dex_name,
                "class_name": class_name,
                "class_display": dalvik_to_dot(class_name),
                "method_text": method_text,
                "method_name": field.name,
                "method_descriptor": "",
                "matched_text": f"field=({field.name})",
                "target_type": "field",
                "target_class": class_name,
                "target_name": field.name,
                "target_descriptor": field.type.descriptor,
                "occurrence": 0,
                "line": method_text,
            })
        return len(member_idxs), dex_rows

    rows = []
    total_hits = 0
    workers = get_effective_search_workers(store)
    if len(dex_names) <= 1 or workers <= 1:
        results = [search_dex(dex_name) for dex_name in dex_names]
    else:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = [ex.submit(search_dex, dex_name) for dex_name in dex_names]
            # Resolve in submission order so rows follow the loaded DEX order,
            # even though each DEX locator runs concurrently.
            results = [fut.result() for fut in futures]

    for hit_count, dex_rows in results:
        total_hits += hit_count
        if len(rows) < limit:
            rows.extend(dex_rows[:limit - len(rows)])

    return {
        "find_type": find_type,
        "query_value": value,
        "results": rows,
        "total_hits": total_hits,
        "workers": workers,
        "backend": "locator",
    }


def _search_with_process_pool(
    store, executor, workers, find_type, find, progress_callback,
    result_callback = None,
):
    total = len(store.entries)
    hit_count = 0
    shown = []
    # Keep process submission outside decompiler module mutation. Completion
    # handling no longer imports worker state and does not need the lock.
    with _GUI_MP_LOCK:
        _debug_log(
            store.debug,
            "runtime",
            f"search process start dex={total} workers={workers} "
            f"{_multiprocessing_state()} executor={id(executor)}",
        )

        futures = {}
        for entry in store.entries:
            try:
                _debug_log(store.debug, "runtime", f"submit dex={entry[0]}")
                fut = executor.submit(
                    _findrefs_worker,
                    store.apk_path,
                    entry,
                    find_type,
                    find,
                    False,
                )
            except Exception as e:
                _debug_log(
                    store.debug,
                    "runtime",
                    f"submit failed dex={entry[0]} err={type(e).__name__}: {e} "
                    f"{_multiprocessing_state()}",
                )
                traceback.print_exc()
                for pending in futures:
                    pending.cancel()
                raise
            futures[fut] = entry[0]

    done = 0
    try:
        for fut in as_completed(futures):
            dex_name = futures.pop(fut)
            try:
                dex_name, lines, _inflate_us, _process_us, _pid = fut.result()
            except Exception as e:
                _debug_log(
                    store.debug,
                    "runtime",
                    f"result failed dex={dex_name} err={type(e).__name__}: {e} "
                    f"{_multiprocessing_state()}",
                )
                traceback.print_exc()
                raise
            done += 1
            # total_hits counts every match, while shown is capped to protect Tk
            # from creating an unbounded result tree.
            hit_count += len(lines)
            _debug_log(
                store.debug,
                "runtime",
                f"result ok dex={dex_name} pid={_pid} hits={len(lines)} done={done}/{total}",
            )
            batch_rows = []
            if len(shown) < _MAX_UI_RESULTS:
                remain = _MAX_UI_RESULTS - len(shown)
                for line in lines[:remain]:
                    row = parse_result_line(line, find_type)
                    shown.append(row)
                    batch_rows.append(row)
            if batch_rows and result_callback is not None:
                result_callback(batch_rows, done, total, hit_count)
            if progress_callback is not None:
                progress_callback(done, total, hit_count)
    except Exception:
        for pending in futures:
            pending.cancel()
        raise

    return hit_count, shown


def _unlink_result(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _close_pipe(pipe):
    if pipe is None:
        return
    try:
        pipe.close()
    except OSError:
        pass


def _stop_worker(proc):
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=1)
    except (subprocess.TimeoutExpired, TimeoutError):
        proc.kill()
        proc.wait(timeout=1)


def _cleanup_worker(proc, result_path, stop=False):
    if stop:
        try:
            _stop_worker(proc)
        except OSError:
            pass
    _close_pipe(getattr(proc, "stdin", None))
    _close_pipe(getattr(proc, "stderr", None))
    _unlink_result(result_path)


def _launch_subprocess_worker(store, entry, find_type, find):
    # stdout is reserved for launcher/debug output. A temporary JSON file keeps
    # large result payloads out of pipe buffers and avoids child deadlocks.
    result_file = tempfile.NamedTemporaryFile(
        prefix="asc_gui_find_",
        suffix=".json",
        delete=False,
    )
    result_path = result_file.name
    result_file.close()

    payload = {
        "apk_path": store.apk_path,
        "entry": list(entry),
        "find_type": find_type,
        "find": find,
        "result_path": result_path,
    }
    cmd = [sys.executable, "-m", "droidasc.asc_client.gui.backend.worker"]
    creationflags = 0
    if os.name == "nt":
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=os.getcwd(),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
        )
        proc.stdin.write(json.dumps(payload))
        proc.stdin.close()
        return proc, result_path
    except Exception:
        if proc is not None:
            _cleanup_worker(proc, result_path, stop=True)
        else:
            _unlink_result(result_path)
        raise


def _search_with_subprocess_pool(
    store, workers, find_type, find, progress_callback, result_callback = None,
):
    total = len(store.entries)
    hit_count = 0
    shown = []
    done = 0
    idx = 0
    running = []

    try:
        while idx < len(store.entries) or running:
            while idx < len(store.entries) and len(running) < workers:
                entry = store.entries[idx]
                idx += 1
                proc, result_path = _launch_subprocess_worker(
                    store,
                    entry,
                    find_type,
                    find,
                )
                running.append((proc, result_path, entry[0]))

            if not running:
                break

            completed = False
            next_running = []
            for proc, result_path, dex_name in running:
                if proc.poll() is None:
                    next_running.append((proc, result_path, dex_name))
                    continue

                completed = True
                stderr_text = proc.stderr.read() if proc.stderr is not None else ""
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"Search worker failed for {dex_name}: "
                        f"{stderr_text.strip() or proc.returncode}"
                    )

                with open(result_path, "r", encoding="utf-8") as fp:
                    payload = json.load(fp)
                _cleanup_worker(proc, result_path)

                lines = payload["lines"]
                done += 1
                hit_count += len(lines)
                batch_rows = []
                if len(shown) < _MAX_UI_RESULTS:
                    remain = _MAX_UI_RESULTS - len(shown)
                    for line in lines[:remain]:
                        row = parse_result_line(line, find_type)
                        shown.append(row)
                        batch_rows.append(row)
                if batch_rows and result_callback is not None:
                    result_callback(batch_rows, done, total, hit_count)
                if progress_callback is not None:
                    progress_callback(done, total, hit_count)

            running = next_running
            if running and not completed:
                # Poll all children without busy-spinning while still allowing
                # batches from faster DEX files to stream to the UI.
                time.sleep(0.01)
    finally:
        for proc, result_path, _dex_name in running:
            _cleanup_worker(proc, result_path, stop=True)

    return hit_count, shown


def search(
    store,
    find_type : str,
    value : str,
    class_name = None,
    fuzzy_class : bool = False,
    exact_member : bool = False,
    max_workers = None,
    progress_callback = None,
    result_callback = None,
):
    find_type, find = build_find_query(
        find_type,
        value,
        class_name,
        fuzzy_class,
        exact_member,
    )
    workers = get_effective_search_workers(store, max_workers)
    _debug_log(
        store.debug,
        "runtime",
        f"search request type={find_type} value={value!r} class={class_name!r} "
        f"fuzzy={fuzzy_class} workers={workers}",
    )
    # The app-owned ProcessPoolExecutor is faster when its import state is safe.
    # The isolated subprocess protocol is the fallback for hostile module state.
    if store.search_executor is not None:
        backend = "process"
        hit_count, shown = _search_with_process_pool(
            store,
            store.search_executor,
            workers,
            find_type,
            find,
            progress_callback,
            result_callback,
        )
    else:
        backend = "subprocess"
        hit_count, shown = _search_with_subprocess_pool(
            store,
            workers,
            find_type,
            find,
            progress_callback,
            result_callback,
        )

    return {
        "find_type": find_type,
        "query_value": value,
        "results": shown,
        "total_hits": hit_count,
        "workers": workers,
        "backend": backend,
    }
