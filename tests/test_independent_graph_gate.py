"""The full-index oracle must reject missing rows and equal-count corruptions.

Expected records below are hand-written, not obtained from a product scanner or
from the candidate index. Androguard remains a separate acceptance-only dependency.
"""

import copy
import hashlib
import importlib
import json
import sqlite3
import struct
import zipfile
import zlib
from collections import Counter
from contextlib import closing
from pathlib import Path

import pytest

ROOT = "Lfixture/A;->root()V"
LEAF = "Lfixture/B;->leaf()V"
EMPTY = "Lfixture/B;->empty()V"
POLY = "Ljava/lang/invoke/MethodHandle;->invokeExact([Ljava/lang/Object;)Ljava/lang/Object;"


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def unresolved(caller=ROOT, entry="classes.dex", offset=3, opcode="invoke-polymorphic"):
    return {
        "caller": caller,
        "dex_entry": entry,
        "instruction_offset": offset,
        "opcode": opcode,
        "reason": "dynamic_target_not_resolved",
    }


def independent_records():
    return [
        ("calls", compact(["classes.dex", ROOT, LEAF, 0, "invoke-static", ""])),
        ("calls", compact(["classes.dex", ROOT, POLY, 3, "invoke-polymorphic", "(I)I"])),
        ("methods", compact(["classes.dex", ROOT, 3, 0])),
        ("methods", compact(["classes2.dex", LEAF, 1, 0])),
        ("methods", compact(["classes2.dex", EMPTY, 0, 1])),
        ("dynamic", compact(["classes.dex", ROOT, unresolved()])),
    ]


