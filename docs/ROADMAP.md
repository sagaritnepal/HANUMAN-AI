# Execution Roadmap — Nepali AI Call Platform

Team: 4 engineers. Strategy: prove it on ourselves → pilot with BYO-number customers (pure software, no licensing risk) → resolve NTA question → scale with platform-owned trunks. Each phase has a **gate** — do not advance until the gate passes.

## Phase 0 — Working agent, zero telephony (Week 1-2)

- Run `test_call.py`; tune `prompts/system_prompt.md` with our real company script (Nepali + English).
- Switch to Claude Haiku; measure cost per simulated call (target ≤ $0.015).
- Stand up Whisper (small) + Piper on the Cloud Himalaya VPS; test Nepali STT accuracy with recorded voice notes from the team.
- **Owner split:** 1 eng on prompt/agent quality, 1 on Whisper/Piper, 1 on VPS/deploy, 1 starts dashboard skeleton.
- **Gate:** a teammate can hold a natural 3-min Nepali voice conversation (mic → Whisper → agent → Piper) with correct lead capture, cost ≤ $0.015/call.

## Phase 1 — Our own agent on a real phone line (Week 3-6)

- Contact NTC enterprise + Ncell Business: SIP trunk pricing, DID numbers, and (critical) **ask in writing about third-party resale/NTA authorization requirements**. Engage a telecom lawyer the same week.
- Install Asterisk on VPS; bridge trunk ⇄ media worker ⇄ `/ws/chat`.
- Real inbound calls to our company answered by the agent; leads in DB; daily transcript review to fix prompt failures.
- Optional: 50-100 Twilio test calls first if trunk paperwork is slow (budget ~$40).
- **Gate:** 100 real calls handled with >80% completed conversations, latency gap < 2s, zero dropped-call bugs for a week.

## Phase 2 — Multi-tenant pilot, BYO numbers (Month 2-4)

- Implement ARCHITECTURE.md: Postgres schema, tenant-scoped agent core, dashboard v1 (script editor, leads list, usage).
- Recruit 5-10 pilot companies (clinics, travel agencies, real-estate, coaching centers — high missed-call pain). They bring their own NTC/Ncell number/trunk; we charge a founder-price (e.g., NPR 1,500/mo) or free-for-feedback.
- Weekly: review every pilot tenant's worst 5 calls; fix prompts/platform.
- Metering + eSewa/Khalti billing integration.
- **Gate:** ≥5 paying-intent pilots, ≥70% of their callers complete the flow, unit cost per tenant-month ≤ $8, and the NTA/legal answer is documented.

## Phase 3 — Commercial launch (Month 4-8)

Pricing (adjust to pilot learnings):

| Plan | NPR/mo (~USD) | Included | Target |
|---|---|---|---|
| Starter | 2,500 (~$18) | 500 inbound min | small shops, clinics |
| Business | 6,500 (~$48) | 2,000 min + outbound add-on | SMEs, agencies |
| Pro | 15,000+ (~$110) | 6,000 min, priority voices, CRM webhooks | call-center replacement |

Outbound: always metered add-on at trunk cost + margin. Never unlimited.

- If NTA answer permits: platform-owned trunk + DID inventory so tenants get a number instantly at signup. If not: stay BYO-number (still a real business) while pursuing authorization.
- Self-serve onboarding: signup → describe business → agent auto-drafts the tenant prompt → test call in browser → go live.
- Scale infra per ARCHITECTURE §5 as concurrency grows (GPU node ~30 concurrent).
- **Gate:** 100 paying tenants, gross margin ≥ 60%, churn < 5%/mo.

## Phase 4 — Scale to 1,000+ (Month 8-18)

- Sales motion: local business associations, chambers of commerce, telco partnership (pitch NTC/Ncell on bundling — they win on trunk minutes).
- Product deepening: appointment booking (calendar integration), order-taking, payment collection via FonePay link SMS, CRM integrations, analytics.
- Reliability: multi-node failover, 99.9% target, on-call rotation.
- Revenue at 1,000 tenants ≈ NPR 3-4M/mo (~$25-30k). Infra + API costs ≈ $6-9k. Fund 2-3 more hires.

## Standing rules (all phases)

1. No SIM boxes/GSM gateways, ever. Licensed trunks only.
2. Agent always admits it's an AI when asked. Recording disclosure on every recorded call.
3. Do-not-call list enforced before any outbound dial.
4. Every phase gate includes a cost-per-call measurement — margin is the business.
5. Legal checkpoint before each phase: lawyer reviews what we're about to do, not what we did.

## Immediate next actions (this week)

1. [Eng] Run Phase 0: `test_call.py` with the real company script.
2. [Founder] Call NTC enterprise & Ncell Business — trunk pricing + resale question in writing.
3. [Founder] Shortlist a Nepali telecom lawyer.
4. [Eng] Benchmark Whisper `small` vs `medium` Nepali accuracy on the VPS.
