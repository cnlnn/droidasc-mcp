from types import SimpleNamespace
import unittest

from droidasc.asc_client.gui.app import AscGuiApp
from droidasc.asc_client.gui.editor.controller import EditorController
from droidasc.asc_client.gui.editor.source import (
    decode_java_unicode_escapes,
    decode_java_unicode_escapes_with_ranges,
    find_method_range,
    find_search_reference,
    identifier_occurrences_in_range,
    index_to_offset,
    is_identifier,
    java_highlight_spans,
    offset_spans_to_indexes,
    rename_identifier_in_range,
    token_at_offset,
)
from droidasc.asc_client.gui.state import EditorTab
from droidasc.asc_client.gui.ui.dialogs import SearchDialog


class _Value:
    def __init__(self, value=None):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class _Widget:
    def __init__(self):
        self.options = {}

    def config(self, **options):
        self.options.update(options)


class _Tree:
    def __init__(self):
        self.items = {}

    def insert(self, _parent, _where, iid, values):
        self.items[iid] = values

    def get_children(self):
        return tuple(self.items)

    def delete(self, *items):
        for item in items:
            self.items.pop(item, None)


class _EditorView:
    def __init__(self):
        self.remembered = []
        self.shown = []
        self.empty_count = 0

    def remember(self, tab):
        self.remembered.append(tab)

    def show_tab(self, tab, available_classes):
        self.shown.append((tab, available_classes))

    def show_empty(self):
        self.empty_count += 1


class _TabBar:
    def __init__(self):
        self.tab_scroll_index = 0
        self.ensured = []
        self.redraw_count = 0

    def ensure_visible(self, index):
        self.ensured.append(index)

    def redraw(self):
        self.redraw_count += 1


def _row(name, matched="matched=(token)"):
    return {
        "dex_name": "classes.dex",
        "class_display": "example.Test",
        "method_text": f"Lexample/Test;->{name}()V",
        "matched_text": matched,
    }


def _dialog():
    dialog = SearchDialog.__new__(SearchDialog)
    dialog.rows = []
    dialog.all_rows = []
    dialog.searching = True
    dialog.filter_entry = _Widget()
    dialog.status_var = _Value()
    dialog.progress_var = _Value()
    dialog.filter_var = _Value("")
    dialog.tree = _Tree()
    return dialog


class StateTests(unittest.TestCase):
    def test_editor_tab_defaults_are_independent(self):
        first = EditorTab("Lexample/First;", "First")
        second = EditorTab("Lexample/Second;", "Second")

        first.comments[1] = "note"
        first.member_references.append((1, 2))

        self.assertEqual(first.kind, "class")
        self.assertTrue(first.loading)
        self.assertEqual(first.yview, (0.0, 1.0))
        self.assertEqual(first.xview, (0.0, 1.0))
        self.assertEqual(first.insert_index, "1.0")
        self.assertEqual(second.comments, {})
        self.assertEqual(second.member_references, [])

    def test_search_done_restores_state_even_if_dialog_was_closed(self):
        app = SimpleNamespace(
            search_dialog=None,
            search_inflight=True,
            search_button=_Widget(),
            status_var=_Value("Searching"),
        )
        payload = {
            "total_hits": 3,
            "workers": 2,
            "backend": "subprocess",
            "results": [],
        }

        AscGuiApp._handle_event(app, ("search_done", payload))

        self.assertFalse(app.search_inflight)
        self.assertEqual(app.search_button.options["state"], "normal")
        self.assertEqual(
            app.status_var.get(),
            "Search done. hits=3 workers=2 backend=subprocess",
        )

    def test_search_error_restores_state_even_if_dialog_was_closed(self):
        app = SimpleNamespace(
            search_dialog=None,
            search_inflight=True,
            search_button=_Widget(),
            status_var=_Value("Searching"),
        )

        AscGuiApp._handle_event(app, ("search_error", "Search failed: broken"))

        self.assertFalse(app.search_inflight)
        self.assertEqual(app.search_button.options["state"], "normal")
        self.assertEqual(app.status_var.get(), "Search failed: broken")

    def test_controller_tab_lifecycle_clears_navigation_and_ignores_late_success(self):
        view = _EditorView()
        bar = _TabBar()
        statuses = []
        selected = []
        store = SimpleNamespace(class_to_dex={"Lexample/First;": "classes.dex"})
        controller = EditorController(
            root=None,
            view=view,
            get_store=lambda: store,
            emit_event=lambda _event: None,
            set_status=statuses.append,
            select_class=selected.append,
            start_reference_search=lambda *_args: None,
            apply_theme_to_window=lambda _win: None,
        )
        controller.set_tab_bar(bar)
        first = EditorTab(
            "Lexample/First;",
            "First",
            dex_name="classes.dex",
            source="class First {}",
            loading=False,
        )
        second = EditorTab(
            "manifest:AndroidManifest.xml",
            "AndroidManifest.xml",
            kind="text",
            source="<manifest/>",
            loading=False,
        )
        controller.tabs = [first, second]
        controller.pending_navigation = (
            "Lexample/First;", "method", "run", "()V",
        )

        controller.activate_tab(0)
        controller.close_tab(0)

        self.assertEqual(controller.tabs, [second])
        self.assertEqual(controller.active_tab_idx, 0)
        self.assertIsNone(controller.pending_navigation)
        self.assertEqual(selected, ["Lexample/First;"])
        self.assertEqual(view.shown[-1][0], second)

        controller.clear_tabs()
        shown_count = len(view.shown)
        controller.finish_open_tab(
            "Lexample/First;", "classes.dex", "late", [],
        )

        self.assertEqual(controller.active_tab_idx, -1)
        self.assertEqual(controller.tabs, [])
        self.assertEqual(view.empty_count, 1)
        self.assertEqual(len(view.shown), shown_count)
        self.assertEqual(statuses[-1], "No class tab open")


