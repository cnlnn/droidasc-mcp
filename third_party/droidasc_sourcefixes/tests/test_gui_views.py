from types import SimpleNamespace
import tkinter as tk
from tkinter import ttk
import unittest
from unittest import mock

from droidasc.asc_client.gui.app import AscGuiApp
from droidasc.asc_client.gui.state import EditorTab
from droidasc.asc_client.gui.ui.class_tree import ClassTree
from droidasc.asc_client.gui.ui.dialogs import (
    LineCommentDialog,
    RenameDialog,
    SearchDialog,
    SettingsDialog,
)
from droidasc.asc_client.gui.ui.tab_bar import EditorTabBar
from droidasc.asc_client.gui.ui.theme import THEMES, ThemeManager


def _row(method_name, matched):
    return {
        "dex_name": "classes.dex",
        "class_name": "Lexample/Test;",
        "class_display": "example.Test",
        "method_text": f"Lexample/Test;->{method_name}()V",
        "matched_text": matched,
    }


class _TabApp:
    def __init__(self, root):
        self.root = root
        self.theme_manager = ThemeManager(root)
        self.theme = self.theme_manager.theme
        self.editor_tabs = [
            EditorTab("Lexample/First;", "First", dex_name="classes.dex", loading=False),
            EditorTab("Lexample/Second;", "Second", loading=True),
            EditorTab("Lexample/Third;", "Third", error="broken", loading=False),
        ]
        self.active_tab_idx = 0
        self.actions = []

    def _open_settings(self):
        self.actions.append(("settings",))

    def activate_tab(self, index):
        self.active_tab_idx = index
        self.actions.append(("activate", index))

    def close_tab(self, index):
        self.actions.append(("close", index))

    def clear_tabs(self):
        self.actions.append(("clear",))

    def apply_theme_to_window(self, win):
        self.theme_manager.apply_toplevel(win)


class _ClassStore:
    class_names = ["LRoot;", "Lcom/example/First;", "Lcom/example/Second;"]

    def iter_root_packages(self):
        return ["com"]

    def iter_package_classes(self, package_path):
        if package_path == "":
            return ["LRoot;"]
        if package_path == "com":
            return ["Lcom/Direct;"]
        return []

    def iter_child_packages(self, package_path):
        return ["com/example"] if package_path == "com" else []

    def iter_filtered_classes(self, keyword, _limit):
        return [
            name for name in self.class_names
            if keyword.lower() in name.lower()
        ]


