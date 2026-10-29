import threading
import traceback
import tkinter as tk

from droidasc.asc_client.gui.backend import dalvik_to_dot
from droidasc.asc_client.gui.editor.source import (
    decode_java_unicode_escapes_with_ranges,
    find_member_declaration,
    find_method_range,
    find_search_reference,
    identifier_occurrences_in_range,
    index_to_offset,
    is_identifier,
    remap_ranges_after_replacements,
    rename_identifier_in_range,
    token_at_offset,
)
from droidasc.asc_client.gui.state import EditorTab
from droidasc.asc_client.gui.ui.dialogs import LineCommentDialog, RenameDialog


_SOURCE_NAV_KEYS = {
    "Left", "Right", "Up", "Down", "Home", "End", "Prior", "Next",
    "Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R",
}


def _class_label(dalvik_class : str):
    return dalvik_class.split("/")[-1].rstrip(";")


class EditorController:
    def __init__(
        self,
        root,
        view,
        get_store,
        emit_event,
        set_status,
        select_class,
        start_reference_search,
        apply_theme_to_window,
        debug : bool = False,
        debug_log = None,
    ):
        self.root = root
        self.view = view
        self.get_store = get_store
        self.emit_event = emit_event
        self.set_status = set_status
        self.select_class = select_class
        self.start_reference_search = start_reference_search
        self.apply_theme_to_window = apply_theme_to_window
        self.debug = debug
        self.debug_log = debug_log or (lambda _scope, _message: None)
        self.tabs = []
        self.active_tab_idx = -1
        # Declaration jumps store four fields; search-result jumps store the
        # containing method, target metadata and occurrence until source loads.
        self.pending_navigation = None
        self.tab_bar = None

    def set_tab_bar(self, tab_bar):
        self.tab_bar = tab_bar

    def bind_shortcuts(self):
        self.view.bind_find_shortcuts()
        self.root.bind("<Control-w>", self.close_active_tab)
        self.root.bind("<Control-W>", self.close_active_tab)
        self.root.bind("<Control-Tab>", self.next_tab)
        self.root.bind("<Control-Shift-Tab>", self.prev_tab)
        self.view.text.bind("<Button-1>", self._set_cursor_from_click)
        self.view.text.bind("<Control-Button-1>", self._open_member_from_click)
        self.view.text.bind("<FocusOut>", self.view.hide_member_links, add="+")
        self.root.bind("<KeyPress-Control_L>", self.show_member_links)
        self.root.bind("<KeyPress-Control_R>", self.show_member_links)
        self.root.bind("<KeyRelease-Control_L>", self.view.hide_member_links)
        self.root.bind("<KeyRelease-Control_R>", self.view.hide_member_links)
        self.view.text.bind("<KeyPress>", self._on_key_press)
        self.view.text.bind("<KeyRelease>", self._on_key_release)
        self.view.text.bind("<<Paste>>", lambda _event: "break")
        self.view.text.bind("<<Cut>>", lambda _event: "break")
        self.view.text.bind("<<Clear>>", lambda _event: "break")

    def _store(self):
        return self.get_store()

    def _available_classes(self):
        store = self._store()
        return store.class_to_dex if store is not None else ()

    def _redraw_tabs(self, ensure_index = None):
        if self.tab_bar is None:
            return
        if ensure_index is not None:
            self.tab_bar.ensure_visible(ensure_index)
        self.tab_bar.redraw()

    def active_tab(self):
        if self.active_tab_idx < 0 or self.active_tab_idx >= len(self.tabs):
            return None
        return self.tabs[self.active_tab_idx]

    def find_tab_index(self, dalvik_class : str):
        for idx, tab in enumerate(self.tabs):
            if tab.dalvik_class == dalvik_class:
                return idx
        return None

    def open_text_tab(self, tab_id : str, title : str, source : str, dex_name : str = ""):
        idx = self.find_tab_index(tab_id)
        if idx is None:
            self.view.remember(self.active_tab())
            self.tabs.append(EditorTab(dalvik_class=tab_id, title=title, kind="text"))
            idx = len(self.tabs) - 1
        tab = self.tabs[idx]
        tab.dex_name = dex_name
        tab.source = source
        tab.edited_source = ""
        tab.loading = False
        tab.error = ""
        self.activate_tab(idx)

    def activate_tab(self, index : int):
        if index < 0 or index >= len(self.tabs):
            return
        if index == self.active_tab_idx:
            self._redraw_tabs(index)
            self.complete_pending_navigation(self.tabs[index].dalvik_class)
            return
        self.view.remember(self.active_tab())
        self.active_tab_idx = index
        tab = self.tabs[index]
        self.view.show_tab(tab, self._available_classes())
        self._redraw_tabs(index)
        if tab.loading:
            self.set_status(f"Decompiling {dalvik_to_dot(tab.dalvik_class)}...")
        elif tab.error:
            self.set_status(tab.error)
        elif tab.kind == "class":
            self.set_status(f"Opened {dalvik_to_dot(tab.dalvik_class)} from {tab.dex_name}")
        else:
            self.set_status(f"Opened {tab.title}")
        if tab.kind == "class":
            self.select_class(tab.dalvik_class)
            self.complete_pending_navigation(tab.dalvik_class)

    def close_tab(self, index : int):
        if index < 0 or index >= len(self.tabs):
            return
        self.view.remember(self.active_tab())
        closing_tab = self.tabs[index]
        was_active = index == self.active_tab_idx
        self.tabs.pop(index)
        if self.pending_navigation is not None and self.pending_navigation[0] == closing_tab.dalvik_class:
            self.pending_navigation = None
        if not self.tabs:
            self.active_tab_idx = -1
            if self.tab_bar is not None:
                self.tab_bar.tab_scroll_index = 0
            self._redraw_tabs()
            self.view.show_empty()
            self.set_status("No class tab open")
            return
        if self.active_tab_idx > index:
            # Removing a tab before the active one shifts the active index but
            # does not require rerendering the still-visible source.
            self.active_tab_idx -= 1
        elif was_active:
            self.active_tab_idx = min(index, len(self.tabs) - 1)
            self.view.show_tab(self.tabs[self.active_tab_idx], self._available_classes())
        self._redraw_tabs(self.active_tab_idx)

    def clear_tabs(self):
        if not self.tabs:
            return
        self.tabs = []
        self.active_tab_idx = -1
        self.pending_navigation = None
        if self.tab_bar is not None:
            self.tab_bar.tab_scroll_index = 0
        self._redraw_tabs()
        self.view.show_empty()
        self.set_status("No class tab open")

    def close_active_tab(self, _event = None):
        self.close_tab(self.active_tab_idx)
        return "break"

    def _cycle_tab(self, step : int):
        if not self.tabs:
            return "break"
        self.activate_tab((self.active_tab_idx + step) % len(self.tabs))
        return "break"

    def next_tab(self, _event = None):
        return self._cycle_tab(1)

    def prev_tab(self, _event = None):
        return self._cycle_tab(-1)

    def finish_open_tab(self, dalvik_class : str, dex_name : str, source : str, member_references):
        idx = self.find_tab_index(dalvik_class)
        if idx is None:
            # The user may close a loading tab before its worker event arrives.
            return
        tab = self.tabs[idx]
        tab.dex_name = dex_name
        tab.source, tab.member_references = decode_java_unicode_escapes_with_ranges(
            source, member_references
        )
        tab.edited_source = ""
        tab.loading = False
        tab.error = ""
        if idx == self.active_tab_idx:
            self.view.show_tab(tab, self._available_classes())
        self._redraw_tabs(idx if idx == self.active_tab_idx else self.active_tab_idx)
        self.set_status(f"Opened {dalvik_to_dot(dalvik_class)} from {dex_name}")
        if idx == self.active_tab_idx:
            self.complete_pending_navigation(dalvik_class)

    def fail_open_tab(self, dalvik_class : str, message : str):
        idx = self.find_tab_index(dalvik_class)
        if idx is None:
            self.set_status(message)
            return
        tab = self.tabs[idx]
        tab.loading = False
        tab.error = message
        if self.pending_navigation is not None and self.pending_navigation[0] == dalvik_class:
            self.pending_navigation = None
        if idx == self.active_tab_idx:
            self.view.show_tab(tab, self._available_classes())
        self._redraw_tabs()
        self.set_status(message)

    def open_class(self, dalvik_class : str):
        store = self._store()
        if dalvik_class is None or store is None:
            return
        idx = self.find_tab_index(dalvik_class)
        created = idx is None
        if idx is None:
            self.view.remember(self.active_tab())
            self.tabs.append(EditorTab(dalvik_class=dalvik_class, title=_class_label(dalvik_class)))
            idx = len(self.tabs) - 1
        self.activate_tab(idx)
        tab = self.tabs[idx]
        if tab.loading and not created:
            return
        if not tab.error and tab.source:
            return
        tab.loading = True
        tab.error = ""
        tab.source = ""
        self.view.show_tab(tab, self._available_classes())
        self._redraw_tabs()
        self.set_status(f"Decompiling {dalvik_to_dot(dalvik_class)}...")
        self.debug_log("app", f"open class request class={dalvik_class}")

        def worker():
            try:
                self.debug_log("app", f"open class worker start class={dalvik_class}")
                dex_name, source, member_references = store.get_source_with_metadata(dalvik_class)
                # Tk must only be touched by the main event drain.
                self.emit_event((
                    "source_done", dalvik_class, dex_name, source, member_references
                ))
                self.debug_log(
                    "app",
                    f"open class worker done class={dalvik_class} dex={dex_name}",
                )
            except Exception as e:
                if self.debug:
                    traceback.print_exc()
                self.emit_event(("source_error", dalvik_class, f"Decompile failed: {e}"))

        threading.Thread(target=worker, daemon=True).start()

    def open_search_result(self, row, find_type : str):
        class_name = row["class_name"]
        target_type = row.get("target_type", "")
        if find_type in ("method", "field"):
            # Direct member rows jump to a declaration by exact descriptor.
            self.pending_navigation = (
                class_name, target_type, row.get("target_name", ""),
                row.get("target_descriptor", ""),
            )
        else:
            # Reference rows first locate their containing method, then select
            # the numbered target occurrence inside that method.
            self.pending_navigation = (
                class_name, "search", row.get("method_name", ""),
                row.get("method_descriptor", ""), target_type,
                row.get("target_class", ""), row.get("target_name", ""),
                row.get("target_descriptor", ""), row.get("occurrence", 0),
            )
        self.open_class(class_name)
        self.complete_pending_navigation(class_name)

    def complete_pending_navigation(self, dalvik_class : str):
        target = self.pending_navigation
        if target is None or target[0] != dalvik_class:
            return
        idx = self.find_tab_index(dalvik_class)
        if idx is None:
            return
        tab = self.tabs[idx]
        # Keep the request pending while an existing/new tab is still loading.
        if tab.loading or tab.error or not tab.source:
            return
        if target[1] == "search":
            self._complete_search_navigation(tab, target)
            return
        _class_name, member_type, member_name, descriptor = target
        reference = find_member_declaration(
            tab.rendered_member_references, member_type, member_name, descriptor
        )
        self.pending_navigation = None
        if reference is None:
            self.set_status(f"Declaration not found: {dalvik_to_dot(dalvik_class)}->{member_name}")
            return
        self._move_to_reference(tab, reference)
        if member_type == "class":
            self.set_status(f"Opened class {dalvik_to_dot(dalvik_class)}")
        else:
            self.set_status(f"Opened declaration {dalvik_to_dot(dalvik_class)}->{member_name}")

    def _complete_search_navigation(self, tab, target):
        (
            dalvik_class, _kind, method_name, method_descriptor,
            target_type, target_class, target_name, target_descriptor, occurrence,
        ) = target
        source = tab.edited_source or tab.source
        references = tab.rendered_member_references
        if tab.comments:
            source, _comment_spans = self.view.render_source(tab)
            references = tab.rendered_member_references
        reference = find_search_reference(
            source, references, method_name, method_descriptor,
            target_type, target_class, target_name, target_descriptor, occurrence,
        )
        exact = reference is not None
        # Older/aggregated worker rows may not identify the exact expression.
        # In that case the containing method declaration remains a useful jump.
        if reference is None:
            reference = find_member_declaration(
                references, "method", method_name, method_descriptor
            )
        if reference is None:
            reference = find_member_declaration(references, "method", method_name, "")
        self.pending_navigation = None
        if reference is None:
            self.set_status(f"Search location not found: {dalvik_to_dot(dalvik_class)}->{method_name}")
            return
        self._move_to_reference(tab, reference)
        suffix = "" if exact else " (exact expression unavailable)"
        self.set_status(f"Opened search hit {dalvik_to_dot(dalvik_class)}->{method_name}{suffix}")

    def _move_to_reference(self, tab, reference):
        index = f"1.0+{reference[0]}c"
        self.view.text.mark_set("insert", index)
        self.view.text.see(index)
        tab.insert_index = self.view.text.index("insert")
        tab.yview = self.view.text.yview()
        self.view.highlight_active_line()
        self.view.highlight_related_identifier(tab, tab.insert_index)

    def _set_cursor_from_click(self, event):
        try:
            self.view.text.focus_set()
            index = self.view.text.index(f"@{event.x},{event.y}")
            self.view.text.mark_set("insert", index)
            self.view.highlight_active_line()
            self.view.highlight_related_identifier(self.active_tab(), index)
        except tk.TclError:
            pass

    def show_member_links(self, _event = None):
        return self.view.show_member_links(self.active_tab(), self._available_classes())

    def _open_member_from_click(self, event):
        try:
            index = self.view.text.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return "break"
        reference = self.view.member_at_index(self.active_tab(), index)
        if reference is None:
            return "break"
        _start, _end, member_type, class_name, member_name, descriptor, _declaration = reference
        store = self._store()
        if store is None or class_name not in store.class_to_dex:
            self.set_status(
                f"Declaration class is not present in this APK: {dalvik_to_dot(class_name)}"
            )
            return "break"
        self.pending_navigation = (class_name, member_type, member_name, descriptor)
        self.open_class(class_name)
        self.complete_pending_navigation(class_name)
        return "break"

    def _on_key_press(self, event):
        if event.state & 0x0004:
            return None
        if event.keysym in ("x", "X"):
            return self.find_current_member_references()
        if event.keysym == "n":
            return self.show_rename_dialog()
        if event.char == ";":
            return self.show_line_comment_dialog()
        if event.keysym in _SOURCE_NAV_KEYS:
            return None
        return "break"

    def _on_key_release(self, event):
        if event.keysym in _SOURCE_NAV_KEYS:
            self.view.highlight_active_line()
            self.view.highlight_related_identifier(
                self.active_tab(),
                self.view.text.index("insert"),
            )
        return None

    def find_current_member_references(self, _event = None):
        tab = self.active_tab()
        if tab is None or tab.kind != "class" or tab.loading or tab.error or not tab.source:
            return "break"
        try:
            reference = self.view.member_at_index(tab, self.view.text.index("insert"))
        except tk.TclError:
            return "break"
        if reference is None or reference[2] not in ("method", "field"):
            self.set_status("Place the cursor on a method or field name to find its references")
            return "break"
        _start, _end, member_type, class_name, member_name, *_metadata = reference
        self.start_reference_search(member_type, member_name, class_name)
        return "break"

    def show_line_comment_dialog(self, _event = None):
        tab = self.active_tab()
        if tab is None or tab.kind != "class" or tab.loading or tab.error or not tab.source:
            return "break"
        line_no = self.view.line_from_index(self.view.text.index("insert"))
        if line_no is None:
            return "break"
        source_line = self._original_line_text(tab, line_no)
        if source_line == "":
            return "break"

        LineCommentDialog(
            self.root,
            line_no,
            source_line,
            tab.comments.get(line_no, ""),
            save_comment=lambda comment: self.set_line_comment(
                tab, line_no, comment
            ),
            apply_theme=self.apply_theme_to_window,
        )
        return "break"

    def set_line_comment(self, tab, line_no : int, comment : str):
        if comment:
            tab.comments[line_no] = comment
        else:
            tab.comments.pop(line_no, None)
        # render_source inserts comments without mutating decompiled source and
        # remaps member ranges for the displayed text.
        self.view.remember(tab)
        tab.insert_index = f"{line_no}.0"
        self.view.show_tab(tab, self._available_classes())
        self.set_status(f"Updated comment on line {line_no}")

    def show_rename_dialog(self, _event = None):
        tab = self.active_tab()
        if tab is None or tab.kind != "class" or tab.loading or tab.error or not tab.source:
            return "break"
        source = tab.edited_source or tab.source
        try:
            offset = index_to_offset(source, self.view.text.index("insert"))
        except tk.TclError:
            return "break"
        token = token_at_offset(source, offset)
        if token is None:
            self.set_status("No identifier at cursor")
            return "break"
        start, _end, old_name = token
        method_range = find_method_range(source, start)
        if method_range is None:
            self.set_status("Rename is only available inside a method body")
            return "break"

        def rename(new_name):
            if not is_identifier(new_name):
                self.set_status("Invalid identifier")
                return False
            self.rename_identifier(tab, method_range, old_name, new_name)
            return True

        RenameDialog(
            self.root,
            old_name,
            rename,
            self.apply_theme_to_window,
        )
        return "break"

    def rename_identifier(self, tab, method_range, old_name : str, new_name : str):
        if old_name == new_name:
            return
        source = tab.edited_source or tab.source
        renamed_spans = identifier_occurrences_in_range(
            source, method_range[0], method_range[1], old_name
        )
        new_source, count = rename_identifier_in_range(
            source, method_range[0], method_range[1], old_name, new_name
        )
        if count == 0:
            self.set_status(f"No occurrences of {old_name} in current method")
            return
        tab.edited_source = new_source
        # Navigation metadata is based on source offsets. Shift later ranges by
        # each identifier length delta before rerendering.
        tab.member_references = remap_ranges_after_replacements(
            tab.member_references, renamed_spans, len(new_name)
        )
        self.view.remember(tab)
        self.view.show_tab(tab, self._available_classes())
        self.set_status(f"Renamed {count} occurrence(s) in current method")

    @staticmethod
    def _original_line_text(tab, line_no : int):
        lines = (tab.edited_source or tab.source).splitlines()
        if line_no < 1 or line_no > len(lines):
            return ""
        return lines[line_no - 1]
