"""Bounded disk ownership, exact duplicate detection and UTF-16 pagination."""

import json

import pytest


def test_directory_roundtrip_order_prefix_and_duplicates(tmp_path):
    from droidasc_mcp.class_directory import ClassDirectory
    from droidasc_mcp.native_dex import utf16_key

    names = [
        "Lz/Z;",
        "La/\uffff;",
        "La/\U0001f600;",
        "La/\ud800;",
        "La/A;",
        "La/\0;",
        'Lquoted/"\\\t\r\n;',
    ]
    path = tmp_path / "owners.sqlite"
    with ClassDirectory(path, budget=1024**2) as directory:
        assert directory.add(names, "classes.dex") == []
        assert directory.metadata_bytes == len(json.dumps(dict.fromkeys(names, "classes.dex")))
        assert directory.add([names[0], "Lb/B;"], "classes2.dex") == [
            {"class_name": names[0], "dex_entries": ["classes.dex", "classes2.dex"]}
        ]
        assert len(directory) == len(names) + 1
        expected = dict.fromkeys(names, "classes.dex") | {"Lb/B;": "classes2.dex"}
        assert directory.metadata_bytes == len(json.dumps(expected))
    with ClassDirectory(path) as directory:
        assert directory[names[0]] == "classes.dex"
        assert "Lmissing/Type;" not in directory
        with pytest.raises(KeyError):
            directory["Lmissing/Type;"]
        total, rows = directory.page(None, 0, 100)
        assert total == len(names) + 1
        assert [row["class_name"] for row in rows] == sorted(names + ["Lb/B;"], key=utf16_key)
        total, rows = directory.page("La/", 1, 2)
        assert total == 5
        assert [row["class_name"] for row in rows] == sorted(names[1:], key=utf16_key)[1:3]
        assert directory.page("La/\uffff", 0, 1)[1][0]["class_name"] == "La/\uffff;"
        assert directory.page(None, 2**100, 1) == (len(names) + 1, [])
        # Returned identifiers remain JSON-safe, even for unpaired DEX surrogates.
        assert (
            json.loads(json.dumps(directory.page(None, 0, 100)[1]))
            == directory.page(None, 0, 100)[1]
        )
    assert not list(tmp_path.glob("*-journal"))


def test_directory_budget_and_read_only_reopen(tmp_path):
    from droidasc_mcp.class_directory import ClassDirectory

    path = tmp_path / "owners.sqlite"
    with (
        ClassDirectory(path, budget=16384) as directory,
        pytest.raises(ValueError, match="metadata exceeds budget"),
    ):
        directory.add([f"Lfixture/{i:08d};" for i in range(10000)], "classes.dex")
    missing = tmp_path / "missing.sqlite"
    with pytest.raises(ValueError, match="class directory"), ClassDirectory(missing):
        pass
    assert not missing.exists()


def test_directory_publishes_bounded_batches_not_one_statement_per_class(tmp_path):
    from droidasc_mcp.class_directory import ClassDirectory

    names = [f"Lfixture/{i:08d};" for i in range(1041)]
    path = tmp_path / "batch.sqlite"
    statements = []
    with ClassDirectory(path, budget=1024**2) as directory:
        directory.connection.set_trace_callback(statements.append)
        assert directory.add(names, "classes.dex") == []
        inserts = [
            statement
            for statement in statements
            if statement.startswith("INSERT OR IGNORE INTO classes")
        ]
        assert len(inserts) <= (len(names) + 127) // 128
        assert directory.metadata_bytes == len(json.dumps(dict.fromkeys(names, "classes.dex")))
        assert directory.page(None, 128, 2)[1] == [
            {"class_name": name, "dex_entry": "classes.dex"} for name in names[128:130]
        ]
    assert path.stat().st_size <= 2 * 1024**2 + 8192


def test_compact_keys_match_utf16_order_roundtrip_and_partial_prefix(tmp_path):
    import random

    from droidasc_mcp.class_directory import ClassDirectory, decode_key, key

    units = [
        0,
        1,
        127,
        128,
        255,
        0x7FF,
        0x800,
        0xD7FF,
        0xD800,
        0xDBFF,
        0xDC00,
        0xDFFF,
        0xE000,
        0xFFFF,
    ]
    rng = random.Random(1937)
    names = {"L" + chr(value) for value in units}
    for _ in range(5000):
        raw = b"".join(rng.choice(units).to_bytes(2, "big") for _ in range(rng.randrange(1, 12)))
        names.add("L" + raw.decode("utf-16-be", "surrogatepass"))
    names.update(["L\U00010000;", "L\U0010ffff;", "L\U0001f600;", "L\ud800", "L\ud800a"])
    expected = sorted(names, key=lambda text: text.encode("utf-16-be", "surrogatepass"))
    assert sorted(names, key=key) == expected
    assert [decode_key(key(name)) for name in expected] == expected
    with ClassDirectory(tmp_path / "compact.sqlite", budget=16 * 1024**2) as directory:
        assert directory.add(expected, "classes.dex") == []
        for prefix in ["L", "L\ud800", "L\udbff", "L\U0001f600", "L\uffff", "missing"]:
            # Prefix matching is defined on UTF-16 code units, like the old directory.
            wanted = [
                name
                for name in expected
                if name.encode("utf-16-be", "surrogatepass").startswith(
                    prefix.encode("utf-16-be", "surrogatepass")
                )
            ]
            total, rows = directory.page(prefix, 0, len(names))
            assert total == len(wanted)
            assert [row["class_name"] for row in rows] == wanted


