"""Central configuration loaded from .env"""
import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
# Haiku keeps per-call cost ~5x lower than Sonnet — the margin of the business.
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "")

COMPANY_NAME = os.getenv("COMPANY_NAME", "Your Company")
AGENT_NAME = os.getenv("AGENT_NAME", "Asha")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "auto")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
TTS_VOICE = os.getenv("TTS_VOICE", "en_US-amy-medium")

LEADS_DB_PATH = os.getenv("LEADS_DB_PATH", "./leads.db")
