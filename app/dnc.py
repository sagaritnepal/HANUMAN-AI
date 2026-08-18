"""Do-not-call list — checked before any outbound dial (roadmap standing rule #3).
Global across tenants: a number that opts out stays opted out platform-wide."""
import sqlite3
from datetime import datetime, timezone

from . import config


def _conn():
    conn = sqlite3.connect(config.LEADS_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS dnc_numbers (
            e164       TEXT PRIMARY KEY,
            reason     TEXT,
            added_at   TEXT
        )"""
    )
    return conn


def add(e164: str, reason: str = "") -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO dnc_numbers (e164, reason, added_at) VALUES (?,?,?)",
            (e164, reason, datetime.now(timezone.utc).isoformat()),
        )


def remove(e164: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM dnc_numbers WHERE e164 = ?", (e164,))


def is_listed(e164: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM dnc_numbers WHERE e164 = ?", (e164,)
        ).fetchone()
    return row is not None


def list_all() -> list[dict]:
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM dnc_numbers ORDER BY added_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]
