"""تنظیمات مرکزی برنامه"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

_default_db = Path(os.getenv("DB_PATH", str(BASE_DIR / "bot.db")))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_default_db}")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

_raw_admins = os.getenv("ADMIN_TELEGRAM_IDS", "")
INITIAL_ADMIN_IDS = [int(x.strip()) for x in _raw_admins.split(",") if x.strip().isdigit()]

MAX_MESSAGE_LENGTH = 4000
MAX_BUTTON_TEXT = 60
ITEMS_PER_PAGE = 8

ATTACHMENTS_DIR = Path(os.getenv("ATTACHMENTS_DIR", "/home/workdir/attachments"))
if not ATTACHMENTS_DIR.exists():
    ATTACHMENTS_DIR = BASE_DIR / "data"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# --- AI / RAG ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "meta-llama/llama-3.2-3b-instruct:free")
AI_ENABLED_DEFAULT = os.getenv("AI_ENABLED", "1") in ("1", "true", "True", "yes")
AI_SCORE_THRESHOLD = float(os.getenv("AI_SCORE_THRESHOLD", "12"))
AI_TOP_K = int(os.getenv("AI_TOP_K", "4"))
AI_MAX_TOKENS = int(os.getenv("AI_MAX_TOKENS", "1024"))
AI_RATE_LIMIT_PER_MINUTE = int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "8"))

# --- معرفی سازنده (فقط از .env؛ بدون پنل ادمین) ---
CREATOR_ENABLED = os.getenv("CREATOR_ENABLED", "1") in ("1", "true", "True", "yes")
CREATOR_NAME = os.getenv("CREATOR_NAME", "").strip()
CREATOR_TELEGRAM_ID = os.getenv("CREATOR_TELEGRAM_ID", "").strip()  # فقط عدد، مثلا 123456789
CREATOR_USERNAME = os.getenv("CREATOR_USERNAME", "").strip().lstrip("@")  # بدون @
CREATOR_TITLE = os.getenv("CREATOR_TITLE", "توسعه‌دهنده ربات").strip()
CREATOR_BIO = os.getenv("CREATOR_BIO", "").strip()
CREATOR_BUTTON_TEXT = os.getenv("CREATOR_BUTTON_TEXT", "👨‍💻 درباره سازنده").strip()