class SourceTests(unittest.TestCase):
    def test_tk_index_to_offset_clamps_lines_and_columns(self):
        text = "one\ntwo\nthree"
        self.assertEqual(index_to_offset(text, "1.2"), 2)
        self.assertEqual(index_to_offset(text, "2.1"), 5)
        self.assertEqual(index_to_offset(text, "4.0"), len(text))
        self.assertEqual(index_to_offset(text, "2.99"), len(text))

    def test_token_lookup_accepts_identifier_end_but_not_punctuation(self):
        text = "target.call();"
        self.assertEqual(token_at_offset(text, text.index("target")), (0, 6, "target"))
        self.assertEqual(token_at_offset(text, text.index(".")), (0, 6, "target"))
        self.assertEqual(token_at_offset(text, text.index("(")), (7, 11, "call"))
        self.assertIsNone(token_at_offset(text, len(text) - 1))
        self.assertIsNone(token_at_offset("", 0))

    def test_java_identifier_rules_keep_dollar_and_underscore(self):
        for value in ("name", "_name", "$name", "name2"):
            with self.subTest(value=value):
                self.assertTrue(is_identifier(value))
        for value in ("", "2name", "bad-name", "white space"):
            with self.subTest(value=value):
                self.assertFalse(is_identifier(value))

    def test_method_range_ignores_braces_in_literals_and_comments(self):
        source = (
            "void run()\n"
            "{\n"
            '    String text = "}";\n'
            "    // }\n"
            "    /* { } */\n"
            "    if (ready) { call(); }\n"
            "}\n"
            "void next() {}\n"
        )
        offset = source.index("call")
        method_range = find_method_range(source, offset)
        self.assertIsNotNone(method_range)
        start, end = method_range
        self.assertEqual(source[start:end], source[:source.index("\nvoid next")])

    def test_rename_changes_code_only_inside_requested_method(self):
        source = (
            "void first() {\n"
            "    int value = 1;\n"
            '    String text = "value"; // value\n'
            "    value++;\n"
            "}\n"
            "void second() { int value = 2; }\n"
        )
        start, end = find_method_range(source, source.index("value"))

        renamed, count = rename_identifier_in_range(
            source,
            start,
            end,
            "value",
            "renamed",
        )

        self.assertEqual(count, 2)
        self.assertIn("int renamed = 1", renamed)
        self.assertIn('"value"; // value', renamed)
        self.assertIn("void second() { int value = 2; }", renamed)

    def test_identifier_occurrences_skip_comments_strings_and_larger_names(self):
        source = 'value value2 "value" // value\nvalue /* value */'
        spans = identifier_occurrences_in_range(source, 0, len(source), "value")
        self.assertEqual([source[start:end] for start, end in spans], ["value", "value"])
        self.assertEqual(spans[1][0], source.index("\nvalue") + 1)

    def test_search_reference_selects_occurrence_inside_exact_method(self):
        source = (
            "void first() { target.call(); }\n"
            "void second() { target.call(); target.call(); }\n"
        )
        first_decl = source.index("first")
        second_decl = source.index("second")
        calls = []
        start = 0
        while True:
            start = source.find("call", start)
            if start < 0:
                break
            calls.append((start, start + 4, "method", "LTarget;", "call", "()V", False))
            start += 4
        references = [
            (first_decl, first_decl + 5, "method", "LTest;", "first", "()V", True),
            (second_decl, second_decl + 6, "method", "LTest;", "second", "()V", True),
            *calls,
        ]

        found = find_search_reference(
            source,
            references,
            "second",
            "()V",
            "method",
            "LTarget;",
            "call",
            "()V",
            occurrence=1,
        )

        self.assertEqual(found, calls[2])

    def test_unicode_decode_preserves_invalid_escapes_and_maps_ranges(self):
        source = r'"\u4f60"; run(); "\uFFFD"; "\uD800";'
        start = source.index("run")
        decoded, ranges = decode_java_unicode_escapes_with_ranges(
            source,
            [(start, start + 3, "method")],
        )
        self.assertIn(chr(0x4F60), decoded)
        self.assertIn(r"\uFFFD", decoded)
        self.assertIn(r"\uD800", decoded)
        self.assertEqual(decoded[ranges[0][0]:ranges[0][1]], "run")
        self.assertEqual(decode_java_unicode_escapes(r"\uD83D\uDE00"), chr(0x1F600))

    def test_java_highlight_spans_keep_lexical_categories_and_tk_indexes(self):
        source = '@Override\npublic void run() { String text = "class"; // return\n}'

        spans = java_highlight_spans(source)
        indexed = offset_spans_to_indexes(source, spans)

        self.assertEqual(
            [source[start:end] for start, end in spans["java_keyword"]],
            ["public", "void"],
        )
        self.assertEqual(
            [source[start:end] for start, end in spans["java_annotation"]],
            ["@Override"],
        )
        self.assertEqual(
            [source[start:end] for start, end in spans["java_string"]],
            ['"class"'],
        )
        self.assertEqual(
            [source[start:end] for start, end in spans["java_comment"]],
            ["// return"],
        )
        self.assertEqual(indexed["java_annotation"], [("1.0", "1.9")])
        self.assertEqual(indexed["java_keyword"][0], ("2.0", "2.6"))


