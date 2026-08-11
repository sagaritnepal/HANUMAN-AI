# Multi-Tenant AI Call Platform — Architecture

Goal: one platform serving 1,000+ Nepali companies, each with their own AI call agent, at ~$20/month base plans. This document is the technical blueprint; see ROADMAP.md for sequencing.

## 1. System overview

```
                        ┌──────────────────────── PSTN / Mobile network ───────────────────────┐
                        │   Customers' phones (Ncell / NTC subscribers)                        │
                        └───────────────┬──────────────────────────────────────────────────────┘
                                        │ SIP trunk(s)  (NTC/Ncell enterprise — ours, or tenant's own)
                        ┌───────────────▼──────────────┐
                        │  TELEPHONY EDGE               │
                        │  Asterisk / FreeSWITCH        │  maps DID (phone number) → tenant_id
                        │  (1 node per ~50 concurrent)  │
                        └───────────────┬──────────────┘
                                        │ audio (RTP) ⇄ text
                  ┌─────────────────────▼─────────────────────┐
                  │  MEDIA WORKERS (scale horizontally)        │
                  │  STT: faster-whisper (GPU node at scale)   │
                  │  TTS: Piper (Nepali + English voices)      │
                  │  VAD + barge-in handling                   │
                  └─────────────────────┬─────────────────────┘
                                        │ text turns (WebSocket — existing /ws/chat protocol)
                  ┌─────────────────────▼─────────────────────┐
                  │  AGENT CORE (FastAPI, stateless, N pods)   │
                  │  loads tenant config → builds prompt →     │
                  │  Claude Haiku (prompt-cached) → envelope   │
                  └──────┬──────────────────────┬─────────────┘
                         │                      │
            ┌────────────▼───────┐   ┌──────────▼──────────────┐
            │  POSTGRES           │   │  REDIS                  │
            │  tenants, numbers,  │   │  active call sessions,  │
            │  leads, usage,      │   │  rate limits, queues    │
            │  billing            │   └─────────────────────────┘
            └────────────┬───────┘
            ┌────────────▼───────────────────────────┐
            │  TENANT DASHBOARD (web app)             │
            │  script editor, leads, recordings,      │
            │  usage & billing (eSewa/Khalti/FonePay) │
            └────────────────────────────────────────┘
```

Design principle: the **agent core stays telephony-agnostic** (it already is — `/ws/chat` text in/out). Everything audio lives in the media workers; everything carrier-related lives at the edge. Each layer scales independently.

## 2. Tenant model

Every request carries a `tenant_id`, resolved at the edge from the dialed number (DID). All data rows are scoped by it. One codebase, one deployment, no per-customer servers.

Per-tenant configuration (editable in dashboard):
- company name, agent name, language mode (ne / en / auto)
- system prompt sections: greeting, business description, FAQ facts, qualification questions
- lead schema (which fields to capture)
- business hours + after-hours behavior
- transfer number (hand hot leads to a human)
- plan, included minutes, current usage

## 3. Database schema (Postgres)

```sql
CREATE TABLE tenants (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name          TEXT NOT NULL,
  status        TEXT NOT NULL DEFAULT 'trial',      -- trial|active|suspended
  plan          TEXT NOT NULL DEFAULT 'starter',    -- starter|business|pro
  included_min  INT  NOT NULL DEFAULT 1000,
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE phone_numbers (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  UUID NOT NULL REFERENCES tenants(id),
  e164       TEXT UNIQUE NOT NULL,                  -- +97714XXXXXX
  trunk      TEXT NOT NULL,                         -- 'platform' | 'byo'
  direction  TEXT NOT NULL DEFAULT 'inbound'        -- inbound|outbound|both
);

CREATE TABLE agent_configs (
  tenant_id   UUID PRIMARY KEY REFERENCES tenants(id),
  agent_name  TEXT NOT NULL DEFAULT 'Asha',
  language    TEXT NOT NULL DEFAULT 'auto',
  greeting    TEXT,
  facts       TEXT,                                 -- company FAQ the agent may state
  questions   JSONB,                                -- qualification questions, ordered
  lead_schema JSONB,                                -- fields to capture
  transfer_to TEXT,                                 -- E.164 or null
  hours       JSONB                                 -- business hours
);

CREATE TABLE calls (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    UUID NOT NULL REFERENCES tenants(id),
  direction    TEXT NOT NULL,
  caller       TEXT,
  started_at   TIMESTAMPTZ NOT NULL,
  duration_sec INT,
  outcome      TEXT,                                -- qualified|not_interested|voicemail|transferred|error
  transcript   JSONB,
  recording_url TEXT
);

CREATE TABLE leads (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  UUID NOT NULL REFERENCES tenants(id),
  call_id    UUID REFERENCES calls(id),
  data       JSONB NOT NULL,                        -- matches tenant lead_schema
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE usage_monthly (
  tenant_id  UUID REFERENCES tenants(id),
  month      DATE,
  minutes    NUMERIC DEFAULT 0,
  calls      INT DEFAULT 0,
  claude_usd NUMERIC DEFAULT 0,
  PRIMARY KEY (tenant_id, month)
);

CREATE INDEX ON calls (tenant_id, started_at DESC);
CREATE INDEX ON leads (tenant_id, created_at DESC);
```

