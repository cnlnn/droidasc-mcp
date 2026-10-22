"""Source-bound SDK input schemas with original per-call validation built on demand."""

import hashlib
import inspect
import json
from copy import deepcopy
from importlib.metadata import version
from pathlib import Path

import pydantic
from mcp.server.mcpserver.tools.base import Tool
from mcp.server.mcpserver.utilities.func_metadata import ArgModelBase, FuncMetadata
from pydantic import PrivateAttr

INPUT_SCHEMA_PATH = Path(__file__).with_suffix(".json")


def source_digest():
    root = Path(__file__).parent
    sources = {
        name: hashlib.sha256((root / name).read_text(encoding="utf-8").encode()).hexdigest()
        for name in ("server.py", "tool_registry.py", "input_schemas.py")
    }
    return hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest()


def records_digest(records):
    return hashlib.sha256(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def schema_document(tools):
    records = {}
    for tool in tools:
        if tool.resolved_params or tool.resolver_plans:
            raise ValueError("Compiled registration does not support resolver parameters")
        records[tool.name] = {
            "description": inspect.cleandoc(tool.description),
            "parameters": tool.parameters,
            "context_kwarg": tool.context_kwarg,
            "is_async": tool.is_async,
        }
    return {
        "schema": 1,
        "source_sha256": source_digest(),
        "pydantic_version": pydantic.__version__,
        "mcp_version": version("mcp"),
        "records_sha256": records_digest(records),
        "tools": records,
    }


def compiled_inputs(path=INPUT_SCHEMA_PATH):
    try:
        with path.open("rb") as stream:
            encoded = stream.read(512 * 1024 + 1)
        if len(encoded) > 512 * 1024:
            return {}
        document = json.loads(encoded)
        if not isinstance(document, dict):
            return {}
        records = document.get("tools")
        if (
            document.get("schema") != 1
            or document.get("source_sha256") != source_digest()
            or document.get("pydantic_version") != pydantic.__version__
            or document.get("mcp_version") != version("mcp")
            or not isinstance(records, dict)
            or document.get("records_sha256") != records_digest(records)
            or any(
                not isinstance(record, dict)
                or not isinstance(record.get("parameters"), dict)
                or record["parameters"].get("type") != "object"
                or not isinstance(record.get("description"), str)
                or type(record.get("is_async")) is not bool
                or not isinstance(record.get("context_kwarg"), (str, type(None)))
                for record in records.values()
            )
        ):
            return {}
        return records
    except (OSError, ValueError, TypeError):
        return {}


class DeferredInputMetadata(FuncMetadata):
    _factory = PrivateAttr()
    _input_metadata = PrivateAttr(default=None)

    def _input(self):
        if self._input_metadata is None:
            self._input_metadata = self._factory()
            self.arg_model = self._input_metadata.arg_model
        return self._input_metadata

    def validate_arguments(self, arguments_to_validate):
        return self._input().validate_arguments(arguments_to_validate)

    def pre_parse_json(self, data):
        return self._input().pre_parse_json(data)


def cached_tool(fn, annotations, contract, output_schema, records):
    if fn.__module__ != "droidasc_mcp.server" or not fn.__qualname__.startswith(
        "build_server.<locals>."
    ):
        return None
    record = records.get(fn.__name__)
    if record is None:
        return None
    metadata = DeferredInputMetadata(
        arg_model=ArgModelBase,
        output_model=contract,
        output_schema=deepcopy(output_schema),
    )
    metadata._factory = lambda: Tool.from_function(fn, structured_output=False).fn_metadata
    return Tool(
        fn=fn,
        name=fn.__name__,
        description=fn.__doc__ or "",
        parameters=deepcopy(record["parameters"]),
        fn_metadata=metadata,
        is_async=record["is_async"],
        context_kwarg=record["context_kwarg"],
        annotations=annotations,
    )
