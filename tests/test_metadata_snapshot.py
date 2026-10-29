"""Metadata pages retain complete source, token identity and Unicode span coordinates."""

import hashlib
import json
from dataclasses import replace

import pytest
from test_native_directory import class_dex

from droidasc_mcp.cli_worker import PublicCliRunner
from droidasc_mcp.dex_worker import analyze
from droidasc_mcp.runner import Snapshot
from droidasc_mcp.service import DroidAscService
from droidasc_mcp.source_metadata import export_snapshot, source_page
from droidasc_mcp.worker_errors import response_limit


@pytest.mark.parametrize(
    "source",
    [
        "",
        "\n",
        "\r",
        "\r\n",
        "last",
        "one\n\n",
        "\U0001f600\r\ntwo\rthree\nlast",
        "A\vB\fC\x1cD\x1dE\x1eF\x85G\u2028H\u2029I",
        "e\u0301\n\u4e2d\U0001f600",
    ],
)
def test_snapshot_keeps_python_unicode_line_boundaries(source):
    snapshot = Snapshot.build(source.encode(), sort=False, budget=100000, keepends=True)
    assert list(snapshot.lines) == source.splitlines(keepends=True)
    assert "".join(snapshot.lines) == source


def rows(source):
    return [
        (index, index + 1, "field", "Lfixture/C;", "name", "I", False)
        for index, char in enumerate(source)
        if char.isalpha() or char == "\U0001f600"
    ]


def test_source_pages_reconstruct_unicode_text_and_ordered_spans():
    source = "\U0001f600\r\nA\u2028B\n\nlast"
    references = [(0, 5, "type", "Lfixture/C;", "C", "Lfixture/C;", True), *rows(source)]
    lines = source.splitlines(keepends=True)
    pieces, found = [], []
    for offset in range(len(lines)):
        page = source_page(lines, references, offset=offset, limit=1)
        assert page["source_start"] == len("".join(pieces))
        pieces.append(page["source"])
        assert page["source_end"] == len("".join(pieces))
        found.extend(page["member_references"])
    whole = source_page(lines, references, offset=0, limit=100)
    assert "".join(pieces) == source
    assert found == whole["member_references"]
    assert found[0]["end"] > len(pieces[0])


@pytest.mark.parametrize("fits", [False, True])
def test_export_has_one_combined_source_reference_budget(tmp_path, fits):
    source = "\U0001f600\r\nA\u2028B\n"
    references = rows(source)
    needed = len(source.encode()) + len(json.dumps(references).encode())
    export_snapshot(tmp_path, source.encode(), references, needed if fits else needed - 1)
    if fits:
        assert (tmp_path / "source.txt").read_bytes() == source.encode()
        assert json.loads((tmp_path / "source-refs.json").read_text()) == [
            list(r) for r in references
        ]
        assert sum(p.stat().st_size for p in tmp_path.iterdir()) == needed
    else:
        assert not list(tmp_path.iterdir())


@pytest.fixture
def metadata_session(settings, tmp_path, monkeypatch):
    from droidasc.asc_client.asc_handler import AscHandler

    path = tmp_path / "input.dex"
    path.write_bytes(class_dex(["Lfixture/C;"]))
    service = DroidAscService(settings)
    state = {"source": "\U0001f600\r\nA\u2028B\n\nlast", "requests": []}
    state["references"] = rows(state["source"])
    monkeypatch.setattr(
        AscHandler,
        "getclass_with_metadata",
        lambda self, data, name: (state["source"], state["references"]),
    )

    def execute(request, workspace):
        state["requests"].append(request)
        result = analyze(request, workspace)
        encoded = json.dumps(result)
        return response_limit() if len(encoded.encode()) > 256 * 1024 else json.loads(encoded)

    try:
        key = service.open_dex_session([str(path)])["session_id"]
        monkeypatch.setattr(service.runner, "_run_dex_request", execute)
        yield service, key, state
    finally:
        service.close()


def query(service, key, *, cached=True, **page):
    return service.query_dex_session(
        key,
        operation="get_class_source_metadata",
        class_name="fixture.C",
        offset=page.get("offset", 0),
        limit=page.get("limit", 1),
        _source_snapshot=cached,
    )


