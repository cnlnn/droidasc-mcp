"""Generate or verify SDK input schemas from uncached, current tool registrations."""

import argparse
import json

from droidasc_mcp.input_schemas import INPUT_SCHEMA_PATH, compiled_inputs, schema_document
from droidasc_mcp.server import build_server
from droidasc_mcp.tool_registry import ToolRegistry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    registry = ToolRegistry(input_schema_path=None)
    build_server(registry=registry)
    document = schema_document(registry.tools)
    if args.check:
        assert compiled_inputs() == document["tools"], "Regenerate the input schema cache"
    else:
        INPUT_SCHEMA_PATH.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"path": str(INPUT_SCHEMA_PATH), "tools": len(registry.tools), "checked": args.check}
        )
    )


if __name__ == "__main__":
    main()