## 4. Prompt strategy (cost control — this is where margin lives)

- Model: **Claude Haiku** for live turns. Escalate to Sonnet only for flagged-complex tenants.
- **Prompt caching:** structure the system prompt as [static platform rules] + [tenant block]. The static part is identical across all tenants → cached across the fleet. Tenant block is small (~300-800 tokens).
- Cap history: summarize after ~12 turns to keep input tokens flat on long calls.
- Target: ≤ $0.012 per average call. Meter actual spend per tenant into `usage_monthly.claude_usd`.

## 5. Concurrency & capacity planning

| Metric | Estimate |
|---|---|
| 1,000 tenants × ~600 calls/mo avg | ~600k calls/mo ≈ 20k/day |
| Peak concurrent calls (10-1pm NPT peak) | ~150-250 |
| Asterisk edge nodes (50 concurrent each) | 3-5 small VPS |
| Whisper capacity | 1× GPU server (~40-60 streams) or ~30 CPU cores; start CPU, move to GPU past ~30 concurrent |
| Agent core pods | stateless; 2-3 small instances behind nginx |
| Postgres + Redis | 1 primary + replica; trivial load at this scale |

Start: everything on the existing Cloud Himalaya VPS. Split layers onto separate nodes only when metrics say so. Keep media workers in-country (latency to callers matters; Claude API round-trip is the only offshore hop, ~300-500ms — acceptable if TTS starts streaming immediately).

## 6. Latency budget (target < 1.5s response gap)

caller stops speaking → VAD 200ms → Whisper streaming final 300ms → Claude Haiku first token 400-700ms → Piper starts speaking 150ms. Techniques: stream STT partials, begin TTS on first sentence of Claude output, play brief acknowledgement fillers ("हस्...") when generation exceeds 1s.

## 7. Security & compliance

- Dashboard auth: per-tenant accounts, role-based (owner/staff). API keys per tenant for their own integrations.
- Data isolation: every query tenant-scoped; no cross-tenant reads. Recordings/transcripts encrypted at rest.
- Call recording: play a disclosure line at call start (configurable per tenant).
- AI disclosure: agent admits it is AI when asked (platform-level rule, tenants cannot disable).
- Do-not-call list table (platform-wide + per-tenant) enforced before any outbound dial.
- NTA: platform-owned trunk resale requires authorization — until confirmed, onboard tenants as **BYO-trunk/number** (they contract NTC/Ncell; we are pure software). See ROADMAP Phase gates.

## 8. Billing (Nepal-friendly)

- Plans (see ROADMAP for pricing) metered from `usage_monthly`; suspend gracefully at cap with dashboard warning at 80%.
- Payment rails: eSewa, Khalti, FonePay QR, bank transfer — card-only billing loses Nepali SMEs.
- Overage: per-minute billing in NPR, invoiced monthly.

## 9. What changes in the existing code

The current repo is the seed of the AGENT CORE:
1. `app/agent.py` — add `tenant_config` parameter; build prompt from DB instead of static file; switch default model to Haiku; add caching headers.
2. `app/storage.py` — replace SQLite with Postgres + the schema above (SQLite stays fine for single-tenant pilot).
3. `app/main.py` — `/ws/chat` gains a `tenant_id` handshake message; add `/admin` CRUD for tenant configs.
4. New: `media/` (Whisper+Piper worker), `dashboard/` (web app), `billing/` (metering jobs).