@pytest.mark.parametrize("version", [0, 1, 3])
def test_legacy_keys_read_only_compatibility_and_unknown_format_rejected(tmp_path, version):
    import sqlite3
    from contextlib import closing

    from droidasc_mcp.class_directory import ClassDirectory, key

    path = tmp_path / "legacy.sqlite"
    names = ["La/A;", "La/\U0001f600;", "La/\ud800;"]
    with closing(sqlite3.connect(path)) as db:
        db.execute("CREATE TABLE classes(name BLOB PRIMARY KEY, entry TEXT NOT NULL) WITHOUT ROWID")
        db.executemany(
            "INSERT INTO classes VALUES (?,?)",
            [
                (
                    name.encode("utf-16-be", "surrogatepass") if version == 0 else key(name),
                    "classes.dex",
                )
                for name in names
            ],
        )
        db.execute(f"PRAGMA user_version={version}")
        db.commit()
    original = path.read_bytes()
    if version == 3:
        with (
            pytest.raises(ValueError, match="Unsupported prepared class directory"),
            ClassDirectory(path),
        ):
            pass
    else:
        with ClassDirectory(path) as directory:
            assert directory[names[1]] == "classes.dex"
            assert directory.page("La/", 0, 3)[0] == 3
            assert {row["class_name"] for row in directory.page(None, 0, 3)[1]} == set(names)
    assert path.read_bytes() == original


def test_owner_names_are_interned_once_per_dex_with_integer_class_references(tmp_path):
    from droidasc_mcp.class_directory import ClassDirectory

    path = tmp_path / "interned.sqlite"
    expected = {}
    with ClassDirectory(path, budget=1024**2) as directory:
        for number in range(1, 65):
            entry = "classes.dex" if number == 1 else f"classes{number}.dex"
            names = [f"Lfixture/dex{number}/Type{index};" for index in range(17)]
            assert directory.add(names, entry) == []
            expected.update(dict.fromkeys(names, entry))
        assert directory.connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert directory.connection.execute("SELECT count(*) FROM entries").fetchone()[0] == 64
        assert (
            directory.connection.execute(
                "SELECT count(*) FROM classes WHERE typeof(entry)!='integer'"
            ).fetchone()[0]
            == 0
        )
        assert directory.metadata_bytes == len(json.dumps(expected))
        with pytest.raises(ValueError, match="DEX entry limit"):
            directory.add([], "classes65.dex")
    with ClassDirectory(path) as directory:
        assert len(directory) == len(expected)
        assert {
            row["class_name"]: row["dex_entry"] for row in directory.page(None, 0, 2000)[1]
        } == expected
        assert all(directory[name] == entry for name, entry in expected.items())


@pytest.mark.parametrize("operation", ["lookup", "page"])
def test_interned_directory_rejects_dangling_owner_ids(tmp_path, operation):
    import sqlite3
    from contextlib import closing

    from droidasc_mcp.class_directory import ClassDirectory

    path = tmp_path / "dangling.sqlite"
    with ClassDirectory(path, budget=65536) as directory:
        directory.add(["Lfixture/Type;"], "classes.dex")
    with closing(sqlite3.connect(path)) as db:
        db.execute("UPDATE classes SET entry=9999")
        db.commit()
    with ClassDirectory(path) as directory, pytest.raises(ValueError, match="class directory"):
        directory["Lfixture/Type;"] if operation == "lookup" else directory.page(None, 0, 100)


def test_interned_directory_empty_and_small_budget_remain_bounded(tmp_path):
    from droidasc_mcp.class_directory import ClassDirectory

    path = tmp_path / "empty.sqlite"
    with ClassDirectory(path, budget=2) as directory:
        assert directory.add([], "classes.dex") == []
        assert directory.metadata_bytes == 2
        assert directory.connection.execute("PRAGMA user_version").fetchone()[0] == 2
    assert path.stat().st_size <= 2 * 2 + 16384
    with ClassDirectory(path) as directory:
        assert len(directory) == 0
        assert directory.page(None, 0, 100) == (0, [])


@pytest.mark.parametrize("damage", ["id", "empty", "duplicate"])
def test_interned_directory_dictionary_validation(tmp_path, damage):
    import sqlite3
    from contextlib import closing

    from droidasc_mcp.class_directory import ClassDirectory

    path = tmp_path / "dictionary.sqlite"
    with ClassDirectory(path, budget=65536) as directory:
        directory.add(["La/A;"], "classes.dex")
        directory.add(["Lb/B;"], "classes2.dex")
    with closing(sqlite3.connect(path)) as db:
        db.execute(
            {
                "id": "UPDATE entries SET id=65 WHERE id=1",
                "empty": "UPDATE entries SET name='' WHERE id=1",
                "duplicate": "UPDATE entries SET name='classes.dex' WHERE id=2",
            }[damage]
        )
        db.commit()
    original = path.read_bytes()
    with pytest.raises(ValueError, match="class directory"), ClassDirectory(path):
        pass
    assert path.read_bytes() == original
