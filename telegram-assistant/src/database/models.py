"""SQLAlchemy modellari: odamlar, xabarlar, bilim bazasi, sozlamalar, loglar."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Ruxsat darajalari
LEVEL_WHITELIST = "whitelist"
LEVEL_UNKNOWN = "unknown"
LEVEL_BLACKLIST = "blacklist"

# Javob loglari statuslari
STATUS_AUTO = "auto"          # whitelist — avtomatik yuborildi
STATUS_APPROVED = "approved"  # owner tasdiqladi
STATUS_EDITED = "edited"      # owner tahrirlab yubordi
STATUS_REJECTED = "rejected"  # owner bekor qildi
STATUS_EXPIRED = "expired"    # 1 soatda tasdiqlanmadi


def utcnow() -> datetime:
    """Naive UTC vaqt (SQLite bilan solishtirish oson bo'lishi uchun)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Barcha modellar uchun asos."""


class Person(Base):
    """Botga yozgan odam va uning ruxsat darajasi."""

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user id
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(160), default="")
    level: Mapped[str] = mapped_column(String(16), default=LEVEL_UNKNOWN, index=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ChatMessage(Base):
    """Suhbat tarixi — LLM konteksti uchun."""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant"
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class KnowledgeSection(Base):
    """Bilim bazasi bo'limi — bot shulardan system prompt yasaydi."""

    __tablename__ = "knowledge_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(120))
    content: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Setting(Base):
    """Kalit-qiymat ko'rinishidagi sozlamalar."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), default="")


class ResponseLog(Base):
    """Yuborilgan/rad etilgan javoblar tarixi."""

    __tablename__ = "response_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    person_name: Mapped[str] = mapped_column(String(160), default="")
    incoming: Mapped[str] = mapped_column(Text, default="")
    reply: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class ErrorLog(Base):
    """Oxirgi xatoliklar — /logs komandasi uchun."""

    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
