import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from dex_fixture import make_dex
from droidasc.asc_client.gui.backend import GuiDexStore
from droidasc.asc_client.gui.backend import search as search_backend
from droidasc.asc_client.gui.backend import worker as search_worker
from droidasc.asc_client.gui.backend.search import (
    build_find_query,
    dalvik_to_dot,
    format_class_name,
    is_member_search,
    parse_result_line,
)


class QueryTests(unittest.TestCase):
    def test_class_names_convert_between_display_and_dalvik_forms(self):
        self.assertEqual(format_class_name("example.Test"), "Lexample/Test;")
        self.assertEqual(format_class_name("example/Test"), "Lexample/Test;")
        self.assertEqual(format_class_name("Lexample/Test;"), "Lexample/Test;")
        self.assertEqual(dalvik_to_dot("Lexample/Test;"), "example.Test")
        self.assertEqual(dalvik_to_dot("int"), "int")
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            format_class_name("")

    def test_string_and_type_queries_keep_the_search_value(self):
        self.assertEqual(
            build_find_query("string refs", "a.b"),
            ("string", {"string": "a.b"}),
        )
        self.assertEqual(
            build_find_query("type refs", "Lexample/Test;"),
            ("type", {"type": "Lexample/Test;"}),
        )

    def test_exact_member_query_normalizes_class_and_member(self):
        find_type, query = build_find_query(
            "method refs",
            "run",
            "example.Test",
            exact_member=True,
        )
        self.assertEqual(find_type, "method")
        self.assertEqual(query, {
            "method": {
                "class": ["Lexample/Test;", True],
                "method": ["run", True],
            },
        })

    def test_fuzzy_member_query_uses_slashes_without_dalvik_wrapping(self):
        find_type, query = build_find_query(
            "field refs",
            "value",
            "example.Target",
            fuzzy_class=True,
        )
        self.assertEqual(find_type, "field")
        self.assertEqual(query, {
            "field": {
                "class": ["example/Target", False],
                "field": "value",
            },
        })

    def test_member_query_accepts_name_only_and_rejects_empty_query(self):
        self.assertEqual(
            build_find_query("method", "run"),
            ("method", {"method": {"class": None, "method": "run"}}),
        )
        with self.assertRaisesRegex(ValueError, "at least one"):
            build_find_query("field", "", None)

    def test_result_parser_preserves_method_target_and_occurrence(self):
        row = parse_result_line(
            "classes2.dex | Lsource/Owner;->run(I)V | "
            "matched=(Ltarget/Api;->call(Ljava/lang/String;)I) | occurrence=2",
            "method",
        )
        self.assertEqual(row["dex_name"], "classes2.dex")
        self.assertEqual(row["class_name"], "Lsource/Owner;")
        self.assertEqual(row["class_display"], "source.Owner")
        self.assertEqual(row["method_name"], "run")
        self.assertEqual(row["method_descriptor"], "(I)V")
        self.assertEqual(row["target_type"], "method")
        self.assertEqual(row["target_class"], "Ltarget/Api;")
        self.assertEqual(row["target_name"], "call")
        self.assertEqual(row["target_descriptor"], "(Ljava/lang/String;)I")
        self.assertEqual(row["occurrence"], 2)

    def test_result_parser_handles_field_type_and_legacy_lines(self):
        row = parse_result_line(
            "classes.dex | Lsource/Owner;->run()V | "
            "matched=(Ltarget/Api;->value:Ljava/lang/String;)",
            "field",
        )
        self.assertEqual(row["matched_text"], "matched=(Ltarget/Api;->value:Ljava/lang/String;)")
        self.assertEqual(row["target_class"], "Ltarget/Api;")
        self.assertEqual(row["target_name"], "value")
        self.assertEqual(row["target_descriptor"], "Ljava/lang/String;")
        self.assertEqual(row["occurrence"], 0)

    def test_member_search_type_is_limited_to_direct_member_modes(self):
        self.assertTrue(is_member_search("method"))
        self.assertTrue(is_member_search("field"))
        self.assertFalse(is_member_search("method refs"))
        self.assertFalse(is_member_search("string refs"))


