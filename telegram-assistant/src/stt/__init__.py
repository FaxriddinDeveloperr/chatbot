"""STT provayderini konfiguratsiyaga qarab tanlash."""

from __future__ import annotations

from .base import STTProvider
from .gemini import GeminiSTT

_provider: STTProvider | None = None


def get_stt() -> STTProvider:
    global _provider
    if _provider is None:
        _provider = GeminiSTT()
    return _provider
