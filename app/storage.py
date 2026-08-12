"""SQLite lead storage — zero-dependency, fine for the pilot phase.
For scale, switch to Postgres using db/schema.sql (same interface)."""
import json
import sqlite3
from datetime import datetime, timezone

from . import config, usage


def _conn():
    conn = sqlite3.connect(config.LEADS_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT,
            call_id TEXT,
            caller_number TEXT,
            created_at TEXT,
            data TEXT,
            transcript TEXT
        )"""
    )
    return conn


def save_session(session) -> None:
    # meter real calls (not portal test chats)
    if session.caller_number != "portal-test":
        try:
            usage.record_call(
                session.tenant.tenant_id, session.duration_sec(), session.cost_usd
            )
        except Exception:
            pass   # metering must never break call handling
    with _conn() as conn:
        conn.execute(
            """INSERT INTO leads
               (tenant_id, call_id, caller_number, created_at, data, transcript)
               VALUES (?,?,?,?,?,?)""",
            (
                session.tenant.tenant_id,
                session.call_id,
                session.caller_number,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(session.lead.to_dict(), ensure_ascii=False),
                json.dumps(session.messages, ensure_ascii=False),
            ),
        )


def list_leads(tenant_id: str | None = None, limit: int = 100) -> list[dict]:
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        if tenant_id:
            rows = conn.execute(
                "SELECT * FROM leads WHERE tenant_id = ? ORDER BY id DESC LIMIT ?",
                (tenant_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM leads ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["data"] = json.loads(d["data"]) if d.get("data") else {}
        d.pop("transcript", None)   # keep list endpoint light
        out.append(d)
    return out
