"""Atomic, size-bounded SQLite indexes shared by fresh session query workers."""

import hashlib
import json
import os
import sqlite3
import subprocess
import zlib
from contextlib import closing
from functools import lru_cache
from pathlib import Path

from .method_backend import java_command
from .runner import DroidAscError

INDEX_OPERATIONS = {"build_xref_index", "find_type_refs", "get_call_graph"}
DISCOVERY_OPERATIONS = {"search_members", "search_strings"}
REFERENCE_OPERATIONS = {"find_method_refs", "get_method_calls", "find_field_refs"}
SCHEMA = "3"


def backend_identity(settings, sources=("IndexBridge.java", "xref_index.py")):
    if not settings.jadx_home:
        return None
    jars = sorted((settings.jadx_home / "lib").glob("*.jar"))
    if not jars:
        return None
    digest = hashlib.sha256(SCHEMA.encode())
    for path in [*(Path(__file__).with_name(name) for name in sources), *jars]:
        digest.update(path.name.encode())
        with path.open("rb") as source:
            while block := source.read(1024 * 1024):
                digest.update(block)
    return digest.hexdigest()


def _build(settings, bundle, target, workspace, identity):
    command = java_command(settings, workspace, "IndexBridge.java")
    if isinstance(command, dict):
        return command
    temporary = workspace / "index.partial.sqlite"
    with closing(sqlite3.connect(temporary)) as db:
        db.execute("PRAGMA page_size=4096")
        db.execute(f"PRAGMA max_page_count={max(1, settings.max_xref_index_bytes // 4096)}")
        db.execute("PRAGMA journal_mode=OFF")
        db.execute("PRAGMA synchronous=OFF")
        db.execute("PRAGMA temp_store=MEMORY")
        db.executescript("""
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE symbols (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
            CREATE TABLE definitions (kind TEXT, name INTEGER UNIQUE, entry TEXT,
                                      PRIMARY KEY(kind,name));
            CREATE TABLE edges (id INTEGER PRIMARY KEY, kind TEXT, target INTEGER,
                                source INTEGER, relation TEXT, data BLOB);
            CREATE TABLE methods (source INTEGER PRIMARY KEY, instructions INTEGER,
                                  without_code INTEGER);
            CREATE TABLE dynamic (id INTEGER PRIMARY KEY, source INTEGER, data BLOB);
            CREATE INDEX incoming ON edges(kind,target,relation);
            CREATE INDEX outgoing ON edges(kind,source);
            CREATE INDEX dynamic_source ON dynamic(source);
        """)

        @lru_cache(maxsize=32768)
        def symbol(name):
            db.execute("INSERT OR IGNORE INTO symbols(name) VALUES (?)", (name,))
            return db.execute("SELECT id FROM symbols WHERE name=?", (name,)).fetchone()[0]

        def pack(data):
            return zlib.compress(json.dumps(data, separators=(",", ":")).encode(), level=1)

        try:
            process = subprocess.Popen(
                [*command, str(bundle)],
                cwd=workspace,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
            )
        except OSError as exc:
            raise DroidAscError("Could not start index backend") from exc
        complete = False
        edges = 0
        with process:
            try:
                while line := process.stdout.readline(1024 * 1024 + 1):
                    if len(line) > 1024 * 1024:
                        raise DroidAscError("Index record exceeds stream limit")
                    if complete:
                        raise DroidAscError("Unexpected records after index trailer")
                    row = json.loads(line)
                    record = row["record"]
                    if record == "definition":
                        db.execute(
                            "INSERT INTO definitions VALUES (?,?,?)",
                            (
                                row["kind"],
                                symbol(row["descriptor"]),
                                row["dex_entry"],
                            ),
                        )
                    elif record == "edge":
                        db.execute(
                            "INSERT INTO edges VALUES (NULL,?,?,?,?,?)",
                            (
                                row["kind"],
                                symbol(row["target"]),
                                symbol(row["source"]),
                                row["relation"],
                                _pack_edge(row["kind"], row["data"]),
                            ),
                        )
                        edges += 1
                    elif record == "method":
                        db.execute(
                            "INSERT INTO methods VALUES (?,?,?)",
                            (
                                symbol(row["source"]),
                                row["instructions"],
                                row["without_code"],
                            ),
                        )
                    elif record == "dynamic":
                        db.execute(
                            "INSERT INTO dynamic VALUES (NULL,?,?)",
                            (
                                symbol(row["source"]),
                                pack(row["data"]),
                            ),
                        )
                    elif record == "complete":
                        complete = row["schema"] == 1 and row["edges"] == edges
                    else:
                        raise DroidAscError("Unknown index record")
                if process.wait() != 0 or not complete:
                    raise DroidAscError("Index scan failed; no partial index was published")
            except BaseException:
                process.kill()
                raise
        db.executemany("INSERT INTO metadata VALUES (?,?)", identity.items())
        db.commit()
    if temporary.stat().st_size > settings.max_xref_index_bytes:
        raise DroidAscError("Index exceeds configured disk budget")
    os.replace(temporary, target)
    return None


