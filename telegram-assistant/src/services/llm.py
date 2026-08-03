"""Google Gemini klienti — /schedule'ning bitta xabarli tahlili shundan foydalanadi."""

from __future__ import annotations

from google import genai

from ..config import config
from .store import store


class LLMError(Exception):
    """LLM ishlamay qolganda ko'tariladi — odamga hech qachon ko'rsatilmaydi."""


_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        if not config.gemini_api_key:
            raise LLMError("GEMINI_API_KEY .env faylda ko'rsatilmagan")
        _client = genai.Client(api_key=config.gemini_api_key)
    return _client


async def current_model() -> str:
    return (await store.get("model", "")) or config.gemini_model
