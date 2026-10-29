import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from droidasc.asc_client.apk.loader import _inflate_dex, _parse_cd_dex_entries
from droidasc.asc_client.dex_container import iter_logical_dex_buffers
from droidasc.asc_core.findrefs.findrefs_manager import FindRefManager
from droidasc.asc_core.utils.tinydex import DEX

from .search import (
    _GUI_MP_LOCK,
    _debug_log,
    _multiprocessing_state,
    _restore_sys_modules,
    _snapshot_sys_modules,
    dalvik_to_dot,
    get_effective_search_workers,
    search,
    search_members,
)


class GuiDexStore:
    def __init__(
        self,
        apk_path : str,
        max_workers : int = 20,
        debug : bool = False,
        search_executor = None,
    ):
        self.apk_path = apk_path
        self.max_workers = max_workers
        self.debug = debug
        self.search_executor = search_executor

        self.entries = []
        self.dex_buffers = {}
        self.class_to_dex = {}
        self.class_names = []
        self.package_children = {}
        self.package_classes = {}
        self.findref_managers = {}
        self.source_cache = {}
        self._source_lock = threading.Lock()

    def _open_apk(self):
        import mmap

        fp = open(self.apk_path, "rb")
        mm = mmap.mmap(fp.fileno(), 0, access=mmap.ACCESS_READ)
        return fp, mm

    def _load_worker_count(self, total : int):
        workers = self.max_workers
        if workers is None or workers <= 0:
            workers = os.cpu_count() or 4
        return min(total, workers)

    def load(self, progress_callback = None):
        fp, mm = self._open_apk()
        try:
            entries = _parse_cd_dex_entries(mm)
            entries.sort(key=lambda item: item[2])
            self.entries = entries
            total = len(entries)
            _debug_log(
                self.debug,
                "runtime",
                f"load start apk={self.apk_path} dex={total}",
            )
            if total == 0:
                self.class_names = []
                return

            def load_entry(entry):
                # mmap is read-only and each task copies/decompresses only its
                # own ZIP range, so DEX entries can load concurrently.
                data = _inflate_dex(mm, entry)
                logical = []
                # One physical DEX 041 entry may expose several logical DEXes;
                # index each one under its synthetic stable name.
                for dex_name, dex_buf in iter_logical_dex_buffers(entry[0], data):
                    dex = DEX.parse(memoryview(dex_buf), dex_name)
                    classes = [
                        dex.classes[class_idx].fullname
                        for class_idx in range(len(dex.classes))
                    ]
                    logical.append((dex_name, dex_buf, dex, classes))
                return entry, logical

            done = 0
            class_count = 0
            workers = self._load_worker_count(total)
            with ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [executor.submit(load_entry, entry) for entry in entries]
                for future in as_completed(futures):
                    entry, logical = future.result()
                    for dex_name, dex_buf, dex, classes in logical:
                        self.dex_buffers[dex_name] = dex_buf
                        self.findref_managers[dex_name] = FindRefManager(
                            dex,
                            self.debug,
                        )
                        for class_name in classes:
                            self.class_to_dex.setdefault(class_name, dex_name)
                        class_count += len(classes)
                    done += 1
                    if progress_callback is not None:
                        progress_callback(done, total, entry[0], class_count)

            self.class_names = sorted(self.class_to_dex)
            self._build_package_index()
            _debug_log(
                self.debug,
                "runtime",
                f"load done dex={len(self.entries)} classes={len(self.class_names)}",
            )
        finally:
            mm.close()
            fp.close()

    def _build_package_index(self):
        package_children = {"": set()}
        package_classes = {}

        # Build both adjacency and class buckets once. Tree expansion can then
        # stay lazy without rescanning every class for each opened package.
        for class_name in self.class_names:
            if class_name.startswith("L") and class_name.endswith(";"):
                body = class_name[1:-1]
            else:
                body = class_name
            parts = body.split("/")
            pkg_path = ""

            for part in parts[:-1]:
                next_path = f"{pkg_path}/{part}" if pkg_path else part
                package_children.setdefault(pkg_path, set()).add(next_path)
                package_children.setdefault(next_path, set())
                pkg_path = next_path

            package_classes.setdefault(pkg_path, []).append(class_name)

        self.package_children = {
            pkg: sorted(children, key=lambda item: item.lower())
            for pkg, children in package_children.items()
        }
        self.package_classes = {}
        for pkg_path, classes in package_classes.items():
            classes.sort(
                key=lambda item: item.split("/")[-1].rstrip(";").lower()
            )
            self.package_classes[pkg_path] = classes

    def iter_root_packages(self):
        return self.package_children.get("", [])

    def iter_child_packages(self, pkg_path : str):
        return self.package_children.get(pkg_path, [])

    def iter_package_classes(self, pkg_path : str):
        return self.package_classes.get(pkg_path, [])

    def iter_filtered_classes(self, keyword : str, limit : int):
        keyword = (keyword or "").strip().lower()
        if not keyword:
            return []

        ret = []
        for class_name in self.class_names:
            if keyword not in dalvik_to_dot(class_name).lower():
                continue
            ret.append(class_name)
            if len(ret) >= limit:
                break
        return ret

    def get_source(self, dalvik_class : str):
        dex_name, source, _references = self.get_source_with_metadata(dalvik_class)
        return dex_name, source

    def get_source_with_metadata(self, dalvik_class : str):
        # Cache lookup and publication are protected separately from the slow
        # decompile so unrelated cached classes are never blocked.
        with self._source_lock:
            old = self.source_cache.get(dalvik_class)
            if old is not None:
                _debug_log(
                    self.debug,
                    "runtime",
                    f"source cache hit class={dalvik_class}",
                )
                return old

        dex_name = self.class_to_dex.get(dalvik_class)
        if dex_name is None:
            raise ValueError(f"class not indexed: {dalvik_class}")

        dex_buf = self.dex_buffers[dex_name]
        _debug_log(
            self.debug,
            "runtime",
            f"source start class={dalvik_class} dex={dex_name} "
            f"{_multiprocessing_state()}",
        )
        from droidasc.asc_client.asc_handler import AscHandler

        # AscHandler imports optional decompiler dependencies which can replace
        # sys.modules entries with stubs. Process spawning must not observe that
        # transient graph, hence the shared lock and exact snapshot restoration.
        with _GUI_MP_LOCK:
            snapshot = _snapshot_sys_modules()
            try:
                source, references = AscHandler(
                    self.debug
                ).getclass_with_metadata(dex_buf, dalvik_class)
            finally:
                _restore_sys_modules(snapshot)
        ret = (dex_name, source, references)
        with self._source_lock:
            self.source_cache[dalvik_class] = ret
        _debug_log(
            self.debug,
            "runtime",
            f"source done class={dalvik_class} dex={dex_name} "
            f"{_multiprocessing_state()}",
        )
        return ret

    def search_members(self, find_type : str, value : str, limit : int = 5000):
        return search_members(self, find_type, value, limit)

    def get_effective_search_workers(self, requested = None):
        return get_effective_search_workers(self, requested)

    def search(
        self,
        find_type : str,
        value : str,
        class_name = None,
        fuzzy_class : bool = False,
        exact_member : bool = False,
        max_workers = None,
        progress_callback = None,
        result_callback = None,
    ):
        return search(
            self,
            find_type,
            value,
            class_name,
            fuzzy_class,
            exact_member,
            max_workers,
            progress_callback,
            result_callback,
        )
