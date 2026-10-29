import threading
import tkinter as tk
from tkinter import ttk

from droidasc.asc_client.gui.backend import dalvik_to_dot
from droidasc.asc_client.gui.editor.source import (
    find_method_range,
    identifier_occurrences_in_range,
    index_to_offset,
    java_highlight_spans,
    linkable_member_spans,
    member_reference_at_offset,
    offset_spans_to_indexes,
    token_at_offset,
)


_COMMENT_GAP = "  "
_SOURCE_TAGS = (
    "java_keyword", "java_comment", "java_string", "java_annotation", "manifest_string",
)
_TRANSIENT_TAGS = (
    "user_comment", "active_line", "symbol_match", "symbol_current",
    "find_match", "find_current", "member_link",
)


class EditorView(ttk.Frame):
    def __init__(self, master, root, emit_event, theme_manager):
        super().__init__(master)
        self.root = root
        self.emit_event = emit_event
        self.theme_manager = theme_manager
        self.find_var = tk.StringVar()
        self.find_status_var = tk.StringVar(value="")
        self._last_find_text = ""
        self._highlight_generation = 0
        self._highlight_apply_batch = 400
        self._highlight_apply_job = None
        self.member_links_visible = False

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_find_bar()

        self.text = tk.Text(self, wrap="none")
        self.text.grid(row=1, column=0, sticky="nsew")
        ybar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.text.yview)
        ybar.grid(row=1, column=1, sticky="ns")
        xbar = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.text.xview)
        xbar.grid(row=2, column=0, sticky="ew")
        self.text.config(yscrollcommand=ybar.set, xscrollcommand=xbar.set)
        self.find_frame.grid_remove()

    def _build_find_bar(self):
        self.find_frame = ttk.Frame(self)
        self.find_frame.grid(row=0, column=0, sticky="ew", pady=(6, 6))
        self.find_frame.columnconfigure(1, weight=1)
        ttk.Label(self.find_frame, text="Find").grid(row=0, column=0, sticky="w")
        self.find_entry = ttk.Entry(self.find_frame, textvariable=self.find_var)
        self.find_entry.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        self.find_entry.bind("<Return>", self._on_find_return)
        self.find_entry.bind("<KP_Enter>", self._on_find_return)
        self.find_entry.bind("<Shift-Return>", self.find_prev)
        self.find_entry.bind("<Shift-KP_Enter>", self.find_prev)
        self.find_entry.bind("<Escape>", self.hide_find)
        self.find_entry.bind("<KeyRelease>", self._on_find_changed)
        ttk.Button(self.find_frame, text="Next", command=self.find_next).grid(
            row=0, column=2, sticky="e"
        )
        ttk.Button(self.find_frame, text="Prev", command=self.find_prev).grid(
            row=0, column=3, sticky="e", padx=(6, 0)
        )
        ttk.Button(self.find_frame, text="Close", command=self.hide_find).grid(
            row=0, column=4, sticky="e", padx=(6, 0)
        )
        ttk.Label(self.find_frame, textvariable=self.find_status_var).grid(
            row=0, column=5, sticky="e", padx=(12, 0)
        )

    def configure_tags(self, theme):
        self.theme_manager.apply_text(self.text)
        self.text.tag_configure("java_keyword", foreground=theme["java_keyword"])
        self.text.tag_configure("java_comment", foreground=theme["java_comment"])
        self.text.tag_configure("java_string", foreground=theme["java_string"])
        self.text.tag_configure("java_annotation", foreground=theme["java_annotation"])
        self.text.tag_configure("manifest_string", foreground=theme["java_string"])
        self.text.tag_configure(
            "user_comment",
            foreground=theme["java_comment"],
            font=("Consolas", 10, "italic"),
        )
        self.text.tag_configure("active_line", background=theme["active_line"])
        self.text.tag_configure("symbol_match", background=theme["symbol_match"])
        self.text.tag_configure("symbol_current", background=theme["symbol_current"])
        self.text.tag_configure(
            "find_match",
            background=theme["find_match"],
            foreground=theme["editor_fg"],
        )
        self.text.tag_configure(
            "find_current",
            background=theme["find_current"],
            foreground=theme["editor_fg"],
        )
        self.text.tag_configure(
            "member_link",
            foreground=theme["accent"],
            underline=True,
        )

    def bind_find_shortcuts(self):
        self.root.bind("<Control-f>", self.show_find)
        self.root.bind("<Control-F>", self.show_find)
        self.text.bind("<Escape>", self.hide_find)

    def remember(self, tab):
        if tab is None:
            return
        try:
            tab.yview = self.text.yview()
            tab.xview = self.text.xview()
            tab.insert_index = self.text.index("insert")
        except tk.TclError:
            pass

    def set_text(self, text : str, reset_view : bool = True):
        self.text.config(state=tk.NORMAL)
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", text)
        if reset_view:
            self.text.mark_set("insert", "1.0")
            self.text.xview_moveto(0.0)
            self.text.yview_moveto(0.0)

    def render_source(self, tab):
        source = tab.edited_source or tab.source
        if not tab.comments:
            tab.rendered_member_references = list(tab.member_references)
            return source, []

        out = []
        comment_spans = []
        insertions = []
        offset = 0
        source_offset = 0
        lines = source.splitlines(keepends=True)
        # User comments are presentation-only line suffixes. Record each
        # insertion so source metadata can be translated to rendered offsets.
        for line_no, line in enumerate(lines, 1):
            newline = ""
            body = line
            if line.endswith("\r\n"):
                body = line[:-2]
                newline = "\r\n"
            elif line.endswith("\n"):
                body = line[:-1]
                newline = "\n"

            comment = tab.comments.get(line_no)
            if not comment:
                rendered = line
            else:
                comment_text = f"{_COMMENT_GAP}// {comment}"
                insertions.append((source_offset + len(body), len(comment_text)))
                start = offset + len(body) + len(_COMMENT_GAP)
                rendered = f"{body}{comment_text}{newline}"
                comment_spans.append((start, start + len(comment_text) - len(_COMMENT_GAP)))
            out.append(rendered)
            offset += len(rendered)
            source_offset += len(line)

        if not lines and tab.comments:
            rendered = f"// {tab.comments.get(1, '')}"
            return rendered, [(0, len(rendered))]

        def shift_start(point):
            # A reference starting exactly at an insertion moves after it.
            return point + sum(length for position, length in insertions if position <= point)

        def shift_end(point):
            # A reference ending exactly at an insertion remains before it.
            return point + sum(length for position, length in insertions if position < point)

        tab.rendered_member_references = [
            (shift_start(item[0]), shift_end(item[1]), *item[2:])
            for item in tab.member_references
        ]
        return "".join(out), comment_spans

    def show_empty(self):
        # Incrementing invalidates highlight results still queued by old tabs.
        self._highlight_generation += 1
        self._clear_tags()
        self.set_text("Open a class from the package tree or search results.", reset_view=True)
        self.find_status_var.set("")

    def show_tab(self, tab, available_classes=()):
        self._highlight_generation += 1
        self._clear_tags()
        if tab.loading:
            self.set_text(f"Decompiling {dalvik_to_dot(tab.dalvik_class)}...", reset_view=True)
            return
        if tab.error:
            self.set_text(tab.error, reset_view=True)
            return

        rendered, comment_spans = self.render_source(tab)
        self.set_text(rendered, reset_view=False)
        try:
            self.text.mark_set("insert", tab.insert_index)
            self.text.xview_moveto(tab.xview[0])
            self.text.yview_moveto(tab.yview[0])
        except tk.TclError:
            self.text.mark_set("insert", "1.0")
        for start, end in comment_spans:
            self.tag_range("user_comment", start, end)
        if tab.kind == "class":
            self._start_async_highlight(rendered)
        else:
            self._highlight_quoted_strings(rendered)
        self.refresh_find_marks(reset_cursor=False)
        self.highlight_active_line()
        if self.member_links_visible:
            self.member_links_visible = False
            self.show_member_links(tab, available_classes)

    def _clear_tags(self):
        for tag_name in _SOURCE_TAGS + _TRANSIENT_TAGS:
            self.text.tag_remove(tag_name, "1.0", tk.END)

    @staticmethod
    def line_from_index(index : str):
        try:
            return int(str(index).split(".", 1)[0])
        except (TypeError, ValueError):
            return None

    def highlight_active_line(self):
        self.text.tag_remove("active_line", "1.0", tk.END)
        try:
            line_no = self.line_from_index(self.text.index("insert"))
        except tk.TclError:
            line_no = None
        if line_no is None:
            return
        self.text.tag_add("active_line", f"{line_no}.0", f"{line_no}.end+1c")
        # Syntax and selection colors must remain visible over the line tint.
        self.text.tag_lower("active_line")

    def highlight_related_identifier(self, tab, index : str):
        self.text.tag_remove("symbol_match", "1.0", tk.END)
        self.text.tag_remove("symbol_current", "1.0", tk.END)
        if tab is None or tab.kind != "class" or tab.loading or tab.error:
            return
        source = tab.edited_source or tab.source
        if tab.comments:
            source, _comment_spans = self.render_source(tab)
        if not source:
            return
        token = token_at_offset(source, index_to_offset(source, index))
        if token is None:
            return
        start, end, name = token
        method_range = find_method_range(source, start) or (0, len(source))
        spans = identifier_occurrences_in_range(source, method_range[0], method_range[1], name)
        if len(spans) <= 1:
            return
        for span_start, span_end in spans:
            tag = "symbol_current" if (span_start, span_end) == (start, end) else "symbol_match"
            self.tag_range(tag, span_start, span_end)
        self.text.tag_raise("symbol_match")
        self.text.tag_raise("symbol_current")

    def show_member_links(self, tab, available_classes):
        if self.member_links_visible:
            return None
        self.member_links_visible = True
        self.text.tag_remove("member_link", "1.0", tk.END)
        if tab is not None and tab.kind == "class" and not tab.loading and not tab.error:
            # External framework members have no declaration tab in this APK,
            # so underline only references whose owner class is indexed.
            self.tag_ranges(
                "member_link",
                linkable_member_spans(tab.rendered_member_references, available_classes),
            )
            self.text.tag_raise("member_link")
        return None

    def hide_member_links(self, _event = None):
        self.member_links_visible = False
        self.text.tag_remove("member_link", "1.0", tk.END)
        return None

    def member_at_index(self, tab, index : str):
        if tab is None or tab.kind != "class" or tab.loading or tab.error:
            return None
        rendered = tab.edited_source or tab.source
        references = tab.rendered_member_references or tab.member_references
        if tab.comments:
            rendered, _comment_spans = self.render_source(tab)
            references = tab.rendered_member_references
        return member_reference_at_offset(references, index_to_offset(rendered, index))

    def tag_range(self, tag_name : str, start : int, end : int):
        if end > start:
            self.text.tag_add(tag_name, f"1.0+{start}c", f"1.0+{end}c")

    def tag_ranges(self, tag_name : str, spans, batch_size : int = 512):
        # Tk accepts many start/end pairs in one call; batching avoids thousands
        # of interpreter crossings without creating an oversized Tcl command.
        for offset in range(0, len(spans), batch_size):
            args = []
            for start, end in spans[offset:offset + batch_size]:
                if end > start:
                    args.extend((f"1.0+{start}c", f"1.0+{end}c"))
            if args:
                self.text.tag_add(tag_name, *args)

    def _tag_index_ranges(self, tag_name : str, spans, batch_size : int = 512):
        for offset in range(0, len(spans), batch_size):
            args = []
            for start, end in spans[offset:offset + batch_size]:
                args.extend((start, end))
            if args:
                self.text.tag_add(tag_name, *args)

    def _highlight_quoted_strings(self, text : str):
        spans = []
        start = None
        escape = False
        line = 1
        col = 0
        for ch in text:
            if start is None:
                if ch == '"':
                    start = f"{line}.{col}"
                    escape = False
            elif escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                spans.append((start, f"{line}.{col + 1}"))
                start = None
            if ch == "\n":
                line += 1
                col = 0
            else:
                col += 1
        self._tag_index_ranges("manifest_string", spans)

    def _start_async_highlight(self, text : str):
        self._highlight_generation += 1
        generation = self._highlight_generation
        if self._highlight_apply_job is not None:
            try:
                self.root.after_cancel(self._highlight_apply_job)
            except tk.TclError:
                pass
            self._highlight_apply_job = None
        for tag_name in _SOURCE_TAGS:
            self.text.tag_remove(tag_name, "1.0", tk.END)

        def worker():
            # The worker computes plain strings only. Tk tags are applied later
            # by the main-thread event drain.
            spans = java_highlight_spans(text)
            self.emit_event((
                "highlight_ready",
                generation,
                offset_spans_to_indexes(text, spans),
            ))

        threading.Thread(target=worker, daemon=True).start()

    def apply_highlight_spans(self, generation : int, spans):
        # A tab switch may happen while scanning. Never paint an old result into
        # the newly displayed document.
        if generation != self._highlight_generation:
            return
        work_items = []
        for tag_name in ("java_comment", "java_string", "java_annotation", "java_keyword"):
            for start, end in spans[tag_name]:
                work_items.append((tag_name, start, end))
        if not work_items:
            return

        def apply_chunk(offset : int = 0):
            if generation != self._highlight_generation:
                self._highlight_apply_job = None
                return
            end_offset = min(offset + self._highlight_apply_batch, len(work_items))
            for idx in range(offset, end_offset):
                tag_name, start, end = work_items[idx]
                self.text.tag_add(tag_name, start, end)
            if end_offset < len(work_items):
                # Yield between chunks so scrolling and tab switches remain
                # responsive on large decompiled classes.
                self._highlight_apply_job = self.root.after(1, apply_chunk, end_offset)
            else:
                self.text.tag_raise("user_comment")
                self.text.tag_lower("active_line")
                self._highlight_apply_job = None

        apply_chunk()

    def show_find(self, _event = None):
        self.hide_member_links()
        self.find_frame.grid()
        self.find_entry.focus_set()
        self.find_entry.selection_range(0, tk.END)
        self._last_find_text = self.find_var.get()
        self.refresh_find_marks(reset_cursor=True)
        return "break"

    def hide_find(self, _event = None):
        self.find_frame.grid_remove()
        self.text.tag_remove("find_match", "1.0", tk.END)
        self.text.tag_remove("find_current", "1.0", tk.END)
        self.find_status_var.set("")
        self.text.focus_set()
        return "break"

    def refresh_find_marks(self, reset_cursor : bool = False):
        needle = self.find_var.get()
        self.text.tag_remove("find_match", "1.0", tk.END)
        self.text.tag_remove("find_current", "1.0", tk.END)
        if reset_cursor:
            self.text.mark_set("insert", "1.0")
        if not needle:
            self.find_status_var.set("")
            return 0

        count = tk.IntVar()
        pos = "1.0"
        hits = 0
        while True:
            idx = self.text.search(needle, pos, stopindex=tk.END, nocase=True, count=count)
            if not idx or count.get() <= 0:
                break
            end = f"{idx}+{count.get()}c"
            self.text.tag_add("find_match", idx, end)
            hits += 1
            pos = end
        self.find_status_var.set(f"{hits} matches" if hits else "No match")
        return hits

    def _find_step(self, backwards : bool):
        needle = self.find_var.get()
        if not needle:
            self.find_status_var.set("Empty query")
            return "break"

        current_ranges = self.text.tag_ranges("find_current")
        current_start = str(current_ranges[0]) if current_ranges else None
        current_end = str(current_ranges[1]) if current_ranges else None
        self.refresh_find_marks(reset_cursor=False)
        count = tk.IntVar()
        insert_idx = self.text.index("insert")
        if backwards:
            start_idx = current_start or insert_idx
            idx = self.text.search(
                needle, start_idx, stopindex="1.0", backwards=True, nocase=True, count=count
            )
            if not idx:
                # No previous match: wrap from the end of the document.
                idx = self.text.search(
                    needle, tk.END, stopindex="1.0", backwards=True, nocase=True, count=count
                )
        else:
            start_idx = current_end or insert_idx
            idx = self.text.search(needle, start_idx, stopindex=tk.END, nocase=True, count=count)
            if not idx:
                # No following match: wrap from the beginning.
                idx = self.text.search(
                    needle, "1.0", stopindex=tk.END, nocase=True, count=count
                )
        if not idx or count.get() <= 0:
            self.find_status_var.set("No match")
            return "break"

        end = f"{idx}+{count.get()}c"
        self.text.tag_remove("find_current", "1.0", tk.END)
        self.text.tag_add("find_current", idx, end)
        self.text.mark_set("insert", idx if backwards else end)
        self.text.see(idx)
        self.find_status_var.set(f"Match at {idx}")
        return "break"

    def find_next(self, _event = None):
        return self._find_step(False)

    def find_prev(self, _event = None):
        return self._find_step(True)

    def _on_find_return(self, event = None):
        if event is not None and (event.state & 0x0001):
            return self.find_prev()
        return self.find_next()

    def _on_find_changed(self, event = None):
        if event is not None and event.keysym in (
            "Return", "KP_Enter", "Shift_L", "Shift_R",
            "Control_L", "Control_R", "Alt_L", "Alt_R",
        ):
            return "break"
        current = self.find_var.get()
        if current == self._last_find_text:
            return
        self._last_find_text = current
        self.refresh_find_marks(reset_cursor=True)
