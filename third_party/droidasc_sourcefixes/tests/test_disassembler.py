import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from dex_fixture import (
    make_dex,
    make_field_invoke_chain_dex,
    make_instance_field_dex,
    make_invoke_dex,
    make_rich_dex,
)
from dadguard.core.dex import DEX, Instruction3rc
from dadguard.disassembler import disassemble_dex_bytes
from droidasc.asc_core.core.dex.dex_manager import DexManager


ROOT = Path(__file__).resolve().parents[1]


class DisassemblerTests(unittest.TestCase):
    def test_full_dex_disassembly_keeps_class_method_and_instruction_context(self):
        output = disassemble_dex_bytes(make_dex())

        self.assertIn("# CLASS: Lexample/Test;", output)
        self.assertIn("## METHOD: public static first ()V", output)
        self.assertNotIn("# 00000000  ", output)
        self.assertIn("const-string", output)
        self.assertIn("return-void", output)

    def test_range_disassembly_uses_instruction_offsets(self):
        output = disassemble_dex_bytes(make_dex(), offset=0x120, size=6)

        self.assertIn("const-string", output)
        self.assertIn("return-void", output)

    def test_method_filter_requires_exact_full_signature(self):
        output = disassemble_dex_bytes(
            make_dex(),
            method_signature="first()V",
        )

        self.assertIn(".method public static first()V", output)
        self.assertNotIn(".method public static second()V", output)
        with self.assertRaises(ValueError):
            disassemble_dex_bytes(make_dex(), method_signature="first")
        with self.assertRaises(ValueError):
            disassemble_dex_bytes(
                make_dex(),
                method_signature="missing()V",
            )

    def test_field_references_use_smali_colon_separator(self):
        output = disassemble_dex_bytes(make_instance_field_dex())

        self.assertIn("iget-object v0, v0, Lexample/Test;->a:Lexample/Target;", output)
        self.assertNotIn("Lexample/Test;->a L", output)

    def test_invoke_registers_use_smali_braces(self):
        output = disassemble_dex_bytes(make_invoke_dex())
        chain_output = disassemble_dex_bytes(make_field_invoke_chain_dex())

        self.assertIn(
            "invoke-static {}, Lexample/Target;->callToMethod()V",
            output,
        )
        self.assertIn(
            "invoke-virtual {v0}, Lexample/Target;->callToMethod()V",
            chain_output,
        )

    def test_range_invoke_registers_use_smali_range_braces(self):
        dex = DEX(make_dex())
        instruction = Instruction3rc(
            dex.CM,
            b"\x77\x03\x00\x00\x02\x00",
        )

        self.assertEqual(
            "{v2 .. v4}, Lexample/Test;->first()V",
            instruction.get_output(),
        )

    def test_full_disassembly_renders_smali_metadata_debug_and_exception_labels(self):
        output = disassemble_dex_bytes(make_rich_dex())

        self.assertIn(".class public Lexample/Rich;", output)
        self.assertIn(".super Ljava/lang/Object;", output)
        self.assertIn(".implements Lexample/Marker;", output)
        self.assertIn('.source "Rich.java"', output)
        self.assertIn(".field public value:I", output)
        self.assertIn(".method public run(I)I", output)
        self.assertIn("    .locals 1", output)
        self.assertIn(".annotation runtime Ldalvik/annotation/Deprecated;", output)
        self.assertNotIn("    .line ", output)
        self.assertNotIn("    .local ", output)
        self.assertNotIn("    .end local ", output)
        self.assertIn("    if-nez v0, :cond_0", output)
        self.assertIn("    goto :goto_0", output)
        self.assertIn("    :try_start_0", output)
        self.assertIn("    :try_end_0", output)
        self.assertIn(
            "    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0",
            output,
        )
        self.assertIn("    :catch_0", output)

        debug_output = disassemble_dex_bytes(make_rich_dex(), debug=True)
        self.assertIn("    # 00000000  ", debug_output)
        self.assertNotIn("    .line ", debug_output)

        debuginfo_output = disassemble_dex_bytes(
            make_rich_dex(),
            debuginfo=True,
        )
        self.assertIn("    .line 10", debuginfo_output)
        self.assertIn('    .local v0, "arg":I', debuginfo_output)
        self.assertIn("    .end local v0", debuginfo_output)

    def test_rebuilt_class_keeps_debug_info_for_smali_output(self):
        rebuilt = DexManager(memoryview(make_rich_dex())).extract_and_rebuild(
            "Lexample/Rich;"
        )
        output = disassemble_dex_bytes(
            rebuilt,
            verify_checksum=False,
            debuginfo=True,
        )

        self.assertIn("    .line 10", output)
        self.assertIn('    .local v0, "arg":I', output)
        self.assertIn("    .end local v0", output)
        self.assertIn(
            "    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0",
            output,
        )

    def test_cli_extracts_rebuilds_and_disassembles_target_class_from_apk(self):
        with tempfile.TemporaryDirectory() as directory:
            apk_path = Path(directory) / "fixture.apk"
            with zipfile.ZipFile(apk_path, "w") as archive:
                archive.writestr("classes.dex", make_dex())
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "main.py"),
                    "disassemble",
                    str(apk_path),
                    "example.Test",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# CLASS: Lexample/Test;", result.stdout)
        self.assertIn("const-string", result.stdout)
        self.assertNotIn("class Test", result.stdout)

    def test_cli_debug_reports_disassemble_stage_timings(self):
        with tempfile.TemporaryDirectory() as directory:
            apk_path = Path(directory) / "fixture.apk"
            with zipfile.ZipFile(apk_path, "w") as archive:
                archive.writestr("classes.dex", make_dex())
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "main.py"),
                    "disassemble",
                    str(apk_path),
                    "example.Test",
                    "--debug",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[DEBUG] Disassemble APK lookup:", result.stderr)
        self.assertIn("[DEBUG] Disassemble DEX rebuild:", result.stderr)
        self.assertIn("[DEBUG] Disassemble smali format:", result.stderr)
        self.assertIn("[DEBUG] Disassemble total:", result.stderr)

    def test_cli_method_filter_uses_exact_signature(self):
        with tempfile.TemporaryDirectory() as directory:
            apk_path = Path(directory) / "fixture.apk"
            with zipfile.ZipFile(apk_path, "w") as archive:
                archive.writestr("classes.dex", make_dex())
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "main.py"),
                    "disassemble",
                    str(apk_path),
                    "example.Test",
                    "--method",
                    "first()V",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(".method public static first()V", result.stdout)
        self.assertNotIn(".method public static second()V", result.stdout)

    def test_cli_debuginfo_enables_line_directives(self):
        with tempfile.TemporaryDirectory() as directory:
            apk_path = Path(directory) / "fixture.apk"
            with zipfile.ZipFile(apk_path, "w") as archive:
                archive.writestr("classes.dex", make_rich_dex())
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "main.py"),
                    "disassemble",
                    str(apk_path),
                    "example.Rich",
                    "--debuginfo",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("    .line 10", result.stdout)
        self.assertIn('    .local v0, "arg":I', result.stdout)


if __name__ == "__main__":
    unittest.main()
