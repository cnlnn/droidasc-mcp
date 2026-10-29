import tkinter as tk
from tkinter import ttk


class SearchDialog:
    def __init__(
        self,
        root,
        find_type : str,
        value : str,
        class_name,
        fuzzy_class : bool,
        open_result,
        apply_theme,
        on_destroy = None,
    ):
        self.find_type = find_type
        self.value = value
        self.class_name = class_name
        self.fuzzy_class = fuzzy_class
        self.open_result = open_result
        self.apply_window_theme = apply_theme
        self.on_destroy = on_destroy
        # all_rows is the immutable search result set; rows is the currently
        # displayed filtered projection addressed by Treeview iid.
        self.rows = []
        self.all_rows = []
        self.searching = True

        self.win = tk.Toplevel(root)
        self.win.title("Search")
        self.win.geometry("1280x760")
        self.win.transient(root)
        self.status_var = tk.StringVar(value="Searching...")
        self.progress_var = tk.IntVar(value=0)
        self.filter_var = tk.StringVar(value="")

        self._build_ui()
        self.win.protocol("WM_DELETE_WINDOW", self.win.destroy)
        self.win.bind("<Destroy>", self._on_destroy, add="+")

    def _build_ui(self):
        self.win.columnconfigure(0, weight=1)
        self.win.rowconfigure(1, weight=1)
        top = ttk.Frame(self.win, padding=8)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(2, weight=1)
        ttk.Label(top, textvariable=self.status_var).grid(row=0, column=0, sticky="w")
        ttk.Label(top, text="Filter").grid(row=0, column=1, sticky="e", padx=(12, 0))
        self.filter_entry = ttk.Entry(top, textvariable=self.filter_var)
        self.filter_entry.grid(row=0, column=2, sticky="ew", padx=(8, 0))
        self.filter_entry.bind("<KeyRelease>", self._on_filter_changed)
        self.filter_entry.config(state=tk.DISABLED)
        self.progress = ttk.Progressbar(
            top,
            mode="determinate",
            variable=self.progress_var,
            maximum=100,
        )
        self.progress.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(8, 0))

        body = ttk.Frame(self.win, padding=(8, 0, 8, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(
            body,
            columns=("dex", "class", "method", "matched"),
            show="headings",
        )
        self.tree.heading("dex", text="DEX")
        self.tree.heading("class", text="Class")
        self.tree.heading("method", text="Method")
        self.tree.heading("matched", text="Matched")
        self.tree.column("dex", width=120, stretch=False)
        self.tree.column("class", width=320, stretch=False)
        self.tree.column("method", width=260, stretch=False)
        self.tree.column("matched", width=560, stretch=True)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Double-Button-1>", self._open_selected)
        ybar = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.tree.yview)
        ybar.grid(row=0, column=1, sticky="ns")
        xbar = ttk.Scrollbar(body, orient=tk.HORIZONTAL, command=self.tree.xview)
        xbar.grid(row=1, column=0, sticky="ew")
        self.tree.config(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.apply_theme()

    def _on_destroy(self, event):
        if event.widget is self.win and self.on_destroy is not None:
            self.on_destroy(self)

    def apply_theme(self):
        if self.win.winfo_exists():
            self.apply_window_theme(self.win)

    def update_progress(self, done : int, total : int, hit_count : int):
        percent = int((done / total) * 100) if total else 0
        self.progress_var.set(percent)
        self.status_var.set(f"Searching {done}/{total} dex, hits={hit_count}")

    def finish(self, payload):
        if not self.rows and payload["results"]:
            self.append_results(payload["results"])
        self.searching = False
        self.filter_entry.config(state=tk.NORMAL)
        self.status_var.set(
            f"Done. hits={payload['total_hits']} workers={payload['workers']} "
            f"backend={payload['backend']}"
        )
        self.progress_var.set(100)

    def append_results(self, rows):
        if not rows:
            return
        self.all_rows.extend(rows)
        if self.searching:
            self._append_visible_rows(rows)
            return
        keyword = self.filter_var.get().strip().lower()
        if keyword:
            rows = [row for row in rows if self._row_matches_filter(row, keyword)]
        self._append_visible_rows(rows)

    def fail(self, message : str):
        self.searching = False
        self.filter_entry.config(state=tk.NORMAL)
        self.status_var.set(message)

    def _open_selected(self, _event = None):
        selection = self.tree.selection()
        if selection:
            self.open_result(self.rows[int(selection[0])], self.find_type)

    def _append_visible_rows(self, rows):
        if not rows:
            return
        start_idx = len(self.rows)
        self.rows.extend(rows)
        for offset, row in enumerate(rows):
            method_name = row["method_text"].split("->", 1)[1]
            self.tree.insert(
                "",
                tk.END,
                # Selection can recover the row in O(1) without storing a
                # second object mapping on every Treeview item.
                iid=str(start_idx + offset),
                values=(
                    row["dex_name"],
                    row["class_display"],
                    method_name,
                    row["matched_text"],
                ),
            )

    @staticmethod
    def _row_matches_filter(row, keyword : str):
        if not keyword:
            return True
        return (
            keyword in row["dex_name"].lower()
            or keyword in row["class_display"].lower()
            or keyword in row["method_text"].lower()
            or keyword in row["matched_text"].lower()
        )

    def _rebuild_filtered_rows(self):
        if self.searching:
            return
        keyword = self.filter_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        self.rows = []
        if not keyword:
            self._append_visible_rows(self.all_rows)
            return
        self._append_visible_rows([
            row for row in self.all_rows if self._row_matches_filter(row, keyword)
        ])

    def _on_filter_changed(self, _event = None):
        if not self.searching:
            self._rebuild_filtered_rows()


class SettingsDialog:
    def __init__(
        self,
        root,
        current_theme : str,
        theme_names,
        set_theme,
        apply_theme,
    ):
        self.set_theme = set_theme
        self.win = tk.Toplevel(root)
        self.win.title("Settings")
        self.win.transient(root)
        self.win.resizable(False, False)
        self.win.geometry(
            "+%d+%d" % (root.winfo_rootx() + 96, root.winfo_rooty() + 96)
        )
        self.theme_var = tk.StringVar(value=current_theme)

        body = ttk.Frame(self.win, padding=12)
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        ttk.Label(body, text="Theme").grid(row=0, column=0, sticky="w")
        combo = ttk.Combobox(
            body,
            textvariable=self.theme_var,
            values=theme_names,
            state="readonly",
            width=18,
        )
        combo.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        combo.bind("<<ComboboxSelected>>", self._on_theme_changed)
        actions = ttk.Frame(body)
        actions.grid(row=1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(actions, text="Close", command=self.win.destroy).grid(
            row=0, column=0, sticky="e"
        )
        apply_theme(self.win)

    def _on_theme_changed(self, _event = None):
        self.set_theme(self.theme_var.get())


class LineCommentDialog:
    def __init__(
        self,
        root,
        line_no : int,
        source_line : str,
        comment : str,
        save_comment,
        apply_theme,
    ):
        self.save_comment = save_comment
        self.win = tk.Toplevel(root)
        self.win.title(f"Comment line {line_no}")
        self.win.transient(root)
        self.win.resizable(True, False)
        apply_theme(self.win)
        _place_dialog(root, self.win, 640, 118, 420)

        frame = ttk.Frame(self.win, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")
        self.win.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text=f"Line {line_no}").grid(row=0, column=0, sticky="w")
        ttk.Label(frame, text=_ellipsize(source_line.strip(), 92)).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )
        self.comment_var = tk.StringVar(value=comment)
        ttk.Label(frame, text="Comment").grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.entry = ttk.Entry(frame, textvariable=self.comment_var)
        self.entry.grid(row=1, column=1, sticky="ew", padx=(8, 0), pady=(8, 0))
        actions = ttk.Frame(frame)
        actions.grid(row=2, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(actions, text="Save", command=self._save).grid(
            row=0, column=0, sticky="e"
        )
        ttk.Button(actions, text="Delete", command=self._delete).grid(
            row=0, column=1, sticky="e", padx=(6, 0)
        )
        ttk.Button(actions, text="Cancel", command=self.win.destroy).grid(
            row=0, column=2, sticky="e", padx=(6, 0)
        )
        self.entry.bind("<Return>", self._save)
        self.entry.bind("<Escape>", lambda _event: self.win.destroy())
        self.entry.focus_set()
        self.entry.selection_range(0, tk.END)

    def _save(self, _event = None):
        self.save_comment(self.comment_var.get().strip())
        self.win.destroy()
        return "break"

    def _delete(self):
        self.save_comment("")
        self.win.destroy()


class RenameDialog:
    def __init__(self, root, old_name : str, rename, apply_theme):
        self.rename = rename
        self.win = tk.Toplevel(root)
        self.win.title(f"Rename {old_name}")
        self.win.transient(root)
        self.win.resizable(True, False)
        apply_theme(self.win)
        _place_dialog(root, self.win, 520, 110, 360)

        frame = ttk.Frame(self.win, padding=10)
        frame.grid(row=0, column=0, sticky="nsew")
        self.win.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text="Rename").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar(value=old_name)
        self.entry = ttk.Entry(frame, textvariable=self.name_var)
        self.entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        actions = ttk.Frame(frame)
        actions.grid(row=1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(actions, text="Rename", command=self._save).grid(
            row=0, column=0, sticky="e"
        )
        ttk.Button(actions, text="Cancel", command=self.win.destroy).grid(
            row=0, column=1, sticky="e", padx=(6, 0)
        )
        self.entry.bind("<Return>", self._save)
        self.entry.bind("<Escape>", lambda _event: self.win.destroy())
        self.entry.focus_set()
        self.entry.selection_range(0, tk.END)

    def _save(self, _event = None):
        if self.rename(self.name_var.get().strip()):
            self.win.destroy()
        return "break"


def _place_dialog(root, win, width : int, height : int, min_width : int):
    x = root.winfo_rootx() + max(80, (root.winfo_width() - width) // 2)
    y = root.winfo_rooty() + 160
    win.geometry(f"{width}x{height}+{x}+{y}")
    win.minsize(min_width, height)


def _ellipsize(text : str, limit : int):
    if len(text) <= limit:
        return text
    return text[:max(0, limit - 3)] + "..."
