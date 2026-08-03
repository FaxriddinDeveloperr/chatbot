"""SQLAlchemy modellari: kontaktlar, rejalashtirilgan xabarlar, sozlamalar, loglar."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

STATUS_AUTO = "auto"  # yuborilgan rejalashtirilgan xabar (/history uchun)

# Rejalashtirilgan xabar statuslari
SCHED_PENDING = "pending"
SCHED_SENT = "sent"
SCHED_CANCELLED = "cancelled"
SCHED_FAILED = "failed"


def utcnow() -> datetime:
    """Naive UTC vaqt (SQLite bilan solishtirish oson bo'lishi uchun)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Barcha modellar uchun asos."""


class Person(Base):
    """Business orqali sizga yozgan odam — /schedule shulardan qidiradi."""

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user id
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(160), default="")
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    """Kalit-qiymat ko'rinishidagi sozlamalar."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(255), default="")


class ResponseLog(Base):
    """Yuborilgan rejalashtirilgan xabarlar tarixi — /history uchun."""

    __tablename__ = "response_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    person_name: Mapped[str] = mapped_column(String(160), default="")
    incoming: Mapped[str] = mapped_column(Text, default="")
    reply: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(16), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class ScheduledMessage(Base):
    """Kelajakda ma'lum vaqtda yuborilishi kerak bo'lgan xabar."""

    __tablename__ = "scheduled_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    person_id: Mapped[int] = mapped_column(BigInteger, index=True)  # qabul qiluvchi (= chat_id)
    person_name: Mapped[str] = mapped_column(String(160), default="")
    text: Mapped[str] = mapped_column(Text)
    send_at: Mapped[datetime] = mapped_column(DateTime, index=True)  # naive UTC
    status: Mapped[str] = mapped_column(String(16), default=SCHED_PENDING, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ErrorLog(Base):
    """Oxirgi xatoliklar — /logs komandasi uchun."""

    __tablename__ = "error_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
