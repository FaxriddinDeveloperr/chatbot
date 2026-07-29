"""Google Gemini bilan ishlash: javob generatsiyasi (til aniqlash bilan birga)."""

from __future__ import annotations

import json
import logging

from google import genai
from google.genai import types

from ..config import config
from .store import store

logger = logging.getLogger(__name__)


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


def _history_to_contents(history: list[tuple[str, str]]) -> list[types.Content]:
    """(role, text) juftliklarini Gemini formatiga o'giradi."""
    contents: list[types.Content] = []
    for role, text in history:
        gemini_role = "user" if role == "user" else "model"
        contents.append(
            types.Content(role=gemini_role, parts=[types.Part.from_text(text=text)])
        )
    return contents


async def generate_reply(
    system_prompt: str,
    history: list[tuple[str, str]],
    rewrite: bool = False,
) -> tuple[str, str]:
    """Suhbat tarixiga javob yozadi. (til, javob_matni) qaytaradi.

    Tarixning oxirgi elementi — foydalanuvchining yangi xabari bo'lishi kerak.
    """
    contents = _history_to_contents(history)
    if rewrite:
        contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="[TIZIM] Oldingi javobing rad etildi. Xuddi shu xabarga "
                        "BOSHQACHA uslubdagi muqobil javob yoz."
                    )
                ],
            )
        )

    model = await current_model()
    try:
        response = await get_client().aio.models.generate_content(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.9 if rewrite else 0.7,
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "language": {"type": "STRING"},
                        "reply": {"type": "STRING"},
                    },
                    "required": ["language", "reply"],
                },
            ),
        )
    except Exception as exc:  
        raise LLMError(f"Gemini API xatosi: {exc}") from exc

    raw = (response.text or "").strip()
    try:
        data = json.loads(raw)
        lang = str(data.get("language", "uz")).lower()[:2]
        reply = str(data.get("reply", "")).strip()
    except (json.JSONDecodeError, AttributeError):
        logger.warning("LLM JSON qaytarmadi, xom matn ishlatiladi")
        lang, reply = "uz", raw

    if not reply:
        raise LLMError("LLM bo'sh javob qaytardi")
    if lang not in ("uz", "ru", "en"):
        default = await store.get("default_lang", "auto")
        lang = default if default in ("uz", "ru", "en") else "uz"
    return lang, reply