def _pack_edge(kind, row):
    # Descriptors, relation and source DEX already live in normalized tables.
    payload = [row["instruction_offset"]]
    if kind == "type":
        payload.append(row["detail"])
    else:
        payload.append(row["opcode"])
        payload.append(row.get("call_site_prototype") if kind == "method" else row["storage"])
    return json.dumps(payload, separators=(",", ":")).encode()


def _unpack_edge(kind, payload, source, target, relation, entry):
    data = json.loads(payload)
    row = {
        "dex_entry": entry,
        "instruction_offset": data[0],
        "offset_unit": None if data[0] is None else "code_units_from_method_start",
    }
    if kind == "type":
        row.update(source=source, type_descriptor=target, relation=relation, detail=data[1])
    else:
        row.update(caller=source, opcode=data[1])
        if kind == "method":
            row["callee"] = target
            if data[2] is not None:
                row["call_site_prototype"] = data[2]
        else:
            row.update(field_descriptor=target, access=relation, storage=data[2])
    return row


def query_index(settings, bundle, common, query, workspace):
    from .durable_index import DurableIndexes

    target = bundle.parent / "xrefs.sqlite"
    fingerprint = backend_identity(settings)
    if fingerprint is None:
        return {"status": "error", "code": "backend_unavailable", "message": "Configure JADX 1.5.5"}
    identity = {"schema": SCHEMA, "input_id": common["input_id"], "backend_id": fingerprint}
    try:
        cache = DurableIndexes(settings)
        reused = target.is_file()
        cache_status = "not_accessed" if settings.xref_cache_dir else "disabled"
        if not reused and cache.restore(identity, target, workspace):
            reused = True
            cache_status = "restored"
        if reused:
            with closing(sqlite3.connect(target.as_uri() + "?mode=ro", uri=True)) as db:
                if dict(db.execute("SELECT key,value FROM metadata")) != identity:
                    return {
                        "status": "error",
                        "code": "index_identity_changed",
                        "message": "Reopen the session after engine/schema changes",
                    }
        else:
            if query["operation"] not in INDEX_OPERATIONS:
                return None
            from .query_cache import clear_cache

            clear_cache(bundle.parent)
            error = _build(settings, bundle, target, workspace, identity)
            if error:
                return error
            cache_status = cache.publish(identity, target)
        with closing(sqlite3.connect(target.as_uri() + "?mode=ro", uri=True)) as db:
            result = _query(db, query, settings)
        result["index"] = {
            **identity,
            "reused": reused,
            "stored_bytes": target.stat().st_size,
            "persistence": "session_lifetime",
            "durable_cache": cache_status,
            "format": "sqlite",
        }
        return result
    except (sqlite3.Error, ValueError, KeyError, OSError, zlib.error) as exc:
        raise DroidAscError("Index failed validation or exceeded its disk budget") from exc