def test_cached_and_uncached_metadata_pages_have_identical_contract(metadata_session):
    service, key, state = metadata_session
    whole = query(service, key, limit=100)
    assert whole["source"] == state["source"]
    assert whole["source_sha256"] == hashlib.sha256(state["source"].encode()).hexdigest()
    for offset in range(whole["total"] + 2):
        for limit in (1, 2, 100):
            assert query(service, key, offset=offset, limit=limit) == query(
                service, key, cached=False, offset=offset, limit=limit
            )
    assert sum(r.get("source_snapshot", False) for r in state["requests"]) == 1
    assert len(service.runner._cache) == 1
    assert (
        sum(v.size_bytes for v in service.runner._cache.values())
        <= service.settings.max_output_bytes
    )


def test_metadata_responses_and_plain_source_cache_are_independent(metadata_session, monkeypatch):
    service, key, state = metadata_session
    first = query(service, key, limit=100)
    first["member_references"][0]["name"] = "mutated"
    first["sources"].clear()
    assert query(service, key, limit=100)["member_references"][0]["name"] == "name"
    assert query(service, key)["sources"]
    monkeypatch.setattr(PublicCliRunner, "_execute", lambda self, args: b"plain\n")
    plain = service.query_dex_session(
        key, operation="get_class_source", class_name="fixture.C", offset=0, limit=1, threads=1
    )
    assert plain["source"] == "plain" and len(service.runner._cache) == 2
    assert query(service, key, limit=100)["source"] == state["source"]
    assert service.sessions.close(key)["status"] == "ok" and not service.runner._cache


def test_metadata_optional_retention_failure_keeps_original_page(metadata_session, monkeypatch):
    service, key, state = metadata_session
    expected = query(service, key, cached=False)

    def fail(*args, **kwargs):
        from droidasc_mcp.runner import DroidAscError

        raise DroidAscError("Decoded snapshot exceeds memory budget")

    monkeypatch.setattr(Snapshot, "build", fail)
    assert query(service, key) == expected and not service.runner._cache


def test_metadata_disk_capacity_falls_back_to_existing_worker(metadata_session):
    service, key, state = metadata_session
    service.sessions.settings = replace(service.settings, max_dex_session_bytes=1)
    assert query(service, key)["status"] == "ok"
    assert not service.runner._cache and service.sessions.reserved == 0
    assert not state["requests"][-1].get("source_snapshot", False)


@pytest.mark.parametrize("damage", ["source", "references", "missing"])
def test_metadata_export_failure_preserves_first_page(metadata_session, monkeypatch, damage):
    service, key, state = metadata_session
    expected = query(service, key, cached=False)
    execute = service.runner._run_dex_request

    def corrupt(request, workspace):
        result = execute(request, workspace)
        if request.get("source_snapshot"):
            if damage == "source":
                (workspace / "source.txt").write_bytes(b"changed")
            elif damage == "references":
                (workspace / "source-refs.json").write_bytes(b"{")
            else:
                (workspace / "source-refs.json").unlink()
        return result

    monkeypatch.setattr(service.runner, "_run_dex_request", corrupt)
    assert query(service, key) == expected and not service.runner._cache


def test_malformed_later_token_row_keeps_worker_error_envelope(metadata_session):
    service, key, state = metadata_session
    last = len(state["source"]) - 1
    state["references"].append((last, last + 1))
    assert query(service, key)["status"] == "ok"
    offset = len(state["source"].splitlines()) - 1
    expected = query(service, key, cached=False, offset=offset)
    assert expected["code"] == "invalid_query"
    assert query(service, key, offset=offset) == expected


def test_later_oversized_plain_line_keeps_worker_error_envelope(metadata_session, monkeypatch):
    service, key, state = metadata_session
    monkeypatch.setattr(
        PublicCliRunner, "_execute", lambda self, args: b"small\n" + b"x" * 100000 + b"\n"
    )
    arguments = {
        "operation": "get_class_source",
        "class_name": "fixture.C",
        "threads": 1,
        "limit": 1,
    }
    assert service.query_dex_session(key, **arguments, offset=0)["status"] == "ok"
    expected = service.query_dex_session(key, **arguments, offset=1, _source_snapshot=False)
    assert expected["code"] == "engine_error"
    assert service.query_dex_session(key, **arguments, offset=1) == expected
