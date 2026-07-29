"""Konfiguratsiya: barcha kalitlar .env fayldan o'qiladi."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Config:
    """Muhit o'zgaruvchilaridan yig'ilgan sozlamalar."""

    bot_token: str = os.getenv("BOT_TOKEN", "")
    owner_id: int = int(os.getenv("OWNER_ID", "0") or 0)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    tts_provider: str = os.getenv("TTS_PROVIDER", "edge")
    stt_provider: str = os.getenv("STT_PROVIDER", "gemini")
    db_path: Path = BASE_DIR / os.getenv("DB_PATH", "data/bot.db")


config = Config()
