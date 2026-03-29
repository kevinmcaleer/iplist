"""Tests for backup.py -- backup and restore of the iplist database."""

import sqlite3
import textwrap
from pathlib import Path

import pytest

# Import functions under test
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from backup import backup, restore, _quote


# ---- Fixtures ---------------------------------------------------------------

@pytest.fixture
def db_path(tmp_path):
    """Create a temporary SQLite database with the devices table and sample data."""
    path = tmp_path / "devices.db"
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            mac TEXT PRIMARY KEY,
            ip TEXT,
            hostname TEXT DEFAULT '',
            description TEXT DEFAULT '',
            last_seen TEXT,
            is_online INTEGER DEFAULT 0
        )
    """)
    conn.execute(
        "INSERT INTO devices (mac, ip, hostname, description, last_seen, is_online) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("AA:BB:CC:DD:EE:FF", "192.168.1.10", "myhost", "Living room TV", "2026-03-22T10:00:00", 1),
    )
    conn.execute(
        "INSERT INTO devices (mac, ip, hostname, description, last_seen, is_online) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("11:22:33:44:55:66", "192.168.1.20", "printer", "", "2026-03-22T09:00:00", 0),
    )
    conn.commit()
    conn.close()
    return path


@pytest.fixture
def empty_db_path(tmp_path):
    """Create a temporary SQLite database with the devices table but no data."""
    path = tmp_path / "empty.db"
    conn = sqlite3.connect(str(path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS devices (
            mac TEXT PRIMARY KEY,
            ip TEXT,
            hostname TEXT DEFAULT '',
            description TEXT DEFAULT '',
            last_seen TEXT,
            is_online INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    return path


# ---- _quote -----------------------------------------------------------------

class TestQuote:
    def test_none(self):
        assert _quote(None) == "NULL"

    def test_integer(self):
        assert _quote(0) == "0"
        assert _quote(1) == "1"

    def test_string(self):
        assert _quote("hello") == "'hello'"

    def test_string_with_single_quote(self):
        assert _quote("it's") == "'it''s'"

    def test_empty_string(self):
        assert _quote("") == "''"


# ---- backup -----------------------------------------------------------------

class TestBackup:
    def test_backup_contains_create_table(self, db_path):
        sql = backup(db_path)
        assert "CREATE TABLE" in sql
        assert "devices" in sql

    def test_backup_contains_drop_table(self, db_path):
        sql = backup(db_path)
        assert "DROP TABLE IF EXISTS devices;" in sql

    def test_backup_contains_insert_statements(self, db_path):
        sql = backup(db_path)
        assert "INSERT INTO devices" in sql
        assert "AA:BB:CC:DD:EE:FF" in sql
        assert "11:22:33:44:55:66" in sql

    def test_backup_empty_table(self, empty_db_path):
        sql = backup(empty_db_path)
        assert "CREATE TABLE" in sql
        # No INSERT statements expected
        assert "INSERT" not in sql

    def test_backup_produces_valid_sql(self, db_path):
        """The backup SQL should be executable against a fresh database."""
        sql = backup(db_path)
        fresh = db_path.parent / "fresh.db"
        conn = sqlite3.connect(str(fresh))
        conn.executescript(sql)
        rows = conn.execute("SELECT * FROM devices ORDER BY mac").fetchall()
        conn.close()
        assert len(rows) == 2

    def test_backup_preserves_values(self, db_path):
        """Round-trip: backup then execute should preserve all column values."""
        sql = backup(db_path)
        fresh = db_path.parent / "fresh.db"
        conn = sqlite3.connect(str(fresh))
        conn.row_factory = sqlite3.Row
        conn.executescript(sql)
        row = dict(conn.execute(
            "SELECT * FROM devices WHERE mac = ?", ("AA:BB:CC:DD:EE:FF",)
        ).fetchone())
        conn.close()
        assert row["ip"] == "192.168.1.10"
        assert row["hostname"] == "myhost"
        assert row["description"] == "Living room TV"
        assert row["is_online"] == 1


# ---- restore ----------------------------------------------------------------

class TestRestore:
    def test_restore_creates_table(self, tmp_path):
        dest = tmp_path / "restored.db"
        sql = textwrap.dedent("""\
            DROP TABLE IF EXISTS devices;
            CREATE TABLE devices (
                mac TEXT PRIMARY KEY,
                ip TEXT
            );
            INSERT INTO devices (mac, ip) VALUES ('AA:BB:CC:DD:EE:FF', '10.0.0.1');
        """)
        restore(dest, sql)
        conn = sqlite3.connect(str(dest))
        rows = conn.execute("SELECT * FROM devices").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "AA:BB:CC:DD:EE:FF"

    def test_restore_replaces_existing_data(self, db_path):
        """Restoring should drop existing tables and recreate them."""
        sql = textwrap.dedent("""\
            DROP TABLE IF EXISTS devices;
            CREATE TABLE devices (
                mac TEXT PRIMARY KEY,
                ip TEXT
            );
            INSERT INTO devices (mac, ip) VALUES ('FF:FF:FF:FF:FF:FF', '10.0.0.99');
        """)
        restore(db_path, sql)
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT * FROM devices").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][0] == "FF:FF:FF:FF:FF:FF"


# ---- round-trip --------------------------------------------------------------

class TestRoundTrip:
    def test_backup_then_restore(self, db_path, tmp_path):
        """Full round-trip: backup a database, restore to a new file, compare."""
        sql = backup(db_path)
        dest = tmp_path / "roundtrip.db"
        restore(dest, sql)

        conn_orig = sqlite3.connect(str(db_path))
        conn_new = sqlite3.connect(str(dest))

        orig_rows = conn_orig.execute("SELECT * FROM devices ORDER BY mac").fetchall()
        new_rows = conn_new.execute("SELECT * FROM devices ORDER BY mac").fetchall()

        conn_orig.close()
        conn_new.close()

        assert orig_rows == new_rows


# ---- CLI (main) via subprocess -----------------------------------------------

class TestCLI:
    def test_backup_to_stdout(self, db_path, monkeypatch):
        """Running main() without --output should write SQL to stdout."""
        import io
        import backup as backup_mod

        monkeypatch.setattr(backup_mod, "DB_PATH", db_path)
        captured = io.StringIO()
        monkeypatch.setattr(sys, "stdout", captured)
        monkeypatch.setattr(sys, "argv", ["backup.py"])

        backup_mod.main()
        output = captured.getvalue()
        assert "CREATE TABLE" in output
        assert "INSERT INTO" in output

    def test_backup_to_file(self, db_path, tmp_path, monkeypatch):
        import backup as backup_mod

        out_file = tmp_path / "out.sql"
        monkeypatch.setattr(backup_mod, "DB_PATH", db_path)
        monkeypatch.setattr(sys, "argv", ["backup.py", "-o", str(out_file)])

        backup_mod.main()
        assert out_file.exists()
        contents = out_file.read_text()
        assert "CREATE TABLE" in contents

    def test_restore_from_file(self, db_path, tmp_path, monkeypatch):
        import backup as backup_mod

        # First create a backup file
        sql = backup(db_path)
        backup_file = tmp_path / "backup.sql"
        backup_file.write_text(sql)

        # Restore to a fresh database
        dest = tmp_path / "restored.db"
        monkeypatch.setattr(sys, "argv", ["backup.py", "--restore", str(backup_file), "--db", str(dest)])

        backup_mod.main()
        conn = sqlite3.connect(str(dest))
        rows = conn.execute("SELECT * FROM devices ORDER BY mac").fetchall()
        conn.close()
        assert len(rows) == 2

    def test_restore_missing_file(self, tmp_path, monkeypatch):
        import backup as backup_mod

        monkeypatch.setattr(sys, "argv", ["backup.py", "--restore", str(tmp_path / "nope.sql")])

        with pytest.raises(SystemExit) as exc_info:
            backup_mod.main()
        assert exc_info.value.code == 1

    def test_backup_missing_db(self, tmp_path, monkeypatch):
        import backup as backup_mod

        monkeypatch.setattr(backup_mod, "DB_PATH", tmp_path / "nope.db")
        monkeypatch.setattr(sys, "argv", ["backup.py"])

        with pytest.raises(SystemExit) as exc_info:
            backup_mod.main()
        assert exc_info.value.code == 1
