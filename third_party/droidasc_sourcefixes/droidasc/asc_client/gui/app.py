import os
import queue
import threading
import time
import traceback
import tkinter as tk
from tkinter import ttk

from droidasc.asc_client.gui.backend import GuiDexStore, is_member_search
from droidasc.asc_client.gui.editor.controller import EditorController
from droidasc.asc_client.gui.editor.view import EditorView
from droidasc.asc_client.gui.ui.class_tree import ClassTree
from droidasc.asc_client.gui.ui.dialogs import SearchDialog, SettingsDialog
from droidasc.asc_client.gui.ui.tab_bar import EditorTabBar
from droidasc.asc_client.gui.ui.theme import ThemeManager
from droidasc.asc_client.manifest_handler import get_manifest_xml


def _debug_log(enabled : bool, scope : str, msg : str):
    if not enabled:
        return
    tid = threading.get_ident() & 0xFFFF
    now = time.perf_counter()
    print(f"[GUI DEBUG] [{scope}] [T{tid:04x}] {now:.6f} {msg}")


class AscGuiApp:
    def __init__(self, root, apk_path : str, max_workers : int = 8, debug : bool = False, search_executor = None):
        self.root = root
        self.apk_path = apk_path
        self.max_workers = max_workers
        self.debug = debug
        self.search_executor = search_executor

        self.store = None
        # Background threads/process callbacks only enqueue plain data. The Tk
        # thread drains this queue and owns every widget mutation.
        self.events = queue.Queue()
        self.search_dialog = None
        self.search_inflight = False
        self.theme_manager = ThemeManager(root, "light")
        self.theme_name_var = tk.StringVar(value=self.theme_manager.name)
        self.theme = self.theme_manager.theme

        self.status_var = tk.StringVar(value="Loading APK...")
        self.search_type_var = tk.StringVar(value="string refs")
        self.search_value_var = tk.StringVar()
        self.search_class_var = tk.StringVar()
        self.fuzzy_class_var = tk.BooleanVar(value=False)

        self._build_ui()
        self.editor.bind_shortcuts()
        self._set_controls_enabled(False)
        self._start_load()
        self.root.after(50, self._drain_events)
        _debug_log(
            self.debug,
            "app",
            f"init apk={self.apk_path} workers={self.max_workers} executor={id(self.search_executor)}",
        )

    def _ensure_search_executor(self):
        if self.search_executor is not None:
            return self.search_executor
        from concurrent.futures import ProcessPoolExecutor

        self.search_executor = ProcessPoolExecutor(max_workers=self.max_workers)
        if self.store is not None:
            self.store.search_executor = self.search_executor
        _debug_log(self.debug, "app", f"create search executor workers={self.max_workers}")
        return self.search_executor

    def _dispose_search_executor(self):
        executor = self.search_executor
        self.search_executor = None
        if self.store is not None:
            self.store.search_executor = None
        if executor is None:
            return
        _debug_log(self.debug, "app", "dispose search executor")
        # Do not block Tk on child shutdown. Completed search workers have
        # already returned; this only releases the pool lifecycle.
        executor.shutdown(wait=False, cancel_futures=False)

    def _open_settings(self):
        SettingsDialog(
            self.root,
            self.theme_name_var.get(),
            self.theme_manager.names(),
            self.set_theme,
            self.apply_theme_to_window,
        )

    def set_theme(self, name : str):
        self.theme_manager.set_theme(name)
        self.theme_name_var.set(self.theme_manager.name)
        self.theme = self.theme_manager.theme
        self.apply_theme()

    def apply_theme_to_window(self, win):
        self.theme_manager.apply_toplevel(win)

    def apply_theme(self):
        self.theme = self.theme_manager.theme
        self.theme_manager.apply_root(self.root)
        if hasattr(self, "editor_view"):
            self.editor_view.configure_tags(self.theme)
        if hasattr(self, "editor_tab_bar"):
            self.editor_tab_bar.apply_theme()
        if self.search_dialog is not None and self.search_dialog.win.winfo_exists():
            self.search_dialog.apply_theme()

    def _build_ui(self):
        self.root.title(f"ASC GUI Auth: MG1937 - {os.path.basename(self.apk_path)}")
        self.root.geometry("1500x920")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        self.theme_manager.apply_root(self.root)

        top = ttk.Frame(self.root, padding=8)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="APK").grid(row=0, column=0, sticky="w")
        ttk.Label(top, text=self.apk_path).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(top, textvariable=self.status_var).grid(row=0, column=2, sticky="e", padx=(12, 0))

        body = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
        body.grid(row=1, column=0, sticky="nsew")

        right = ttk.Frame(body, padding=8)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        self.class_browser = ClassTree(
            body,
            open_class=lambda dalvik_class: self.editor.open_class(dalvik_class),
            open_manifest=self._open_manifest,
        )
        body.add(self.class_browser, weight=1)
        body.add(right, weight=4)

        controls = ttk.Frame(right)
        controls.grid(row=0, column=0, sticky="ew")
        for idx in range(7):
            controls.columnconfigure(idx, weight=0)
        controls.columnconfigure(2, weight=1)

        ttk.Label(controls, text="Search").grid(row=0, column=0, sticky="w")
        self.search_type_box = ttk.Combobox(
            controls,
            textvariable=self.search_type_var,
            values=("string refs", "type refs", "method refs", "field refs", "method", "field"),
            state="readonly",
            width=12,
        )
        self.search_type_box.grid(row=0, column=1, sticky="w", padx=(8, 0))
        self.search_type_box.bind("<<ComboboxSelected>>", self._on_search_type_changed)
        self.search_type_box.bind("<Return>", self._on_search_enter)

        self.search_value_entry = ttk.Entry(controls, textvariable=self.search_value_var)
        self.search_value_entry.grid(row=0, column=2, sticky="ew", padx=(8, 0))
        self.search_value_entry.bind("<Return>", self._on_search_enter)

        ttk.Label(controls, text="Class").grid(row=0, column=3, sticky="w", padx=(8, 0))
        self.search_class_entry = ttk.Entry(controls, textvariable=self.search_class_var, width=30)
        self.search_class_entry.grid(row=0, column=4, sticky="w", padx=(4, 0))
        self.search_class_entry.bind("<Return>", self._on_search_enter)

        self.fuzzy_class_check = ttk.Checkbutton(controls, text="Fuzzy class", variable=self.fuzzy_class_var)
        self.fuzzy_class_check.grid(row=0, column=5, sticky="w", padx=(8, 0))

        self.search_button = ttk.Button(controls, text="Search", command=self._start_search)
        self.search_button.grid(row=0, column=6, sticky="e", padx=(8, 0))

        source_frame = ttk.Frame(right)
        source_frame.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        source_frame.columnconfigure(0, weight=1)
        source_frame.rowconfigure(1, weight=1)

        self.editor_view = EditorView(
            source_frame,
            self.root,
            self.events.put,
            self.theme_manager,
        )
        self.editor = EditorController(
            self.root,
            self.editor_view,
            get_store=lambda: self.store,
            emit_event=self.events.put,
            set_status=self.status_var.set,
            select_class=self.class_browser.select_class,
            start_reference_search=self._start_reference_search,
            apply_theme_to_window=self.apply_theme_to_window,
            debug=self.debug,
            debug_log=lambda scope, msg: _debug_log(self.debug, scope, msg),
        )
        self.editor_tab_bar = EditorTabBar(
            source_frame,
            get_tabs=lambda: self.editor.tabs,
            get_active_index=lambda: self.editor.active_tab_idx,
            activate_tab=self.editor.activate_tab,
            close_tab=self.editor.close_tab,
            clear_tabs=self.editor.clear_tabs,
            open_settings=self._open_settings,
            get_theme=lambda: self.theme,
            apply_theme_to_window=self.apply_theme_to_window,
            apply_listbox_theme=self.theme_manager.apply_listbox,
        )
        self.editor.set_tab_bar(self.editor_tab_bar)
        self.editor_tab_bar.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.editor_view.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.editor_view.configure_tags(self.theme)
        self.apply_theme()
        self.editor_view.show_empty()
        self._on_search_type_changed()

    def _set_controls_enabled(self, enabled : bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.class_browser.set_enabled(enabled)
        self.search_button.config(state=state)
        self.search_value_entry.config(state=state)
        self.search_type_box.config(state="readonly" if enabled else tk.DISABLED)
        self.search_class_entry.config(state=state)
        self.fuzzy_class_check.config(state=state)

    def _drain_events(self):
        # This callback always runs on Tk's event loop, making it the single
        # synchronization point between background work and widgets.
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            self._handle_event(event)
        self.root.after(50, self._drain_events)

    def _handle_event(self, event):
        kind = event[0]
        dialog = self.search_dialog
        if kind.startswith("search_") and dialog is not None:
            # Search work outlives its optional result window. Continue updating
            # global state, but never send events to a destroyed Toplevel.
            try:
                if not dialog.win.winfo_exists():
                    dialog = None
                    self.search_dialog = None
            except tk.TclError:
                dialog = None
                self.search_dialog = None
        if kind == "load_progress":
            _kind, done, total, dex_name, class_count = event
            self.status_var.set(f"Indexing {done}/{total} dex, classes={class_count}, last={dex_name}")
            return
        if kind == "load_done":
            self.store = event[1]
            self._set_controls_enabled(True)
            self.class_browser.set_store(self.store)
            self.status_var.set(f"Ready. dex={len(self.store.entries)} classes={len(self.store.class_names)}")
            return
        if kind == "load_error":
            self.status_var.set(event[1])
            return
        if kind == "source_done":
            _kind, dalvik_class, dex_name, source, member_references = event
            self.editor.finish_open_tab(dalvik_class, dex_name, source, member_references)
            return
        if kind == "text_tab_done":
            _kind, tab_id, title, source, dex_name = event
            self.editor.open_text_tab(tab_id, title, source, dex_name=dex_name)
            self.status_var.set(f"Opened {title}")
            return
        if kind == "highlight_ready":
            _kind, generation, spans = event
            self.editor_view.apply_highlight_spans(generation, spans)
            return
        if kind == "source_error":
            _kind, dalvik_class, message = event
            self.editor.fail_open_tab(dalvik_class, message)
            return
        if kind == "search_progress":
            _kind, done, total, hit_count = event
            if dialog is not None:
                dialog.update_progress(done, total, hit_count)
            self.status_var.set(f"Searching {done}/{total} dex, hits={hit_count}")
            return
        if kind == "search_batch":
            _kind, rows, done, total, hit_count = event
            if dialog is not None:
                dialog.append_results(rows)
                dialog.update_progress(done, total, hit_count)
            self.status_var.set(f"Searching {done}/{total} dex, hits={hit_count}")
            return
        if kind == "search_done":
            payload = event[1]
            self.search_inflight = False
            self.search_button.config(state=tk.NORMAL)
            if dialog is not None:
                dialog.finish(payload)
            self.status_var.set(
                f"Search done. hits={payload['total_hits']} workers={payload['workers']} backend={payload['backend']}"
            )
            return
        if kind == "search_error":
            self.search_inflight = False
            self.search_button.config(state=tk.NORMAL)
            if dialog is not None:
                dialog.fail(event[1])
            self.status_var.set(event[1])
            return

    def _start_load(self):
        def worker():
            try:
                _debug_log(self.debug, "app", "load worker start")
                store = GuiDexStore(
                    self.apk_path,
                    self.max_workers,
                    self.debug,
                    search_executor=self.search_executor,
                )
                store.load(
                    # Progress callbacks run on the loader thread and therefore
                    # must be converted to main-thread events.
                    lambda done, total, dex_name, class_count: self.events.put(
                        ("load_progress", done, total, dex_name, class_count)
                    )
                )
                self.events.put(("load_done", store))
                _debug_log(self.debug, "app", "load worker done")
            except Exception as e:
                if self.debug:
                    traceback.print_exc()
                self.events.put(("load_error", f"Load failed: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _open_manifest(self):
        self.status_var.set("Parsing AndroidManifest.xml...")

        def worker():
            try:
                xml = get_manifest_xml(self.apk_path, pretty=True)
                self.events.put(("text_tab_done", "manifest:AndroidManifest.xml", "AndroidManifest.xml", xml, "manifest"))
            except Exception as e:
                if self.debug:
                    traceback.print_exc()
                self.events.put(("source_error", "manifest:AndroidManifest.xml", f"Manifest parse failed: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_search_type_changed(self, _event = None):
        find_type = self.search_type_var.get()
        need_class = find_type in ("method refs", "field refs")
        class_state = tk.NORMAL if need_class and self.store is not None else tk.DISABLED
        fuzzy_state = tk.NORMAL if need_class and self.store is not None else tk.DISABLED
        self.search_class_entry.config(state=class_state)
        self.fuzzy_class_check.config(state=fuzzy_state)

    def _on_search_enter(self, _event = None):
        self._start_search()
        return "break"

    def open_search_result(self, row, find_type : str):
        self.editor.open_search_result(row, find_type)

    def _start_reference_search(self, member_type : str, member_name : str, class_name : str):
        self.search_type_var.set(f"{member_type} refs")
        self.search_value_var.set(member_name)
        self.search_class_var.set(class_name)
        self.fuzzy_class_var.set(False)
        self._on_search_type_changed()
        self._start_search(exact_member=True)

    def _start_search(self, exact_member : bool = False):
        if self.store is None:
            return
        if self.search_inflight:
            self.status_var.set("Search is already running")
            return

        find_type = self.search_type_var.get()
        value = self.search_value_var.get().strip()
        class_name = self.search_class_var.get().strip()
        fuzzy_class = self.fuzzy_class_var.get()
        if find_type in ("string refs", "type refs", "method", "field") and not value:
            self.status_var.set("Search value is empty")
            return
        if find_type in ("method refs", "field refs") and not value and not class_name:
            self.status_var.set(f"{find_type} search needs class or name")
            return

        self.search_dialog = SearchDialog(
            self.root,
            find_type=find_type,
            value=value,
            class_name=class_name or None,
            fuzzy_class=fuzzy_class,
            open_result=self.open_search_result,
            apply_theme=self.apply_theme_to_window,
            on_destroy=self._on_search_dialog_destroyed,
        )
        self.search_inflight = True
        self.search_button.config(state=tk.DISABLED)
        _debug_log(
            self.debug,
            "app",
            f"search request type={find_type} value={value!r} class={class_name!r} fuzzy={fuzzy_class}",
        )

        def worker():
            try:
                _debug_log(self.debug, "app", "search worker start")
                if is_member_search(find_type):
                    # Declaration listing uses already-loaded locator indexes;
                    # xrefs below require isolated process workers.
                    payload = self.store.search_members(
                        find_type=find_type,
                        value=value,
                    )
                    self.events.put(("search_batch", payload["results"], 1, 1, payload["total_hits"]))
                    self.events.put(("search_done", payload))
                    _debug_log(
                        self.debug,
                        "app",
                        f"member search worker done hits={payload['total_hits']}",
                    )
                    return

                self._ensure_search_executor()
                payload = self.store.search(
                    find_type=find_type,
                    value=value,
                    class_name=class_name or None,
                    fuzzy_class=fuzzy_class,
                    exact_member=exact_member,
                    max_workers=self.max_workers,
                    progress_callback=lambda done, total, hit_count: self.events.put(
                        ("search_progress", done, total, hit_count)
                    ),
                    result_callback=lambda rows, done, total, hit_count: self.events.put(
                        ("search_batch", rows, done, total, hit_count)
                    ),
                )
                self.events.put(("search_done", payload))
                _debug_log(
                    self.debug,
                    "app",
                    f"search worker done hits={payload['total_hits']} backend={payload['backend']}",
                )
            except Exception as e:
                if self.debug:
                    traceback.print_exc()
                self.events.put(("search_error", f"Search failed: {e}"))
            finally:
                # A fresh pool keeps later searches away from module state which
                # a decompile may have loaded or replaced in this process.
                self._dispose_search_executor()

        threading.Thread(target=worker, daemon=True).start()

    def _on_search_dialog_destroyed(self, dialog):
        if self.search_dialog is dialog:
            self.search_dialog = None


def launch_gui(apk_path : str, max_workers : int = 20, debug : bool = False):
    root = tk.Tk()

    _debug_log(debug, "app", f"launch gui apk={apk_path} workers={max_workers}")
    app = AscGuiApp(root, apk_path, max_workers=max_workers, debug=debug, search_executor=None)
    closed = False

    def on_close():
        nonlocal closed
        # protocol callback and mainloop finally can both reach this function.
        if closed:
            return
        closed = True
        _debug_log(debug, "app", "shutdown gui")
        app._dispose_search_executor()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    try:
        root.mainloop()
    finally:
        on_close()
