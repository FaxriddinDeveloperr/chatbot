"""TTS abstraksiya qatlami — provayder almashtirish uchun."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class TTSProvider(ABC):
    """Matnni ovozga aylantiruvchi provayder interfeysi.

    Yangi provayder qo'shish: shu klassdan meros oling (masalan
    tts/elevenlabs.py), keyin .env da TTS_PROVIDER=elevenlabs qiling.
    """

    @abstractmethod
    def supports(self, lang: str) -> bool:
        """Berilgan til ("uz"/"ru"/"en") uchun ovoz bormi."""

    @abstractmethod
    async def synthesize(self, text: str, lang: str) -> Path | None:
        """Matnni ovozga aylantirib, OGG/Opus fayl yo'lini qaytaradi.

        Muvaffaqiyatsiz bo'lsa None qaytaradi (chaqiruvchi matnga qaytadi).
        """
