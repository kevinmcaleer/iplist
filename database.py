import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "devices.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = get_conn()
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


def upsert_device(mac: str, ip: str, hostname: str, last_seen: str) -> None:
    conn = get_conn()
    conn.execute("""
        INSERT INTO devices (mac, ip, hostname, last_seen, is_online)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(mac) DO UPDATE SET
            ip = excluded.ip,
            hostname = excluded.hostname,
            last_seen = excluded.last_seen,
            is_online = 1
    """, (mac, ip, hostname, last_seen))
    conn.commit()
    conn.close()


def mark_all_offline() -> None:
    conn = get_conn()
    conn.execute("UPDATE devices SET is_online = 0")
    conn.commit()
    conn.close()


def get_all_devices(online_only: bool = False) -> list[dict]:
    conn = get_conn()
    sql = "SELECT * FROM devices"
    if online_only:
        sql += " WHERE is_online = 1"
    sql += " ORDER BY is_online DESC, ip ASC"
    rows = conn.execute(sql).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_device(mac: str, description: str | None = None, hostname: str | None = None) -> bool:
    conn = get_conn()
    fields = []
    values = []
    if description is not None:
        fields.append("description = ?")
        values.append(description)
    if hostname is not None:
        fields.append("hostname = ?")
        values.append(hostname)
    if not fields:
        conn.close()
        return False
    values.append(mac)
    cur = conn.execute(f"UPDATE devices SET {', '.join(fields)} WHERE mac = ?", values)
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated


def delete_device(mac: str) -> bool:
    conn = get_conn()
    cur = conn.execute("DELETE FROM devices WHERE mac = ?", (mac,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted
