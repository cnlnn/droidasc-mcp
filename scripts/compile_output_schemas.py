"""Generate or verify the source/version-bound MCP output schema cache."""

import argparse
import json

from droidasc_mcp.tool_registry import SCHEMA_PATH, compiled_schemas, schema_document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    document = schema_document()
    if args.check:
        assert compiled_schemas() == document["schemas"], "Regenerate the output schema cache"
    else:
        SCHEMA_PATH.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"path": str(SCHEMA_PATH), "contracts": len(document["schemas"]), "checked": args.check}
        )
    )


if __name__ == "__main__":
    main()