class TkTestCase(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.root.withdraw()

    def tearDown(self):
        if self.root.winfo_exists():
            self.root.destroy()


class AppViewTests(TkTestCase):
    def test_app_builds_the_existing_layout_without_starting_background_load(self):
        with mock.patch.object(AscGuiApp, "_start_load"):
            app = AscGuiApp(self.root, "fixture.apk", max_workers=4)

        self.assertEqual(self.root.title(), "ASC GUI Auth: MG1937 - fixture.apk")
        self.assertEqual(app.status_var.get(), "Loading APK...")
        self.assertEqual(tuple(app.search_type_box.cget("values")), (
            "string refs",
            "type refs",
            "method refs",
            "field refs",
            "method",
            "field",
        ))
        self.assertEqual(str(app.search_button.cget("state")), "disabled")
        self.assertEqual(str(app.search_type_box.cget("state")), "disabled")
        self.assertEqual(
            str(app.class_browser.manifest_button.cget("state")),
            "disabled",
        )
        self.assertEqual(app.editor_view.find_frame.winfo_manager(), "")
        self.assertTrue(self.root.bind("<Control-f>"))
        self.assertTrue(self.root.bind("<Control-Tab>"))
        self.assertTrue(app.editor_view.text.bind("<Control-Button-1>"))

    def test_runtime_theme_change_updates_app_and_editor_colors(self):
        with mock.patch.object(AscGuiApp, "_start_load"):
            app = AscGuiApp(self.root, "fixture.apk")

        app.set_theme("dark")

        self.assertEqual(app.theme_name_var.get(), "dark")
        self.assertIs(app.theme, THEMES["dark"])
        self.assertEqual(
            app.editor_view.text.cget("background"),
            THEMES["dark"]["editor_bg"],
        )
        self.assertEqual(
            app.editor_view.text.tag_cget("member_link", "foreground"),
            THEMES["dark"]["accent"],
        )


class TabBarTests(TkTestCase):
    def setUp(self):
        super().setUp()
        self.root.geometry("320x180")
        self.app = _TabApp(self.root)
        self.bar = EditorTabBar(
            self.root,
            get_tabs=lambda: self.app.editor_tabs,
            get_active_index=lambda: self.app.active_tab_idx,
            activate_tab=self.app.activate_tab,
            close_tab=self.app.close_tab,
            clear_tabs=self.app.clear_tabs,
            open_settings=self.app._open_settings,
            get_theme=lambda: self.app.theme,
            apply_theme_to_window=self.app.apply_theme_to_window,
            apply_listbox_theme=self.app.theme_manager.apply_listbox,
        )
        self.bar.pack(fill=tk.X)
        self.root.update_idletasks()
        self.bar.redraw()

    def test_overflow_keeps_fixed_buttons_and_draws_clickable_tabs(self):
        self.assertEqual(str(self.bar.more_button.cget("state")), "normal")
        self.assertEqual(self.bar.more_button.cget("text"), "...")
        self.assertGreaterEqual(len(self.bar.tab_rects), 1)
        self.assertLess(len(self.bar.tab_rects), len(self.app.editor_tabs))

        index, x1, _x2, close_x1, close_x2 = self.bar.tab_rects[0]
        self.bar._on_click(SimpleNamespace(x=x1 + 5))
        self.bar._on_click(SimpleNamespace(x=(close_x1 + close_x2) // 2))

        self.assertEqual(self.app.actions, [
            ("activate", index),
            ("close", index),
        ])

    def test_ensure_visible_and_scroll_keep_index_in_bounds(self):
        self.bar.ensure_visible(2)
        self.assertLessEqual(self.bar.tab_scroll_index, 2)
        self.assertIn(
            2,
            [item[0] for item in self.bar._visible_capacity(
                self.bar.tab_scroll_index,
                self.bar._available_tab_width(),
            )],
        )
        self.bar.scroll_tabs(100)
        self.assertEqual(self.bar.tab_scroll_index, 2)
        self.bar.scroll_tabs(-100)
        self.assertEqual(self.bar.tab_scroll_index, 0)

    def test_tab_list_filter_preserves_original_tab_indexes_and_state(self):
        self.bar.popup_filter_var = tk.StringVar(master=self.root, value="second")
        self.assertEqual(
            self.bar._tab_list_rows(),
            ["example.Second  [loading]"],
        )
        self.assertEqual(self.bar.popup_visible_tab_indexes, [1])
        self.assertEqual(self.bar._tab_index_from_popup_selection(0), 1)
        self.assertIsNone(self.bar._tab_index_from_popup_selection(1))


class ClassTreeTests(TkTestCase):
    def test_lazy_packages_filtering_and_selection_keep_existing_behavior(self):
        opened = []
        browser = ClassTree(
            self.root,
            open_class=opened.append,
            open_manifest=lambda: None,
        )
        browser.pack(fill=tk.BOTH, expand=True)
        browser.set_store(_ClassStore())

        self.assertEqual(browser.info_var.get(), "Packages / Classes (3)")
        self.assertTrue(browser.tree.exists("pkg:com:stub"))
        self.assertTrue(browser.tree.exists("cls:LRoot;"))

        browser.tree.focus("pkg:com")
        browser._on_open()
        self.assertFalse(browser.tree.exists("pkg:com:stub"))
        self.assertTrue(browser.tree.exists("pkg:com/example"))
        self.assertTrue(browser.tree.exists("cls:Lcom/Direct;"))

        browser.tree.selection_set("cls:Lcom/Direct;")
        browser._on_select()
        self.assertEqual(opened, ["Lcom/Direct;"])

        browser.filter_var.set("second")
        browser.refresh()
        self.assertEqual(browser.info_var.get(), "Classes (1 filtered)")
        self.assertEqual(
            browser.tree.get_children(),
            ("cls:Lcom/example/Second;",),
        )


class DialogTests(TkTestCase):
    def test_search_dialog_streams_filters_and_opens_selected_result(self):
        opened = []
        theme_manager = ThemeManager(self.root)
        dialog = SearchDialog(
            self.root,
            "string refs",
            "token",
            None,
            False,
            open_result=lambda row, find_type: opened.append((row, find_type)),
            apply_theme=theme_manager.apply_toplevel,
        )
        first = _row("first", "matched=(alpha)")
        second = _row("second", "matched=(beta)")

        self.assertEqual(dialog.win.title(), "Search")
        self.assertEqual(str(dialog.filter_entry.cget("state")), "disabled")
        self.assertEqual(tuple(dialog.tree.cget("columns")), (
            "dex",
            "class",
            "method",
            "matched",
        ))

        dialog.append_results([first, second])
        dialog.finish({
            "results": [first, second],
            "total_hits": 2,
            "workers": 1,
            "backend": "subprocess",
        })
        dialog.filter_var.set("beta")
        dialog._rebuild_filtered_rows()
        dialog.tree.selection_set("0")
        dialog._open_selected()

        self.assertEqual(dialog.rows, [second])
        self.assertEqual(opened, [(second, "string refs")])
        self.assertEqual(str(dialog.filter_entry.cget("state")), "normal")
        dialog.win.destroy()

    def test_settings_dialog_applies_selected_theme_immediately(self):
        manager = ThemeManager(self.root)
        selected = []
        dialog = SettingsDialog(
            self.root,
            "light",
            manager.names(),
            selected.append,
            manager.apply_toplevel,
        )

        dialog.theme_var.set("dark")
        dialog._on_theme_changed()

        self.assertEqual(selected, ["dark"])
        self.assertEqual(dialog.win.title(), "Settings")
        self.assertFalse(dialog.win.resizable()[0])
        self.assertFalse(dialog.win.resizable()[1])
        dialog.win.destroy()

    def test_rename_dialog_stays_open_for_invalid_name_and_closes_on_success(self):
        manager = ThemeManager(self.root)
        renamed = []
        dialog = RenameDialog(
            self.root,
            "oldName",
            lambda value: renamed.append(value) or value == "newName",
            manager.apply_toplevel,
        )

        dialog.name_var.set("bad-name")
        dialog._save()
        self.assertTrue(dialog.win.winfo_exists())
        dialog.name_var.set("newName")
        dialog._save()

        self.assertEqual(renamed, ["bad-name", "newName"])
        self.assertFalse(dialog.win.winfo_exists())

    def test_line_comment_dialog_strips_saved_text_and_delete_returns_empty(self):
        manager = ThemeManager(self.root)
        saved = []
        dialog = LineCommentDialog(
            self.root,
            3,
            "    call();",
            "old",
            saved.append,
            manager.apply_toplevel,
        )
        dialog.comment_var.set("  revised  ")
        dialog._save()
        self.assertEqual(saved, ["revised"])

        dialog = LineCommentDialog(
            self.root,
            3,
            "    call();",
            "old",
            saved.append,
            manager.apply_toplevel,
        )
        dialog._delete()
        self.assertEqual(saved, ["revised", ""])


class ThemeTests(TkTestCase):
    def test_unknown_theme_falls_back_and_widget_helpers_apply_colors(self):
        manager = ThemeManager(self.root, "missing")
        text = tk.Text(self.root)
        listbox = tk.Listbox(self.root)

        manager.apply_text(text)
        manager.apply_listbox(listbox)

        self.assertEqual(manager.name, "light")
        self.assertEqual(manager.names(), ("light", "dark"))
        self.assertEqual(text.cget("background"), THEMES["light"]["editor_bg"])
        self.assertEqual(listbox.cget("selectbackground"), THEMES["light"]["accent"])


if __name__ == "__main__":
    unittest.main()
