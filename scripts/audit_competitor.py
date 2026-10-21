"""Check the exhaustive parity table against a pinned competitor source checkout."""

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

PIN = "848c711f1d80a1c2577283f1fa5f475ff734aa40"
DOCUMENT = Path(__file__).resolve().parents[1] / "docs" / "COMPETITOR_API_AUDIT.md"


def documented_surface(document=DOCUMENT):
    rows = {}
    for line in document.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip().strip("`") for cell in line.split("|")]
        if len(cells) != 7 or cells[1] not in {"tool", "resource", "prompt"}:
            continue
        key = (cells[1], cells[2])
        if key in rows:
            raise ValueError(f"Duplicate audit entry: {key}")
        rows[key] = tuple(cells[3].split(",")) if cells[3] else ()
    return rows


def source_surface(source):
    rows = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            if not (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and isinstance(decorator.func.value, ast.Name)
                and decorator.func.value.id == "server"
                and decorator.func.attr in {"tool", "resource", "prompt"}
            ):
                continue
            kind = decorator.func.attr
            name = node.name
            if kind == "resource":
                name = ast.literal_eval(decorator.args[0])
            for keyword in decorator.keywords:
                if keyword.arg == "name" and kind != "resource":
                    name = ast.literal_eval(keyword.value)
            rows[(kind, name)] = tuple(
                arg.arg for arg in node.args.args + node.args.kwonlyargs if arg.arg != "ctx"
            )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    args = parser.parse_args()
    commit = subprocess.check_output(
        ["git", "-C", str(args.checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != PIN:
        parser.error(f"Review the new competitor commit before changing the pin: {commit}")
    source = (args.checkout / "asc_mcp" / "server.py").read_bytes()
    expected, actual = documented_surface(), source_surface(source)
    if expected != actual:
        mismatches = sorted(
            key for key in expected.keys() | actual.keys() if expected.get(key) != actual.get(key)
        )
        parser.error(f"Missing/changed public contract rows: {mismatches}")
    print(
        json.dumps(
            {
                "status": "ok",
                "commit": commit,
                "server_sha256": hashlib.sha256(source).hexdigest(),
                "tools": sum(kind == "tool" for kind, _ in actual),
                "resources": sum(kind == "resource" for kind, _ in actual),
                "prompts": sum(kind == "prompt" for kind, _ in actual),
                "parameters": sum(map(len, actual.values())),
                "omissions": [],
                "scope": "public_surface_inventory_not_behavioral_acceptance",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