class StoreTests(unittest.TestCase):
    def _loaded_store(self):
        directory = tempfile.TemporaryDirectory()
        apk = Path(directory.name) / "fixture.apk"
        with zipfile.ZipFile(apk, "w") as archive:
            archive.writestr("classes.dex", make_dex())
        store = GuiDexStore(str(apk), max_workers=1)
        store.load()
        self.addCleanup(directory.cleanup)
        return store

    def test_package_index_keeps_packages_and_root_classes_separate(self):
        store = GuiDexStore("unused.apk")
        store.class_names = sorted([
            "LRoot;",
            "Lcom/z/Beta;",
            "Lcom/a/Zed;",
            "Lcom/a/Alpha;",
        ])

        store._build_package_index()

        self.assertEqual(store.iter_root_packages(), ["com"])
        self.assertEqual(store.iter_child_packages("com"), ["com/a", "com/z"])
        self.assertEqual(store.iter_package_classes(""), ["LRoot;"])
        self.assertEqual(
            store.iter_package_classes("com/a"),
            ["Lcom/a/Alpha;", "Lcom/a/Zed;"],
        )

    def test_filtered_classes_are_case_insensitive_and_limited(self):
        store = GuiDexStore("unused.apk")
        store.class_names = [
            "Lalpha/First;",
            "Lalpha/Second;",
            "Lbeta/Alpha;",
        ]
        self.assertEqual(
            store.iter_filtered_classes("ALPHA", 2),
            ["Lalpha/First;", "Lalpha/Second;"],
        )
        self.assertEqual(store.iter_filtered_classes("  ", 10), [])

    def test_load_reports_progress_and_builds_indexes(self):
        store = self._loaded_store()
        self.assertEqual([entry[0] for entry in store.entries], ["classes.dex"])
        self.assertIn("Lexample/Test;", store.class_names)
        self.assertEqual(store.class_to_dex["Lexample/Test;"], "classes.dex")
        self.assertIn("classes.dex", store.dex_buffers)
        self.assertIn("classes.dex", store.findref_managers)

    def test_effective_workers_respect_dex_count_and_minimum_parallelism(self):
        store = GuiDexStore("unused.apk", max_workers=1)
        store.entries = [("a.dex",), ("b.dex",), ("c.dex",)]
        self.assertEqual(store.get_effective_search_workers(), 2)
        self.assertEqual(store.get_effective_search_workers(20), 3)
        store.entries = [("a.dex",)]
        self.assertEqual(store.get_effective_search_workers(20), 1)

    def test_source_metadata_is_cached_by_class(self):
        store = GuiDexStore("unused.apk")
        store.class_to_dex = {"Lexample/Test;": "classes.dex"}
        store.dex_buffers = {"classes.dex": b"dex"}
        calls = []

        class FakeHandler:
            def __init__(self, debug):
                self.debug = debug

            def getclass_with_metadata(self, dex_buf, class_name):
                calls.append((dex_buf, class_name))
                return "class Test {}", [(6, 10, "class")]

        with mock.patch("droidasc.asc_client.asc_handler.AscHandler", FakeHandler):
            first = store.get_source_with_metadata("Lexample/Test;")
            second = store.get_source_with_metadata("Lexample/Test;")

        self.assertIs(first, second)
        self.assertEqual(calls, [(b"dex", "Lexample/Test;")])

    def test_unknown_class_fails_without_touching_the_cache(self):
        store = GuiDexStore("unused.apk")
        with self.assertRaisesRegex(ValueError, "class not indexed"):
            store.get_source_with_metadata("Lmissing/Class;")
        self.assertEqual(store.source_cache, {})

    def test_member_search_returns_stable_rows_and_total_before_limit(self):
        store = self._loaded_store()
        result = store.search_members("method", "s", limit=1)
        self.assertEqual(result["backend"], "locator")
        self.assertEqual(result["workers"], 1)
        self.assertGreater(result["total_hits"], len(result["results"]))
        self.assertEqual(len(result["results"]), 1)
        row = result["results"][0]
        self.assertEqual(row["dex_name"], "classes.dex")
        self.assertEqual(row["class_name"], "Lexample/Test;")
        self.assertEqual(row["target_type"], "method")
        self.assertEqual(row["target_class"], row["class_name"])


class _FakeProcess:
    def __init__(self, returncode, stderr=""):
        self.returncode = returncode
        self.stderr = io.StringIO(stderr)
        self.terminated = False
        self.killed = False
        self.waited = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        self.waited = True
        return self.returncode


class WorkerTests(unittest.TestCase):
    def test_worker_writes_the_json_protocol(self):
        with tempfile.TemporaryDirectory() as directory:
            result_path = Path(directory) / "result.json"
            payload = {
                "apk_path": "fixture.apk",
                "entry": ["classes.dex", 1, 2, 3],
                "find_type": "string",
                "find": {"string": "token"},
                "result_path": str(result_path),
            }
            worker_result = ("classes.dex", ["line"], 10, 20, 30)
            with mock.patch.object(search_worker, "_findrefs_worker", return_value=worker_result):
                with mock.patch("sys.stdin", io.StringIO(json.dumps(payload))):
                    search_worker.main()

            self.assertEqual(json.loads(result_path.read_text(encoding="utf-8")), {
                "dex_name": "classes.dex",
                "lines": ["line"],
                "inflate_us": 10,
                "process_us": 20,
                "pid": 30,
            })

    def test_subprocess_failure_cleans_other_workers_and_temp_files(self):
        store = GuiDexStore("fixture.apk")
        store.entries = [("classes.dex",), ("classes2.dex",)]
        failed = _FakeProcess(1, "broken worker")
        running = _FakeProcess(None)

        with tempfile.TemporaryDirectory() as directory:
            failed_path = Path(directory) / "failed.json"
            running_path = Path(directory) / "running.json"
            failed_path.write_text("", encoding="utf-8")
            running_path.write_text("", encoding="utf-8")
            launched = iter([
                (failed, str(failed_path)),
                (running, str(running_path)),
            ])
            with mock.patch.object(
                search_backend,
                "_launch_subprocess_worker",
                side_effect=lambda *_args: next(launched),
            ):
                with self.assertRaisesRegex(RuntimeError, "broken worker"):
                    search_backend._search_with_subprocess_pool(
                        store,
                        2,
                        "string",
                        {"string": "token"},
                        None,
                    )

            self.assertTrue(running.terminated or running.killed)
            self.assertTrue(running.waited)
            self.assertFalse(failed_path.exists())
            self.assertFalse(running_path.exists())


if __name__ == "__main__":
    unittest.main()
