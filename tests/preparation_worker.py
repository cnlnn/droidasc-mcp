"""Real preparation worker paused inside its SQLite owner writer for supervision tests."""

import json
import os
import sys
import time
from pathlib import Path

from droidasc_mcp.class_directory import ClassDirectory
from droidasc_mcp.dex_worker import main


def blocked_add(self, *args):
    Path(sys.argv[2]).write_text(
        json.dumps({"pid": os.getpid(), "root": str(Path(sys.argv[1]).parent)}),
        encoding="utf-8",
    )
    time.sleep(60)
    return original_add(self, *args)


if __name__ == "__main__":
    original_add = ClassDirectory.add
    ClassDirectory.add = blocked_add
    main()
