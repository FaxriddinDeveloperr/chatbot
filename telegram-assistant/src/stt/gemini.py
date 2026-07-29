"""Gemini orqali ovozli xabarni matnga aylantirish (audio input)."""

from __future__ import annotations

from google.genai import types

from ..services.llm import LLMError, current_model, get_client
from .base import STTProvider


class GeminiSTT(STTProvider):
    """Gemini'ning audio tushunish qobiliyatidan foydalanadi."""

    async def transcribe(self, audio: bytes, mime_type: str) -> str:
        try:
            response = await get_client().aio.models.generate_content(
                model=await current_model(),
                contents=[
                    types.Part.from_text(
                        text="Quyidagi ovozli xabarni aynan aytilgan tilda, so'zma-so'z "
                        "matnga aylantir. Faqat transkripsiya matnini qaytar, boshqa "
                        "hech narsa yozma."
                    ),
                    types.Part.from_bytes(data=audio, mime_type=mime_type),
                ],
            )
        except LLMError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise LLMError(f"STT xatosi: {exc}") from exc

        text = (response.text or "").strip()
        if not text:
            raise LLMError("STT bo'sh natija qaytardi")
        return text
