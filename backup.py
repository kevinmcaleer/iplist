#!/usr/bin/env python3
"""Backup and restore the iplist SQLite database.

Exports the database schema (CREATE TABLE) and all rows (INSERT INTO)
as a plain SQL script that can be piped back in to restore.
"""

import argparse
import sqlite3
import sys
from pathlib import Path

from database import DB_PATH


def _quote(value):
    """Return a SQL-literal representation of *value*."""
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    # Escape single quotes by doubling them
    return "'" + str(value).replace("'", "''") + "'"


def backup(db_path: Path) -> str:
    """Return a SQL script that recreates every table and row in *db_path*."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row

    lines: list[str] = ["-- iplist database backup", ""]

    # Iterate over every user table (skip sqlite internals)
    tables = conn.execute(
        "SELECT name, sql FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    ).fetchall()

    for table in tables:
        table_name = table["name"]
        create_sql = table["sql"]

        # Schema
        lines.append(f"DROP TABLE IF EXISTS {table_name};")
        lines.append(f"{create_sql};")
        lines.append("")

        # Data
        rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
        col_names = [desc[0] for desc in conn.execute(f"SELECT * FROM {table_name} LIMIT 0").description]
        for row in rows:
            values = ", ".join(_quote(row[col]) for col in col_names)
            cols = ", ".join(col_names)
            lines.append(f"INSERT INTO {table_name} ({cols}) VALUES ({values});")

        if rows:
            lines.append("")

    conn.close()
    return "\n".join(lines) + "\n"


def restore(db_path: Path, sql: str) -> None:
    """Execute a SQL backup script against *db_path*, replacing existing data."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(sql)
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Backup or restore the iplist device database."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Write backup SQL to FILE instead of stdout.",
        metavar="FILE",
    )
    parser.add_argument(
        "-r", "--restore",
        type=str,
        default=None,
        help="Restore the database from a SQL backup file.",
        metavar="FILE",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Path to the SQLite database (default: devices.db next to database.py).",
        metavar="PATH",
    )
    args = parser.parse_args()

    db_path = Path(args.db) if args.db else DB_PATH

    if args.restore:
        # --- Restore mode ---
        restore_path = Path(args.restore)
        if not restore_path.exists():
            print(f"Error: file not found: {restore_path}", file=sys.stderr)
            sys.exit(1)
        sql = restore_path.read_text(encoding="utf-8")
        restore(db_path, sql)
        print(f"Database restored from {restore_path}", file=sys.stderr)
    else:
        # --- Backup mode ---
        if not db_path.exists():
            print(f"Error: database not found: {db_path}", file=sys.stderr)
            sys.exit(1)
        sql = backup(db_path)
        if args.output:
            Path(args.output).write_text(sql, encoding="utf-8")
            print(f"Backup written to {args.output}", file=sys.stderr)
        else:
            sys.stdout.write(sql)


if __name__ == "__main__":
    main()
