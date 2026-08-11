"""
Voice bridge — reference pipeline: audio in → Whisper STT → agent (/ws/chat)
→ Piper TTS → audio out.

Two modes:

  1. Local mic test (needs a machine with mic/speakers, e.g. a dev laptop):
       python media/voice_bridge.py mic --tenant <tenant_id>

  2. Asterisk/FreeSWITCH integration (production, on the VPS):
       Use `transcribe_wav()` and `synthesize()` from your dialplan handler
       (e.g. Asterisk ARI/AGI or FreeSWITCH ESL script). Feed each caller
       utterance WAV in, play the returned WAV back on the channel.

Install:  pip install faster-whisper piper-tts websockets sounddevice soundfile
Piper voices: download .onnx voice files from the piper-voices repository
into ./voices/ (English: en_US-amy-medium; Nepali: check community voices,
or use Google Cloud TTS ne-NP as a paid alternative).
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

WHISPER_MODEL_NAME = "small"
PIPER_VOICE = str(Path(__file__).parent / "voices" / "en_US-amy-medium.onnx")
SERVER_WS = "ws://127.0.0.1:8000/ws/chat"

_whisper = None


def _get_whisper():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel
        _whisper = WhisperModel(WHISPER_MODEL_NAME, device="cpu", compute_type="int8")
    return _whisper


def transcribe_wav(wav_path: str, language: str | None = None) -> str:
    """WAV file → text. language: 'ne', 'en', or None for auto-detect."""
    segments, _info = _get_whisper().transcribe(
        wav_path, language=language, vad_filter=True
    )
    return " ".join(s.text.strip() for s in segments).strip()


def synthesize(text: str, out_wav: str, voice: str = PIPER_VOICE) -> str:
    """Text → WAV file via Piper. Returns out_wav path."""
    subprocess.run(
        ["piper", "--model", voice, "--output_file", out_wav],
        input=text.encode("utf-8"),
        check=True,
        capture_output=True,
    )
    return out_wav


# --------------------------------------------------------------- mic mode

async def mic_session(tenant_id: str | None):
    """Talk to the agent with your mic — full voice loop for local testing."""
    import sounddevice as sd
    import soundfile as sf
    import websockets

    async with websockets.connect(SERVER_WS) as ws:
        if tenant_id:
            await ws.send(json.dumps({"tenant_id": tenant_id}))
        greeting = await ws.recv()
        print(f"AGENT: {greeting}")
        _speak_local(greeting)

        while True:
            print("… speak now (5s) …")
            audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1)
            sd.wait()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                sf.write(f.name, audio, 16000)
                text = transcribe_wav(f.name)
            if not text:
                print("(heard nothing)")
                continue
            print(f"YOU: {text}")
            await ws.send(text)
            reply = await ws.recv()
            print(f"AGENT: {reply}")
            _speak_local(reply)


def _speak_local(text: str):
    import sounddevice as sd
    import soundfile as sf
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        try:
            synthesize(text, f.name)
            data, sr = sf.read(f.name)
            sd.play(data, sr)
            sd.wait()
        except Exception as e:
            print(f"[TTS unavailable: {e}]")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "mic":
        tid = sys.argv[3] if len(sys.argv) >= 4 and sys.argv[2] == "--tenant" else None
        asyncio.run(mic_session(tid))
    else:
        print(__doc__)
