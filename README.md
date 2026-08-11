# hanuman.ai — AI Call Platform for Nepal

An AI phone agent powered by Claude. Answers or makes calls, talks to customers in Nepali or English, qualifies leads, and saves them to a database. Runs on your own VPS — the only per-use costs are the Claude API and your phone line.

## How it works

```
Caller ──phone line──> Telephony layer ──text──> FastAPI server ──> Claude (agent brain)
                        (Twilio or SIP/Asterisk)                       │
Caller <──voice──────── TTS <──"say" text────────────────────────────┘
                                          Lead info ──> SQLite (leads.db)
```

The agent brain (`app/agent.py`) is telephony-agnostic. Two ways to connect a real phone line:

**Path A — Twilio (fastest to test).** Twilio provides the number, does speech-to-text and text-to-speech for you. Endpoints `/twilio/voice` and `/twilio/turn` are ready. Note: verify Twilio's current Nepal calling support/rates before committing.

**Path B — SIP trunk from Ncell/NTC enterprise (the proper local setup).** Contact Ncell Business or Nepal Telecom's enterprise division for a SIP trunk (this is how licensed Nepali call centers operate — do NOT use SIM boxes/GSM gateways; unlicensed ones are illegal under NTA rules). Run Asterisk/FreeSWITCH on the VPS, pipe audio through faster-whisper (STT) and piper (TTS), and connect to the `/ws/chat` WebSocket, which speaks plain text in/out.

## Quick start (test with no phone at all)

```bash
git clone <your-repo> && cd nepal-call-agent
python3 -m venv venv && source venv/bin/activate
pip install fastapi uvicorn anthropic python-dotenv   # minimal set for text testing
cp .env.example .env    # then edit: add your ANTHROPIC_API_KEY, company name
python test_call.py     # simulated call in your terminal
```

Type what a caller would say (Nepali or English). The agent replies, and at the end prints the captured lead.

## Run the server

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Endpoints: `/twilio/voice` + `/twilio/turn` (Twilio webhooks), `/ws/chat` (generic text WebSocket), `/leads` (captured leads — add auth before production), `/health`.

## Deploy on Cloud Himalaya VPS (Ubuntu)

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nginx certbot python3-certbot-nginx
# ... clone repo, create venv, install requirements as above ...

# Run as a service
sudo tee /etc/systemd/system/callagent.service > /dev/null <<'EOF'
[Unit]
Description=hanuman.ai Call Platform
After=network.target
[Service]
User=www-data
WorkingDirectory=/opt/nepal-call-agent
ExecStart=/opt/nepal-call-agent/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now callagent

# HTTPS (needed for Twilio webhooks): point a domain at the VPS, then
sudo certbot --nginx -d calls.yourdomain.com.np
```

Nginx should proxy `https://calls.yourdomain.com.np` → `http://127.0.0.1:8000` (include WebSocket upgrade headers for `/ws/chat`).

## Nepali speech notes

- **STT:** faster-whisper `small` handles Nepali reasonably; `medium` is better if your VPS has ≥8 GB RAM. Twilio's built-in STT does not support Nepali — for Nepali calls use Path B with Whisper.
- **TTS:** Piper has community Nepali voices (check the piper-voices repo); quality varies. For better Nepali TTS consider Google Cloud TTS (`ne-NP` voices, pay-per-character).

## Costs (approx.)

- Claude API: a few NPR per call turn with claude-sonnet-5 (each turn is one small request).
- Telephony: Twilio per-minute rates, or your Ncell/NTC SIP trunk contract.
- VPS + Whisper/Piper: fixed monthly cost, no per-call fee.

## Legal / compliance checklist (Nepal)

- Use a licensed telephony route (SIP trunk / registered provider). No SIM boxes.
- For outbound marketing calls, check NTA rules on unsolicited calls and keep a do-not-call list.
- The agent is instructed to admit it's an AI when asked — keep that; it builds trust and avoids deception complaints.
- Protect `/leads` and `leads.db` — it contains customer personal data.

## Multi-tenant platform (serve many companies)

- `/admin` — your operations dashboard (auth: `ADMIN_API_KEY` from .env). Create tenant companies, edit their agents, map phone numbers, see all leads. Creating a tenant generates its portal access key (`tk_...`) — give that key to the customer.
- `/portal` — the customer-facing app (web + mobile). Customers sign in with their key to see leads, edit their agent's script, and test-chat with their agent. It's a PWA: on a phone, "Add to Home Screen" installs it like a native app.
- Number routing: map each tenant's phone number in `/admin`; inbound calls to that number automatically get that tenant's agent.
- `python test_call.py <tenant_id>` tests a specific tenant's agent in the terminal.

## Customize

- `prompts/system_prompt.md` — the agent's personality, script, and qualification questions.
- `.env` — company name, agent name, language mode, model.
- `app/agent.py` → `Lead` dataclass — add/remove fields you want captured.
