"""STT (ovoz -> matn) abstraksiya qatlami."""

from __future__ import annotations

from abc import ABC, abstractmethod


class STTProvider(ABC):
    """Ovozli xabarni matnga aylantiruvchi provayder interfeysi."""

    @abstractmethod
    async def transcribe(self, audio: bytes, mime_type: str) -> str:
        """Audio baytlarni matnga aylantiradi. Xato bo'lsa exception ko'taradi."""
