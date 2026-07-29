"""edge-tts provayderi: rus va ingliz tillari uchun ovoz.

O'zbek tili edge-tts'da yaxshi qo'llab-quvvatlanmaydi — supports() False
qaytaradi, bot matn yuboradi. Telegram "voice" sifatida ko'rsatishi uchun
mp3 ni ffmpeg bilan OGG/Opus'ga o'giramiz; ffmpeg bo'lmasa None qaytadi.
"""

from __future__ import annotations

import asyncio
import logging
import tempfile
import uuid
from pathlib import Path

import edge_tts

from .base import TTSProvider

logger = logging.getLogger(__name__)

VOICES: dict[str, str] = {
    "ru": "ru-RU-DmitryNeural",
    "en": "en-US-ChristopherNeural",
}


class EdgeTTS(TTSProvider):
    """Microsoft Edge onlayn TTS xizmati (bepul)."""

    def supports(self, lang: str) -> bool:
        return lang in VOICES

    async def synthesize(self, text: str, lang: str) -> Path | None:
        voice = VOICES.get(lang)
        if voice is None:
            return None

        tmp_dir = Path(tempfile.gettempdir())
        stem = f"tts_{uuid.uuid4().hex}"
        mp3_path = tmp_dir / f"{stem}.mp3"
        ogg_path = tmp_dir / f"{stem}.ogg"

        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(mp3_path))
        except Exception as exc:  # noqa: BLE001
            logger.warning("edge-tts ishlamadi: %s", exc)
            return None

        # Telegram voice uchun OGG/Opus kerak
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", str(mp3_path),
            "-c:a", "libopus", "-b:a", "32k", "-ar", "48000", str(ogg_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await proc.communicate()
        except FileNotFoundError:
            logger.warning("ffmpeg topilmadi — ovoz yuborilmaydi, matn yuboriladi")
            mp3_path.unlink(missing_ok=True)
            return None

        mp3_path.unlink(missing_ok=True)
        if proc.returncode != 0 or not ogg_path.exists():
            logger.warning("ffmpeg konvertatsiya xatosi")
            ogg_path.unlink(missing_ok=True)
            return None
        return ogg_path
