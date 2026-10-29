import mmap
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
import zipfile

from dex_fixture import make_dex
from droidasc.asc_client import apk_handler
from droidasc.asc_client.apk import dex_reader, loader, worker


class LoaderTests(unittest.TestCase):
    def test_prefix_inflate_skips_trailing_dex_data(self):
        payload = make_dex() + (b"padding" * 1024)
        with tempfile.TemporaryDirectory() as directory:
            apk = Path(directory) / "fixture.apk"
            with zipfile.ZipFile(apk, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("classes.dex", payload)

            with apk.open("rb") as fp, mmap.mmap(
                fp.fileno(), 0, access=mmap.ACCESS_READ
            ) as mm:
                entry = loader._parse_cd_dex_entries(mm)[0]
                prefix = loader._inflate_dex_prefix(
                    mm,
                    entry,
                    lambda buf, full_size: dex_reader.class_defines_prefix_len(
                        buf,
                        b"Lexample/Test;",
                        full_size,
                    ),
                )

                self.assertIsNotNone(prefix)
                prefix_data, complete = prefix
                self.assertFalse(complete)
                self.assertLess(len(prefix_data), len(payload))
                self.assertTrue(
                    dex_reader._dex_defines_class(
                        prefix_data,
                        b"Lexample/Test;",
                    )
                )
                self.assertEqual(loader._inflate_dex(mm, entry), payload)

    def test_prefix_inflate_keeps_stored_entries_on_full_path(self):
        payload = make_dex() + (b"padding" * 128)
        with tempfile.TemporaryDirectory() as directory:
            apk = Path(directory) / "fixture.apk"
            with zipfile.ZipFile(apk, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr("classes.dex", payload)

            with apk.open("rb") as fp, mmap.mmap(
                fp.fileno(), 0, access=mmap.ACCESS_READ
            ) as mm:
                entry = loader._parse_cd_dex_entries(mm)[0]
                prefix = loader._inflate_dex_prefix(
                    mm,
                    entry,
                    lambda buf, full_size: dex_reader.class_defines_prefix_len(
                        buf,
                        b"Lexample/Test;",
                        full_size,
                    ),
                )

                self.assertEqual(prefix, (payload, True))

    def test_stored_and_deflated_entries_round_trip(self):
        payload = make_dex()
        for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            with self.subTest(compression=compression):
                with tempfile.TemporaryDirectory() as directory:
                    apk = Path(directory) / "fixture.apk"
                    with zipfile.ZipFile(apk, "w", compression=compression) as archive:
                        archive.writestr("classes.dex", payload)
                        archive.writestr("assets/classes2.dex", b"ignored")

                    with apk.open("rb") as fp, mmap.mmap(
                        fp.fileno(), 0, access=mmap.ACCESS_READ
                    ) as mm:
                        entries = loader._parse_cd_dex_entries(mm)
                        self.assertEqual([entry[0] for entry in entries], ["classes.dex"])
                        self.assertEqual(loader._inflate_dex(mm, entries[0]), payload)

    def test_deflate_cancellation_and_malformed_apk_are_clean(self):
        payload = make_dex()
        with tempfile.TemporaryDirectory() as directory:
            apk = Path(directory) / "fixture.apk"
            with zipfile.ZipFile(
                apk, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                archive.writestr("classes.dex", payload)

            with apk.open("rb") as fp, mmap.mmap(
                fp.fileno(), 0, access=mmap.ACCESS_READ
            ) as mm:
                entry = loader._parse_cd_dex_entries(mm)[0]
                cancelled = threading.Event()
                cancelled.set()
                self.assertIsNone(loader._inflate_dex(mm, entry, cancelled))

        with self.assertRaisesRegex(ValueError, "EOCD not found"):
            loader._parse_cd_dex_entries(b"broken")


class DexReaderTests(unittest.TestCase):
    def test_class_lookup_and_listing_share_the_same_string_reader(self):
        dex = make_dex()

        self.assertTrue(dex_reader._dex_defines_class(dex, b"Lexample/Test;"))
        self.assertFalse(dex_reader._dex_defines_class(dex, b"Lexample/Missing;"))
        self.assertEqual(dex_reader.list_dex_classes(dex), ["Lexample/Test;"])
        self.assertEqual(
            dex_reader.list_dex_classes(
                dex,
                prefix="Lexample",
                prefix_bytes=b"Lexample",
            ),
            ["Lexample/Test;"],
        )
        self.assertEqual(
            dex_reader.list_dex_classes(
                dex,
                prefix="Lmissing",
                prefix_bytes=b"Lmissing",
            ),
            [],
        )

    def test_invalid_header_preserves_lookup_and_listing_contracts(self):
        self.assertEqual(dex_reader._find_type_idx(b"broken", b"LTest;"), -1)
        with self.assertRaisesRegex(ValueError, "invalid DEX header"):
            dex_reader.list_dex_classes(b"broken")


class WorkerTests(unittest.TestCase):
    def tearDown(self):
        worker._close_worker_apk()

    def test_worker_reuses_and_closes_its_process_local_mmap(self):
        with tempfile.TemporaryDirectory() as directory:
            apk = Path(directory) / "fixture.apk"
            apk.write_bytes(b"mapped")

            first = worker._get_worker_apk_mm(str(apk))
            second = worker._get_worker_apk_mm(str(apk))
            self.assertIs(first, second)

            worker._close_worker_apk()
            self.assertIsNone(worker._WORKER_APK_PATH)
            self.assertIsNone(worker._WORKER_APK_FP)
            self.assertIsNone(worker._WORKER_APK_MM)

    def test_process_context_keeps_windows_on_spawn_default(self):
        if os.name == "nt":
            self.assertIsNone(worker._process_pool_context())


class FacadeTests(unittest.TestCase):
    def test_public_facade_does_not_reexport_moved_private_helpers(self):
        self.assertTrue(hasattr(apk_handler, "ApkHandler"))
        self.assertFalse(hasattr(apk_handler, "_inflate_dex"))
        self.assertFalse(hasattr(apk_handler, "_parse_cd_dex_entries"))
        self.assertFalse(hasattr(apk_handler, "_findrefs_worker"))

    def test_single_dex_lookup_avoids_a_useless_thread_pool(self):
        with tempfile.TemporaryDirectory() as directory:
            apk = Path(directory) / "fixture.apk"
            with zipfile.ZipFile(
                apk, "w", compression=zipfile.ZIP_DEFLATED
            ) as archive:
                archive.writestr("classes.dex", make_dex())

            handler = apk_handler.ApkHandler(str(apk), max_workers=8)
            with mock.patch.object(apk_handler, "ThreadPoolExecutor") as executor:
                dex_name, dex = handler.get_class_dex("Lexample/Test;")

            executor.assert_not_called()
            self.assertEqual(dex_name, "classes.dex")
            self.assertTrue(dex.startswith(b"dex"))

            with self.assertRaises(ValueError):
                apk_handler.ApkHandler(
                    str(apk), max_workers=0
                ).get_class_dex("Lexample/Test;")


if __name__ == "__main__":
    unittest.main()
