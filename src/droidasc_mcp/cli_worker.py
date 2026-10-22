"""Invoke the original ASC CLI inside an already-supervised query worker."""

import runpy
import sys
from contextlib import redirect_stderr, redirect_stdout

from .dex_worker import BoundedText
from .runner import DroidAscError, DroidAscRunner, _clean_error


class PublicCliRunner(DroidAscRunner):
    """The outer supervisor enforces process, memory, time and output limits."""

    def _execute(self, args: list[str], *, module_name: str | None = None) -> bytes:
        assert module_name is None
        argv = sys.argv
        with (
            BoundedText(self.settings.max_output_bytes) as output,
            BoundedText(65536) as errors,
            redirect_stdout(output),
            redirect_stderr(errors),
        ):
            sys.argv = ["droidasc", *args]
            try:
                runpy.run_module("droidasc", run_name="__main__")
            except SystemExit as exc:
                if exc.code:
                    raise DroidAscError(_clean_error(errors.getvalue()) or "ASC failed") from None
            finally:
                sys.argv = argv
            return output.getvalue().encode("utf-8", errors="replace")
