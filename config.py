import os
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN is not set in environment or .env file.")
    sys.exit(1)

ADMIN_ID_RAW = os.getenv("ADMIN_ID")
if not ADMIN_ID_RAW:
    print("ERROR: ADMIN_ID is not set in environment or .env file.")
    sys.exit(1)

try:
    ADMIN_ID = int(ADMIN_ID_RAW.strip())
except ValueError:
    print(f"ERROR: ADMIN_ID must be a valid integer, got: {ADMIN_ID_RAW}")
    sys.exit(1)

PROXY_URL = os.getenv("PROXY_URL") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or None

DB_PATH = BASE_DIR / "bot.db"
