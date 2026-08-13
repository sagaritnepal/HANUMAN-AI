# Asterisk ARI Bridge — Setup Notes (Phase 1)

**Status: untested groundwork.** `media/asterisk_bridge.py` was written against the
documented Asterisk ARI REST API (18+) without a live Asterisk instance to verify
against. Treat everything below as a starting point, not a confirmed procedure —
expect to debug RTP framing, ARI event shapes, and playback timing against your
actual Asterisk version. See the module's docstring for the specific assumptions
that need checking.

This bridges inbound PSTN calls into the existing agent core over `/ws/chat`
(`app/main.py`), reusing the STT/TTS primitives already in `media/voice_bridge.py`.
It must run **on the same host as Asterisk** — it writes generated reply audio
into Asterisk's local sounds directory and tells Asterisk to stream caller audio
back to a `127.0.0.1` UDP port by default.

## 1. Install Asterisk

Standard Asterisk 18+ install (`apt install asterisk` on Debian/Ubuntu, or build
from source — see Asterisk's own install docs). No special modules beyond a
default install should be required (`res_ari`, `res_ari_channels`,
`res_ari_bridges`, `chan_pjsip`, and `format_wav` all ship by default).

## 2. Enable ARI

`/etc/asterisk/http.conf`:

```ini
[general]
enabled = yes
bindaddr = 127.0.0.1     ; ARI only needs to be reachable locally
bindport = 8088
```

`/etc/asterisk/ari.conf`:

```ini
[general]
enabled = yes

[hanuman]                 ; matches ARI_USERNAME in .env
type = user
password = change-me      ; matches ARI_PASSWORD in .env
password_format = plain
```

## 3. Dialplan

Route the DID(s) you want the agent answering into the `hanuman` Stasis app,
passing the dialed extension through as an arg (the bridge uses it to look up
the tenant via `tenants.tenant_for_number()`):

```ini
; /etc/asterisk/extensions.conf
[from-trunk]
exten => _X.,1,NoOp(Incoming call for ${EXTEN})
 same => n,Stasis(hanuman,${EXTEN})
 same => n,Hangup()
```

Adjust `_X.` and the context name (`from-trunk`) to match your actual trunk
config. Map the DID to a tenant first via the existing admin API:
`POST /admin/numbers {"e164": "+9771...", "tenant_id": "..."}`.

## 4. Configure the bridge

Copy the new block from `.env.example` into your `.env` and fill in the ARI
credentials from step 2:

```
ARI_BASE_URL=http://127.0.0.1:8088/ari
ARI_USERNAME=hanuman
ARI_PASSWORD=change-me
ARI_APP_NAME=hanuman
EXTERNAL_MEDIA_HOST=127.0.0.1
ASTERISK_SOUNDS_DIR=/var/lib/asterisk/sounds/custom
```

`ASTERISK_SOUNDS_DIR` must exist and be writable by whichever user runs the
bridge (and readable by Asterisk) — `mkdir -p /var/lib/asterisk/sounds/custom
&& chown <bridge-user>:asterisk /var/lib/asterisk/sounds/custom`.

## 5. Run it

The agent core (`uvicorn app.main:app`) must already be running — the bridge
connects to it exactly like `test_call.py`/`voice_bridge.py mic` do, over
`/ws/chat` on `127.0.0.1:8000`.

```bash
python media/asterisk_bridge.py
```

For production, `deploy/asterisk-bridge.service` mirrors the existing
`deploy/callagent.service` systemd unit.

## 6. What to actually verify once you have a phone line

- Does `StasisStart` fire for the caller channel with the args you expect
  (`${EXTEN}` showing up as `event["args"][0]`)?
- Does the caller actually hear the greeting (confirms `sound:` playback +
  `format_wav` are working)?
- Does the bridge's RTP depacketizing produce clean audio for Whisper (dump
  a captured utterance WAV and listen to it before trusting transcription)?
- Does silence-timeout VAD (700ms default, tune `SILENCE_TIMEOUT_MS` in
  `media/asterisk_bridge.py`) feel right for Nepali/English conversational
  pacing, or does it cut people off?
- Does the call actually hang up cleanly when the agent sets `end_call`?

Log everything (`asterisk_bridge` uses the standard `logging` module) during
your first real test calls — this is the fastest way to find where the
assumptions above break.