@pytest.fixture
def gate(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    return importlib.import_module("verify_call_index")


@pytest.fixture
def index(tmp_path):
    path = tmp_path / "calls.sqlite"
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
            CREATE TABLE symbols (id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
            CREATE TABLE definitions (kind TEXT, name INTEGER UNIQUE, entry TEXT);
            CREATE TABLE methods (source INTEGER PRIMARY KEY, instructions INTEGER,
                                  without_code INTEGER);
            CREATE TABLE edges (id INTEGER PRIMARY KEY, kind TEXT, target INTEGER,
                                source INTEGER, relation TEXT, data BLOB);
            CREATE TABLE dynamic (id INTEGER PRIMARY KEY, source INTEGER, data BLOB);
        """)
        db.executemany("INSERT INTO symbols VALUES (?,?)", enumerate((ROOT, LEAF, EMPTY, POLY), 1))
        db.executemany(
            "INSERT INTO definitions VALUES ('method',?,?)",
            [(1, "classes.dex"), (2, "classes2.dex"), (3, "classes2.dex")],
        )
        db.executemany("INSERT INTO methods VALUES (?,?,?)", [(1, 3, 0), (2, 1, 0), (3, 0, 1)])
        db.executemany(
            "INSERT INTO edges VALUES (?,'method',?,1,'instruction',?)",
            [
                (1, 2, compact([0, "invoke-static", None])),
                (2, 4, compact([3, "invoke-polymorphic", "(I)I"])),
            ],
        )
        db.execute("INSERT INTO dynamic VALUES (1,1,?)", (zlib.compress(compact(unresolved())),))
    return path


@pytest.fixture
def compare_storage(gate, monkeypatch):
    """Run the unchanged comparator against either physical primary-key layout."""
    connect = sqlite3.connect

    def run(index, records, workspace, *, legacy_rowid=False):
        connections, snapshots = [], []

        class ObservedConnection(sqlite3.Connection):
            is_comparison = False

            def execute(self, sql, *args, **kwargs):
                if sql.startswith("CREATE TABLE records "):
                    self.is_comparison = True
                    assert sql.endswith(" WITHOUT ROWID")
                    if legacy_rowid:
                        sql = sql.removesuffix(" WITHOUT ROWID")
                    # Fix the page size so the allocation comparison is repeatable.
                    super().execute("PRAGMA page_size=4096")
                return super().execute(sql, *args, **kwargs)

            def close(self):
                try:
                    if self.is_comparison:
                        # Inspect live pages, including the uncommitted working set.
                        # compare_index intentionally does not persist this scratch DB.
                        snapshots.append(
                            {
                                "schema": list(
                                    self.execute(
                                        "SELECT type,name,sql FROM sqlite_schema ORDER BY type,name"
                                    )
                                ),
                                "page_count": self.execute("PRAGMA page_count").fetchone()[0],
                                "page_size": self.execute("PRAGMA page_size").fetchone()[0],
                                "rows": list(
                                    self.execute(
                                        "SELECT kind,record,candidate,oracle FROM records "
                                        "ORDER BY kind,record"
                                    )
                                ),
                            }
                        )
                finally:
                    super().close()

        def observed_connect(*args, **kwargs):
            connection = connect(*args, factory=ObservedConnection, **kwargs)
            connections.append(connection)
            return connection

        with monkeypatch.context() as patch:
            patch.setattr(gate.sqlite3, "connect", observed_connect)
            try:
                result = gate.compare_index(index, records, workspace)
            finally:
                # Keep references alive to prove explicit close, not CPython GC.
                assert len(connections) == 2
                for connection in connections:
                    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
                        connection.execute("SELECT 1")
                assert not list(workspace.glob("call-multiset-*"))
        assert len(snapshots) == 1
        return result, snapshots[0]

    return run


def expected_multiset_result(records):
    """Independent in-memory reference for the existing wire-format digest."""
    counts, hashes = {}, {}
    for kind in ("calls", "methods", "dynamic"):
        multiset = Counter(record for tag, record in records if tag == kind)
        counts[kind] = sum(multiset.values())
        digest = hashlib.sha256()
        for record, count in sorted(multiset.items()):
            digest.update(struct.pack("<II", len(record), count))
            digest.update(record)
        hashes[kind] = digest.hexdigest()
    methods = [json.loads(record) for kind, record in records if kind == "methods"]
    return {
        "total_call_sites": counts["calls"],
        "methods": counts["methods"],
        "scanned_instructions": sum(row[2] for row in methods),
        "methods_without_code": sum(row[3] for row in methods),
        "dynamic_sites": counts["dynamic"],
        "site_multiset_sha256": hashes["calls"],
        "method_multiset_sha256": hashes["methods"],
        "dynamic_multiset_sha256": hashes["dynamic"],
    }


@pytest.mark.parametrize("case", ["empty", "mixed", "duplicates", "shared_bytes"])
def test_storage_layout_preserves_exact_multisets(
    gate, index, tmp_path, monkeypatch, compare_storage, case
):
    records = [] if case == "empty" else independent_records()
    if case == "duplicates":
        records += records[::2] * 3 + records[1::2] * 2
    elif case == "shared_bytes":
        # Test the composite key itself: identical bytes in different kinds must
        # never be merged, even when each kind has a different multiplicity.
        key = compact(["classes.dex", "Lfixture/Shared;->same()V", 9, 0])
        records += [
            (kind, key)
            for n, kind in enumerate(("calls", "methods", "dynamic"), 1)
            for _ in range(n)
        ]
    monkeypatch.setattr(gate, "candidate_records", lambda _: iter(records))
    old_result, old = compare_storage(index, reversed(records), tmp_path, legacy_rowid=True)
    new_result, new = compare_storage(index, reversed(records), tmp_path)
    assert old_result == new_result == expected_multiset_result(records)
    expected_rows = [
        (kind, record, count, count) for (kind, record), count in sorted(Counter(records).items())
    ]
    assert old["rows"] == new["rows"] == expected_rows


@pytest.mark.parametrize("kind", ["calls", "methods", "dynamic"])
@pytest.mark.parametrize("fault", ["omission", "duplicate", "equal_count_corruption"])
def test_both_storage_layouts_reject_exact_multiset_differences(
    gate, index, tmp_path, monkeypatch, compare_storage, kind, fault
):
    records = independent_records()
    monkeypatch.setattr(gate, "candidate_records", lambda _: iter(records))
    oracle = records.copy()
    position = next(n for n, (tag, _) in enumerate(oracle) if tag == kind)
    if fault == "omission":
        oracle.pop(position)
    elif fault == "duplicate":
        oracle.append(oracle[position])
    else:
        tag, record = oracle[position]
        oracle[position] = tag, record + b" "  # Same JSON value, different exact bytes.
    errors = []
    for legacy_rowid in (True, False):
        with pytest.raises(AssertionError, match=f"Persisted {kind} multiset") as error:
            compare_storage(index, iter(oracle), tmp_path, legacy_rowid=legacy_rowid)
        errors.append(str(error.value))
    assert errors[0] == errors[1]


@pytest.mark.parametrize("descriptor_repeats", [16, 256], ids=["medium", "overflow"])
def test_long_descriptors_use_one_smaller_exact_key_btree(
    gate, index, tmp_path, monkeypatch, compare_storage, record_property, descriptor_repeats
):
    owner = "Lfixture/" + "LongDescriptor" * descriptor_repeats + ";->"
    records = [
        (
            "calls",
            compact(
                [
                    "classes.dex",
                    owner + "root()V",
                    owner + f"target{n:04d}()V",
                    n,
                    "invoke-static",
                    "",
                ]
            ),
        )
        for n in range(128)
    ]
    records += records[::3]  # Multiplicity updates must not allocate duplicate records.
    monkeypatch.setattr(gate, "candidate_records", lambda _: iter(records))
    old_result, old = compare_storage(index, reversed(records), tmp_path, legacy_rowid=True)
    new_result, new = compare_storage(index, reversed(records), tmp_path)
    assert old_result == new_result == expected_multiset_result(records)
    assert old["rows"] == new["rows"]
    assert [(kind, name) for kind, name, _ in old["schema"]] == [
        ("index", "sqlite_autoindex_records_1"),
        ("table", "records"),
    ]
    assert [(kind, name) for kind, name, _ in new["schema"]] == [("table", "records")]
    assert new["schema"][0][2].endswith(" WITHOUT ROWID")
    assert old["page_size"] == new["page_size"] == 4096
    old_bytes = old["page_count"] * old["page_size"]
    new_bytes = new["page_count"] * new["page_size"]
    record_property("legacy_comparison_bytes", old_bytes)
    record_property("without_rowid_comparison_bytes", new_bytes)
    assert new_bytes < old_bytes * 0.75


def test_complete_multisets_include_empty_methods_and_dynamic_content(gate, index, tmp_path):
    result = gate.compare_index(index, iter(independent_records()), tmp_path)
    assert result["total_call_sites"] == 2
    assert result["methods"] == 3 and result["methods_without_code"] == 1
    assert result["scanned_instructions"] == 4 and result["dynamic_sites"] == 1
    assert (
        len(
            {
                result[key]
                for key in (
                    "site_multiset_sha256",
                    "method_multiset_sha256",
                    "dynamic_multiset_sha256",
                )
            }
        )
        == 3
    )


@pytest.mark.parametrize(
    "mutation",
    [
        "DELETE FROM edges WHERE id=2",
        "INSERT INTO edges SELECT 3,kind,target,source,relation,data FROM edges WHERE id=1",
        "UPDATE edges SET data=(SELECT data FROM edges WHERE id=1),target=2 WHERE id=2",
        "UPDATE edges SET target=999 WHERE id=1",
        "UPDATE edges SET source=999 WHERE id=1",
        "UPDATE edges SET relation='declaration' WHERE id=1",
        "UPDATE edges SET kind='field' WHERE id=1",
        "UPDATE definitions SET entry='classes3.dex' WHERE name=1",
        "UPDATE definitions SET entry='classes.dex' WHERE name=3",
        "DELETE FROM definitions WHERE name=3",
        "DELETE FROM methods WHERE source=3",
        "UPDATE methods SET instructions=CASE source WHEN 1 THEN 2 WHEN 2 THEN 2 ELSE 0 END",
        "UPDATE methods SET without_code=0 WHERE source=3",
        "DELETE FROM dynamic",
        "INSERT INTO dynamic SELECT 2,source,data FROM dynamic WHERE id=1",
        "UPDATE dynamic SET source=2 WHERE id=1",
        "UPDATE dynamic SET source=999 WHERE id=1",
    ],
)
def test_omissions_duplicates_hidden_rows_and_provenance_are_rejected(
    gate, index, tmp_path, mutation
):
    with closing(sqlite3.connect(index)) as db, db:
        db.execute(mutation)
    with pytest.raises(AssertionError):
        gate.compare_index(index, iter(independent_records()), tmp_path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("caller", LEAF),
        ("dex_entry", "classes2.dex"),
        ("instruction_offset", 0),
        ("opcode", "invoke-custom"),
        ("reason", "resolved"),
        ("unexpected", True),
    ],
)
def test_equal_dynamic_counts_cannot_hide_wrong_payload(gate, index, tmp_path, field, value):
    row = {**unresolved(), field: value}
    with closing(sqlite3.connect(index)) as db, db:
        db.execute("UPDATE dynamic SET data=?", (zlib.compress(compact(row)),))
        assert db.execute("SELECT count(*) FROM dynamic").fetchone()[0] == 1
    with pytest.raises(AssertionError, match="dynamic multiset"):
        gate.compare_index(index, iter(independent_records()), tmp_path)


@pytest.mark.parametrize(
    "payload",
    [
        [4, "invoke-polymorphic", "(I)I"],
        [3, "invoke-polymorphic/range", "(I)I"],
        [3, "invoke-polymorphic", "(J)J"],
        [3, "invoke-polymorphic", None],
        [3, "invoke-polymorphic", "(I)I", "ignored"],
    ],
)
def test_call_content_and_polymorphic_prototype_are_exact(gate, index, tmp_path, payload):
    with closing(sqlite3.connect(index)) as db, db:
        db.execute("UPDATE edges SET data=? WHERE id=2", (compact(payload),))
    with pytest.raises(AssertionError):
        gate.compare_index(index, iter(independent_records()), tmp_path)


def test_no_calls_is_a_real_empty_multiset_not_null(gate, index, tmp_path):
    with closing(sqlite3.connect(index)) as db, db:
        db.execute("DELETE FROM edges")
        db.execute("DELETE FROM dynamic")
    rows = [row for row in independent_records() if row[0] == "methods"]
    result = gate.compare_index(index, rows, tmp_path)
    assert result["total_call_sites"] == result["dynamic_sites"] == 0
    assert result["site_multiset_sha256"] == hashlib.sha256().hexdigest()


@pytest.fixture
def acceptance_inputs(gate, index, tmp_path, monkeypatch):
    # A source-provenance unit fixture; decoder behavior is tested separately.
    original, bundle = tmp_path / "original.apk", tmp_path / "canonical.apk"
    raw = bytearray(112)
    raw[:8] = b"dex\n039\0"
    struct.pack_into("<I", raw, 96, 1)
    sources = []
    with zipfile.ZipFile(original, "w") as archive, zipfile.ZipFile(bundle, "w") as canonical:
        # Lexicographic source order is deliberately different from numeric order.
        for number, name in enumerate(("classes10.dex", "classes2.dex"), 1):
            data = bytes(raw) + bytes([number])
            entry = "classes.dex" if number == 1 else "classes2.dex"
            archive.writestr(name, data)
            canonical.writestr(entry, data)
            sources.append(
                {
                    "path": str(original),
                    "container_entry": name,
                    "dex_entry": entry,
                    "size_bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "dex_version": "039",
                    "declared_class_count": 1,
                }
            )
    monkeypatch.setattr(gate, "decoder_identity", lambda: {"name": "test-only-decoder"})
    monkeypatch.setattr(gate, "runtime_identity", lambda: {"runtime.py": "runtime-digest"})
    monkeypatch.setattr(gate, "verifier_identity", lambda: {"verifier.py": "verifier-digest"})
    monkeypatch.setattr(gate, "verify_index", lambda *args: {"total_call_sites": 2})
    return original, bundle, index, sources, tmp_path


def accept(gate, inputs):
    return gate.accept_index(*inputs, byte_limit=4096)


def test_original_mapping_is_accepted_and_bound_without_changing_input(gate, acceptance_inputs):
    receipt = accept(gate, acceptance_inputs)
    gate.validate_acceptance(receipt, *acceptance_inputs[:4])
    assert receipt["sources"][0]["container_entry"] == "classes10.dex"
    assert receipt["sources"][0]["dex_entry"] == "classes.dex"
    assert receipt["original_unchanged"] and receipt["runtime_unchanged"]


@pytest.mark.parametrize(
    "fault",
    [
        "omitted",
        "duplicated",
        "mapping",
        "hash",
        "size",
        "path",
        "version",
        "class_count",
        "bundle_bytes",
        "bundle_inventory",
        "extra_original",
        "duplicate_original",
        "041",
    ],
)
def test_source_inventory_and_canonical_original_bytes_are_independently_checked(
    gate, acceptance_inputs, fault
):
    original, bundle, index, sources, workspace = acceptance_inputs
    if fault == "omitted":
        sources.pop()
    elif fault == "duplicated":
        sources.append(copy.deepcopy(sources[0]))
    elif fault == "mapping":
        sources[0]["container_entry"], sources[1]["container_entry"] = (
            sources[1]["container_entry"],
            sources[0]["container_entry"],
        )
    elif fault in {"hash", "size", "path", "version", "class_count"}:
        field, value = {
            "hash": ("sha256", "0" * 64),
            "size": ("size_bytes", 999),
            "path": ("path", str(workspace / "other.apk")),
            "version": ("dex_version", "035"),
            "class_count": ("declared_class_count", 999),
        }[fault]
        sources[0][field] = value
    elif fault == "bundle_bytes":
        with zipfile.ZipFile(bundle, "w") as archive:
            archive.writestr("classes.dex", b"corrupt")
            archive.writestr("classes2.dex", b"corrupt")
    elif fault == "bundle_inventory":
        with zipfile.ZipFile(bundle, "a") as archive:
            archive.writestr("classes3.dex", b"unexpected")
    elif fault in {"extra_original", "duplicate_original"}:
        with zipfile.ZipFile(original, "a") as archive:
            name = "assets/extra.dex" if fault == "extra_original" else "classes2.dex"
            if fault == "duplicate_original":
                with pytest.warns(UserWarning, match="Duplicate name"):
                    archive.writestr(name, b"unexpected")
            else:
                archive.writestr(name, b"unexpected")
    else:
        with zipfile.ZipFile(original) as archive:
            records = [(name, archive.read(name)) for name in archive.namelist()]
        with zipfile.ZipFile(original, "w") as archive, zipfile.ZipFile(bundle, "w") as canonical:
            for row, (name, data) in zip(sources, records, strict=True):
                data = b"dex\n041\0" + data[8:]
                row.update(sha256=hashlib.sha256(data).hexdigest(), dex_version="041")
                archive.writestr(name, data)
                canonical.writestr(row["dex_entry"], data)
    with pytest.raises(AssertionError):
        gate.accept_index(original, bundle, index, sources, workspace, byte_limit=4096)


@pytest.mark.parametrize(
    "fault",
    [
        "original",
        "bundle",
        "index",
        "source",
        "runtime",
        "verifier",
        "decoder",
        "status",
        "scope",
        "input_id",
        "engine",
    ],
)
def test_graph_replay_rejects_stale_or_differently_bound_acceptance(
    gate, acceptance_inputs, monkeypatch, fault
):
    receipt = accept(gate, acceptance_inputs)
    if fault in {"original", "bundle", "index"}:
        path = acceptance_inputs[{"original": 0, "bundle": 1, "index": 2}[fault]]
        with path.open("ab") as stream:
            stream.write(b"changed")
    elif fault == "source":
        acceptance_inputs[3][0]["container_entry"] = "classes9.dex"
    elif fault in {"runtime", "verifier", "decoder"}:
        monkeypatch.setattr(gate, fault + "_identity", lambda: {"changed": True})
    else:
        receipt[{"engine": "engine_version"}.get(fault, fault)] = "changed"
    with pytest.raises(AssertionError):
        gate.validate_acceptance(receipt, *acceptance_inputs[:4])


def test_engine_and_source_hashes_must_reproduce_input_id(gate, acceptance_inputs):
    sources = acceptance_inputs[3]
    engine = "fixture-engine"
    identity = {"schema": 1, "engine": engine, "dex_sha256": [r["sha256"] for r in sources]}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    receipt = gate.accept_index(
        *acceptance_inputs, byte_limit=4096, input_id=key, engine_version=engine
    )
    gate.validate_acceptance(receipt, *acceptance_inputs[:4], input_id=key, engine_version=engine)
    with pytest.raises(AssertionError, match="Input ID"):
        gate.accept_index(
            *acceptance_inputs, byte_limit=4096, input_id="wrong", engine_version=engine
        )


def test_empty_prototype_is_not_silently_normalized_to_absent(gate, index, tmp_path):
    with closing(sqlite3.connect(index)) as db, db:
        db.execute("UPDATE edges SET data=? WHERE id=1", (compact([0, "invoke-static", ""]),))
    with pytest.raises(AssertionError, match="Unexpected prototype"):
        gate.compare_index(index, independent_records(), tmp_path)


def test_native_graph_fixture_matches_hand_counted_full_inventory(gate, graph_dex_files, tmp_path):
    from droidasc_mcp.config import Settings
    from droidasc_mcp.native_index import build

    bundle, index = tmp_path / "graph.apk", tmp_path / "calls.sqlite"
    with zipfile.ZipFile(bundle, "w") as archive:
        for number, path in enumerate(graph_dex_files, 1):
            archive.write(path, "classes.dex" if number == 1 else "classes2.dex")
    build(Settings.from_env(), bundle, index, tmp_path, {}, calls_only=True)
    a, b = "Lgraph/A;->", "Lgraph/B;->"
    dynamic = a + "dynamic(Ljava/lang/invoke/MethodHandle;)V"
    calls = [
        (a + "root()V", b + "step(I)V", 1),
        (a + "root()V", b + "step(I)V", 4),
        (a + "root()V", b + "step(Ljava/lang/String;)V", 9),
        (a + "root()V", "Lexternal/Missing;->absent()V", 12),
        (a + "root()V", dynamic, 16),
        (a + "loop()V", a + "root()V", 0),
        (a + "entry()V", a + "root()V", 0),
        (a + "recursive()V", a + "recursive()V", 0),
        (b + "step(I)V", a + "loop()V", 0),
    ]
    records = [
        (
            "calls",
            compact(
                [
                    "classes2.dex" if caller.startswith(b) else "classes.dex",
                    caller,
                    callee,
                    offset,
                    "invoke-static",
                    "",
                ]
            ),
        )
        for caller, callee, offset in calls
    ]
    records.append(
        (
            "calls",
            compact(
                [
                    "classes.dex",
                    dynamic,
                    POLY,
                    1,
                    "invoke-polymorphic",
                    "(I)I",
                ]
            ),
        )
    )
    for caller, count, without in [
        (a + "root()V", 9, 0),
        (a + "loop()V", 2, 0),
        (a + "entry()V", 2, 0),
        (a + "recursive()V", 2, 0),
        (dynamic, 3, 0),
        (a + "noCode()V", 0, 1),
        (a + "custom()V", 2, 0),
        (b + "step(I)V", 2, 0),
        (b + "step(Ljava/lang/String;)V", 1, 0),
    ]:
        entry = "classes2.dex" if caller.startswith(b) else "classes.dex"
        records.append(("methods", compact([entry, caller, count, without])))
    for caller, offset, opcode in [
        (dynamic, 1, "invoke-polymorphic"),
        (a + "custom()V", 0, "invoke-custom"),
    ]:
        records.append(
            (
                "dynamic",
                compact(
                    [
                        "classes.dex",
                        caller,
                        unresolved(caller=caller, offset=offset, opcode=opcode),
                    ]
                ),
            )
        )
    result = gate.compare_index(index, records, tmp_path)
    assert result["total_call_sites"] == 10 and result["methods"] == 9
    assert result["scanned_instructions"] == 23 and result["dynamic_sites"] == 2
