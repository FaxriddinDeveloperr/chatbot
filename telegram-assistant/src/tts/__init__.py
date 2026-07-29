"""TTS provayderini konfiguratsiyaga qarab tanlash."""

from __future__ import annotations

from ..config import config
from .base import TTSProvider
from .edge import EdgeTTS

_provider: TTSProvider | None = None


def get_tts() -> TTSProvider:
    """`.env` dagi TTS_PROVIDER ga mos provayderni qaytaradi."""
    global _provider
    if _provider is None:
        # Yangi provayder qo'shilganda shu yerga shart qo'shiladi:
        # if config.tts_provider == "elevenlabs": _provider = ElevenLabsTTS()
        _provider = EdgeTTS()
    return _provider