class SearchDialogTests(unittest.TestCase):
    def test_streamed_rows_remain_visible_and_finish_enables_filter(self):
        dialog = _dialog()
        rows = [_row("first"), _row("second")]

        dialog.append_results(rows)
        dialog.finish({
            "results": rows,
            "total_hits": 2,
            "workers": 1,
            "backend": "locator",
        })

        self.assertEqual(dialog.rows, rows)
        self.assertEqual(dialog.all_rows, rows)
        self.assertEqual(len(dialog.tree.items), 2)
        self.assertFalse(dialog.searching)
        self.assertEqual(dialog.filter_entry.options["state"], "normal")
        self.assertEqual(dialog.progress_var.get(), 100)
        self.assertEqual(
            dialog.status_var.get(),
            "Done. hits=2 workers=1 backend=locator",
        )

    def test_filter_matches_all_displayed_columns(self):
        dialog = _dialog()
        dialog.append_results([
            _row("first", "matched=(alpha)"),
            _row("second", "matched=(beta)"),
        ])
        dialog.searching = False
        dialog.filter_var.set("BETA")

        dialog._rebuild_filtered_rows()

        self.assertEqual(len(dialog.rows), 1)
        self.assertIn("second", dialog.rows[0]["method_text"])
        self.assertEqual(len(dialog.all_rows), 2)
        self.assertEqual(tuple(dialog.tree.items), ("0",))

    def test_progress_handles_empty_and_nonempty_work(self):
        dialog = _dialog()
        dialog.update_progress(0, 0, 0)
        self.assertEqual(dialog.progress_var.get(), 0)
        dialog.update_progress(2, 4, 7)
        self.assertEqual(dialog.progress_var.get(), 50)
        self.assertEqual(dialog.status_var.get(), "Searching 2/4 dex, hits=7")


if __name__ == "__main__":
    unittest.main()
