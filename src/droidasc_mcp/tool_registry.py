"""Register SDK tools with precompiled schemas and unchanged lazy output validation."""

import hashlib
import inspect
import json
from copy import deepcopy
from pathlib import Path

import pydantic
from mcp.server.mcpserver.tools.base import Tool
from pydantic import TypeAdapter
from typing_extensions import is_typeddict

from . import contracts
from .input_schemas import INPUT_SCHEMA_PATH, cached_tool, compiled_inputs

OUTPUT_TYPES = {
    name: getattr(contracts, name)
    for name in (
        "ApkInfoResult",
        "ArchiveResult",
        "ArtifactResult",
        "DexResult",
        "DiffResult",
        "LegacyResult",
        "ManifestResult",
        "PingResult",
        "SecretResult",
        "SigningResult",
    )
}
SCHEMA_PATH = Path(__file__).with_name("output_schemas.json")


def contracts_digest():
    # Universal newline decoding makes canonical Linux sdist schemas usable in a
    # Windows checkout too; every other source change invalidates the cache.
    source = Path(contracts.__file__).read_text(encoding="utf-8")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def schemas_digest(schemas):
    return hashlib.sha256(
        json.dumps(schemas, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def schema_document():
    schemas = {name: TypeAdapter(contract).json_schema() for name, contract in OUTPUT_TYPES.items()}
    return {
        "schema": 1,
        "contracts_sha256": contracts_digest(),
        "pydantic_version": pydantic.__version__,
        "schemas_sha256": schemas_digest(schemas),
        "schemas": schemas,
    }


def compiled_schemas(path=SCHEMA_PATH):
    try:
        with path.open("rb") as stream:
            encoded = stream.read(512 * 1024 + 1)
        if len(encoded) > 512 * 1024:
            return None
        document = json.loads(encoded)
        if not isinstance(document, dict):
            return None
        schemas = document.get("schemas")
        if (
            document.get("schema") != 1
            or document.get("contracts_sha256") != contracts_digest()
            or document.get("pydantic_version") != pydantic.__version__
            or not isinstance(schemas, dict)
            or set(schemas) != set(OUTPUT_TYPES)
            or document.get("schemas_sha256") != schemas_digest(schemas)
            or any(
                not isinstance(value, dict) or value.get("type") != "object"
                for value in schemas.values()
            )
        ):
            return None
        return schemas
    except (OSError, ValueError, TypeError):
        return None


class ToolRegistry:
    def __init__(self, *, schema_path=SCHEMA_PATH, input_schema_path=INPUT_SCHEMA_PATH):
        self.tools = []
        self.schemas = compiled_schemas(schema_path) or {}
        self.inputs = compiled_inputs(input_schema_path) if input_schema_path is not None else {}

    def tool(self, *, annotations):
        def register(fn):
            contract = inspect.get_annotations(fn, eval_str=True)["return"]
            if not is_typeddict(contract) or OUTPUT_TYPES.get(contract.__name__) is not contract:
                raise TypeError(
                    "Only declared object output contracts can use compiled registration"
                )
            name = contract.__name__
            if name not in self.schemas:
                self.schemas[name] = TypeAdapter(contract).json_schema()
            # The SDK still owns input parsing, Context injection, cancellation,
            # serialization and strict output validation. Only schema generation
            # moves to build time; the SDK creates/reuses its adapter on first call.
            tool = cached_tool(fn, annotations, contract, self.schemas[name], self.inputs)
            if tool is None:
                tool = Tool.from_function(fn, annotations=annotations, structured_output=False)
                tool.fn_metadata.output_model = contract
                tool.fn_metadata.output_schema = deepcopy(self.schemas[name])
            self.tools.append(tool)
            return fn

        return register
