"""
Tenant management — each tenant is one customer company with its own agent.

Pilot phase: SQLite (same DB file as leads). The Postgres schema for scale
is in db/schema.sql; this module's interface stays the same when you switch.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass, field, asdict

from . import config

DEFAULT_TENANT_ID = "default"


@dataclass
class TenantConfig:
    tenant_id: str
    company_name: str = "Your Company"
    agent_name: str = "Asha"
    language: str = "auto"                 # auto | ne | en
    greeting: str = ""                     # optional custom opening line
    facts: str = ""                        # company facts/FAQ the agent may state
    questions: list = field(default_factory=lambda: [
        "caller's name",
        "what product or service they are interested in",
        "their approximate budget",
        "their timeline",
    ])
    lead_fields: list = field(default_factory=lambda: [
        "name", "phone", "interest", "budget", "timeline", "qualified", "notes",
    ])
    transfer_to: str = ""                  # human handoff number, if any
    status: str = "active"                 # active | suspended
    included_minutes: int = 1000
    api_key: str = ""                      # tenant portal login key (auto-generated)

    def to_dict(self) -> dict:
        return asdict(self)


def _conn():
    conn = sqlite3.connect(config.LEADS_DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS tenants (
            tenant_id TEXT PRIMARY KEY,
            config    TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS phone_numbers (
            e164      TEXT PRIMARY KEY,
            tenant_id TEXT NOT NULL
        )"""
    )
    return conn


def save(cfg: TenantConfig) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO tenants (tenant_id, config) VALUES (?, ?)",
            (cfg.tenant_id, json.dumps(cfg.to_dict(), ensure_ascii=False)),
        )


def get(tenant_id: str) -> TenantConfig | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT config FROM tenants WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()
    if row is None:
        return None
    data = json.loads(row[0])
    return TenantConfig(**data)


def get_or_default(tenant_id: str | None) -> TenantConfig:
    """Resolve a tenant; fall back to a default built from .env settings."""
    if tenant_id:
        cfg = get(tenant_id)
        if cfg is not None:
            return cfg
    return TenantConfig(
        tenant_id=DEFAULT_TENANT_ID,
        company_name=config.COMPANY_NAME,
        agent_name=config.AGENT_NAME,
        language=config.DEFAULT_LANGUAGE,
    )


def list_all() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT config FROM tenants").fetchall()
    return [json.loads(r[0]) for r in rows]


def create(company_name: str, **overrides) -> TenantConfig:
    cfg = TenantConfig(
        tenant_id=str(uuid.uuid4())[:8],
        company_name=company_name,
        **overrides,
    )
    if not cfg.api_key:
        cfg.api_key = "tk_" + uuid.uuid4().hex        # portal login key
    save(cfg)
    return cfg


def get_by_api_key(api_key: str) -> TenantConfig | None:
    """Portal login: resolve a tenant from its API key."""
    if not api_key:
        return None
    for data in list_all():
        if data.get("api_key") and data["api_key"] == api_key:
            return TenantConfig(**data)
    return None


def delete(tenant_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM tenants WHERE tenant_id = ?", (tenant_id,))
        conn.execute("DELETE FROM phone_numbers WHERE tenant_id = ?", (tenant_id,))


# --- phone number → tenant mapping (how inbound calls find their agent) ---

def map_number(e164: str, tenant_id: str) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO phone_numbers (e164, tenant_id) VALUES (?, ?)",
            (e164, tenant_id),
        )


def tenant_for_number(e164: str) -> str | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT tenant_id FROM phone_numbers WHERE e164 = ?", (e164,)
        ).fetchone()
    return row[0] if row else None
