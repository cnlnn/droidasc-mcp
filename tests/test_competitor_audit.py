"""Keep the exhaustive source audit and its evidence references structurally complete."""

import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("audit", ROOT / "scripts" / "audit_competitor.py")
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_documented_surface_and_evidence_are_complete():
    surface = audit.documented_surface()
    assert len(surface) == 30
    assert sum(kind == "tool" for kind, _ in surface) == 25
    assert sum(kind == "resource" for kind, _ in surface) == 2
    assert sum(kind == "prompt" for kind, _ in surface) == 3
    assert sum(map(len, surface.values())) == 87
    document = audit.DOCUMENT.read_text(encoding="utf-8")
    assert audit.PIN in document
    for filename in re.findall(r"(?:tests|scripts)/[a-z_]+\.py", document):
        assert (ROOT / filename).is_file(), filename


def test_source_extraction_excludes_context_and_resource_display_name():
    source = """
def create_server():
    @server.tool()
    async def method(analysis_id, ctx, *, limit=200): pass
    @server.resource("artifact://{id}/source", name="display")
    async def resource(id, ctx): pass
    @server.prompt(name="public_prompt")
    def prompt(id): pass
"""
    assert audit.source_surface(source) == {
        ("tool", "method"): ("analysis_id", "limit"),
        ("resource", "artifact://{id}/source"): ("id",),
        ("prompt", "public_prompt"): ("id",),
    }