def _query(db, query, settings):
    operation = query["operation"]
    base = {
        "status": "ok",
        "backend": "dexlib2-index",
        "backend_version": "1.5.5",
        "instruction_scan_complete": True,
        "scan_errors": 0,
        "runtime_target_resolution": "not_performed",
    }
    if operation == "build_xref_index":
        return {
            **base,
            "edge_counts": dict(db.execute("SELECT kind,count(*) FROM edges GROUP BY kind")),
            "definition_count": db.execute("SELECT count(*) FROM definitions").fetchone()[0],
        }
    if operation == "get_call_graph":
        from .call_graph import query_call_graph

        return {**base, **query_call_graph(db, query)}
    if operation == "search_members":
        clauses = ["d.kind=?", "instr(s.name,?)>0"]
        params = [query["kind"], query.get("value") or ""]
        if query.get("class_name"):
            clauses.append("substr(s.name,1,length(?))=?")
            owner = query["class_name"] + "->"
            params.extend([owner, owner])
        joined = "FROM definitions d JOIN symbols s ON s.id=d.name WHERE " + " AND ".join(clauses)
        total = db.execute("SELECT count(*) " + joined, params).fetchone()[0]
        offset = min(query["offset"], 2**63 - 1)
        limit = min(query["limit"], settings.max_page_size)
        items = [
            {"kind": kind, "descriptor": name, "dex_entry": entry}
            for kind, name, entry in db.execute(
                "SELECT d.kind,s.name,d.entry " + joined + " ORDER BY s.name LIMIT ? OFFSET ?",
                [*params, limit, offset],
            )
        ]
        more = offset + len(items) < total
        return {
            **base,
            "instruction_scan_complete": False,
            "match_semantics": "case_sensitive_literal_substring_of_full_descriptor",
            "scope": "declarations_in_supplied_files",
            "items": items,
            "total": total,
            "offset": query["offset"],
            "limit": limit,
            "has_more": more,
            "truncated": more,
            "next_offset": offset + len(items) if more else None,
        }
    fields = operation == "find_field_refs"
    types = operation == "find_type_refs"
    outgoing = operation == "get_method_calls"
    kind = "field" if fields else "type" if types else "method"
    descriptor_key = f"{kind}_descriptor"
    requested = query[descriptor_key]
    match = db.execute("SELECT id FROM symbols WHERE name=?", (requested,)).fetchone()
    requested_id = match[0] if match else -1
    if (
        outgoing
        and not db.execute("SELECT 1 FROM methods WHERE source=?", (requested_id,)).fetchone()
    ):
        return {**base, "status": "error", "code": "method_not_found", descriptor_key: requested}
    clauses = ["e.kind=?", "e.source=?" if outgoing else "e.target=?"]
    params = [kind, requested_id]
    relation = (
        query.get("field_access", "all")
        if fields
        else query.get("type_relation", "all")
        if types
        else "all"
    )
    if relation != "all":
        clauses.append("e.relation=?")
        params.append(relation)
    where = " AND ".join(clauses)
    joined = (
        "FROM edges e LEFT JOIN definitions d ON d.kind=e.kind AND d.name=e.target WHERE " + where
    )
    total, unresolved = db.execute(
        "SELECT count(*),count(*)-count(d.entry) " + joined, params
    ).fetchone()
    offset, limit = min(query["offset"], 2**63 - 1), min(query["limit"], settings.max_page_size)
    items = []
    detail_joined = (
        "FROM edges e LEFT JOIN definitions d ON d.kind=e.kind AND d.name=e.target "
        "JOIN symbols src ON src.id=e.source JOIN symbols dst ON dst.id=e.target "
        "JOIN definitions origin ON origin.name=e.source WHERE " + where
    )
    for data, entry, source, target, edge_relation, origin in db.execute(
        "SELECT e.data,d.entry,src.name,dst.name,e.relation,origin.entry "
        + detail_joined
        + " ORDER BY e.id LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ):
        row = _unpack_edge(kind, data, source, target, edge_relation, origin)
        row.update(
            target_resolution="defined_in_input" if entry else "not_defined_in_input",
            target_dex_entry=entry,
        )
        items.append(row)
    base.update(
        {
            descriptor_key: requested,
            "total": total,
            "items": items,
            "offset": query["offset"],
            "limit": limit,
            "has_more": offset + limit < total,
            "truncated": offset + limit < total,
            "next_offset": offset + limit if offset + limit < total else None,
            "unresolved_matches": unresolved,
        }
    )
    subset = " WHERE source=?" if outgoing else ""
    args = (requested_id,) if outgoing else ()
    methods, instructions, without = db.execute(
        "SELECT count(*),coalesce(sum(instructions),0),coalesce(sum(without_code),0) FROM methods"
        + subset,
        args,
    ).fetchone()
    dynamic = db.execute("SELECT count(*) FROM dynamic" + subset, args).fetchone()[0]
    sites = [
        json.loads(zlib.decompress(r[0]))
        for r in db.execute("SELECT data FROM dynamic" + subset + " ORDER BY id LIMIT 20", args)
    ]
    base.update(
        scanned_methods=methods,
        scanned_instructions=instructions,
        methods_without_code=without,
        dynamic_sites=dynamic,
        unresolved_sites=sites,
        unresolved_sites_truncated=dynamic > len(sites),
        scan_scope="selected_method" if outgoing else "supplied_dex_methods",
    )
    if fields:
        base.update(
            field_access=relation,
            reference_semantics="declared_field_operand",
            limitations=[
                "inherited_field_resolution",
                "reflection",
                "jni",
                "runtime_loaded_code",
                "encoded_initial_values",
                "method_handle_targets",
            ],
        )
    elif types:
        base.update(
            type_relation=relation,
            reference_semantics="exact_declared_type",
            limitations=[
                "reflection",
                "jni",
                "runtime_loaded_code",
                "encoded_initial_values",
                "method_handle_targets",
                "generic_signature_strings",
                "array_component_expansion",
            ],
        )
    else:
        base.update(
            reference_semantics="declared_method_operand",
            limitations=["virtual_dispatch", "reflection", "jni", "runtime_loaded_code"],
        )
    return base
