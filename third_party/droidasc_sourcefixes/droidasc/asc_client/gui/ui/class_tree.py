import tkinter as tk
from tkinter import ttk

from droidasc.asc_client.gui.backend import dalvik_to_dot


_MAX_FILTER_CLASSES = 5000


def _package_label(package_path : str):
    if not package_path:
        return "(root)"
    return package_path.rsplit("/", 1)[-1]


def _class_label(dalvik_class : str):
    return dalvik_class.split("/")[-1].rstrip(";")


class ClassTree(ttk.Frame):
    def __init__(self, master, open_class, open_manifest):
        super().__init__(master, padding=8)
        self.open_class = open_class
        self.store = None
        self.filter_var = tk.StringVar()
        self.info_var = tk.StringVar(value="Classes")

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        ttk.Label(top, textvariable=self.info_var).grid(row=0, column=0, sticky="w")
        self.filter_entry = ttk.Entry(top, textvariable=self.filter_var)
        self.filter_entry.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        self.filter_entry.bind("<KeyRelease>", self._on_filter_changed)
        self.manifest_button = ttk.Button(top, text="Manifest", command=open_manifest)
        self.manifest_button.grid(row=0, column=2, sticky="e", padx=(8, 0))

        body = ttk.Frame(self)
        body.grid(row=1, column=0, sticky="nsew", pady=(8, 0))
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(body, show="tree")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewOpen>>", self._on_open)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        scrollbar = ttk.Scrollbar(body, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.config(yscrollcommand=scrollbar.set, selectmode="browse")

    def set_store(self, store):
        self.store = store
        self.refresh()

    def set_enabled(self, enabled : bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.filter_entry.config(state=state)
        self.manifest_button.config(state=state)

    def refresh(self):
        if self.store is None:
            return
        keyword = self.filter_var.get().strip()
        self.tree.delete(*self.tree.get_children())
        if keyword:
            # Rebuilding thousands of Treeview rows blocks Tk. The label makes
            # the hard UI cap visible when more matches may exist.
            matches = self.store.iter_filtered_classes(keyword, _MAX_FILTER_CLASSES)
            for dalvik_class in matches:
                self.tree.insert(
                    "",
                    tk.END,
                    iid=f"cls:{dalvik_class}",
                    text=dalvik_to_dot(dalvik_class),
                )
            if len(matches) >= _MAX_FILTER_CLASSES:
                self.info_var.set(f"Classes ({_MAX_FILTER_CLASSES}+ filtered)")
            else:
                self.info_var.set(f"Classes ({len(matches)} filtered)")
            return

        for package_path in self.store.iter_root_packages():
            self._insert_package("", package_path)
        for dalvik_class in self.store.iter_package_classes(""):
            self.tree.insert(
                "",
                tk.END,
                iid=f"cls:{dalvik_class}",
                text=_class_label(dalvik_class),
                values=("class",),
            )
        self.info_var.set(f"Packages / Classes ({len(self.store.class_names)})")

    def _insert_package(self, parent_id : str, package_path : str):
        item_id = f"pkg:{package_path}"
        if self.tree.exists(item_id):
            return item_id
        self.tree.insert(
            parent_id,
            tk.END,
            iid=item_id,
            text=_package_label(package_path),
            values=("pkg",),
        )
        # Treeview shows an expand arrow only when a node already has a child.
        # Replace this sentinel with real children on first expansion.
        self.tree.insert(item_id, tk.END, iid=f"{item_id}:stub", text="...")
        return item_id

    def _populate_package(self, package_path : str):
        item_id = f"pkg:{package_path}"
        if not self.tree.exists(item_id):
            return
        children = self.tree.get_children(item_id)
        if len(children) == 1 and children[0] == f"{item_id}:stub":
            self.tree.delete(children[0])
        elif children:
            # Existing real children mean this package was already populated.
            return

        for child in self.store.iter_child_packages(package_path):
            self._insert_package(item_id, child)
        for dalvik_class in self.store.iter_package_classes(package_path):
            self.tree.insert(
                item_id,
                tk.END,
                iid=f"cls:{dalvik_class}",
                text=_class_label(dalvik_class),
                values=("class",),
            )

    def select_class(self, dalvik_class : str):
        item_id = f"cls:{dalvik_class}"
        if not self.tree.exists(item_id):
            return
        self.tree.selection_set(item_id)
        self.tree.focus(item_id)
        self.tree.see(item_id)

    def _on_filter_changed(self, _event = None):
        self.refresh()

    def _on_open(self, _event = None):
        selection = self.tree.focus()
        if selection.startswith("pkg:"):
            self._populate_package(selection[4:])

    def _on_select(self, _event = None):
        selection = self.tree.selection()
        if not selection or not selection[0].startswith("cls:"):
            return
        self.open_class(selection[0][4:])
