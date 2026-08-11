"""Per-tenant usage metering — the foundation for billing and plan caps."""
import sqlite3
from datetime import datetime, timezone

from . import config


def _conn():
    conn = sqlite3.connect(config.LEADS_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS usage_monthly (
            tenant_id TEXT,
            month     TEXT,
            calls     INTEGER DEFAULT 0,
            seconds   INTEGER DEFAULT 0,
            PRIMARY KEY (tenant_id, month)
        )"""
    )
    return conn


def _month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def record_call(tenant_id: str, duration_sec: int) -> None:
    with _conn() as conn:
        conn.execute(
            """INSERT INTO usage_monthly (tenant_id, month, calls, seconds)
               VALUES (?, ?, 1, ?)
               ON CONFLICT(tenant_id, month)
               DO UPDATE SET calls = calls + 1, seconds = seconds + excluded.seconds""",
            (tenant_id, _month(), max(0, int(duration_sec))),
        )


def summary(tenant_id: str) -> dict:
    """Current-month usage for one tenant."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT calls, seconds FROM usage_monthly WHERE tenant_id=? AND month=?",
            (tenant_id, _month()),
        ).fetchone()
    calls, seconds = row if row else (0, 0)
    return {
        "month": _month(),
        "calls": calls,
        "minutes": round(seconds / 60, 1),
    }


def all_tenants_summary() -> list[dict]:
    """Current-month usage across all tenants (admin view)."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT tenant_id, calls, seconds FROM usage_monthly WHERE month=?",
            (_month(),),
        ).fetchall()
    return [
        {"tenant_id": t, "calls": c, "minutes": round(s / 60, 1)}
        for t, c, s in rows
    ]


def over_cap(tenant_id: str, included_minutes: int) -> bool:
    return summary(tenant_id)["minutes"] >= included_minutes
