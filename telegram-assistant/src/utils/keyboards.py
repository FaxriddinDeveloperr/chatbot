"""Barcha inline klaviaturalar bir joyda."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ..database.models import Person


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📅 Yangi reja", callback_data="sch:start"),
                InlineKeyboardButton("🗓 Rejalar ro'yxati", callback_data="sch:list"),
            ],
            [
                InlineKeyboardButton("📜 Tarix", callback_data="menu:history"),
                InlineKeyboardButton("🐞 Xatoliklar", callback_data="menu:logs"),
            ],
            [InlineKeyboardButton("⚙️ Sozlamalar", callback_data="st:menu")],
        ]
    )


def schedule_confirm(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Ha, yubor", callback_data=f"sch:confirm:{token}"),
                InlineKeyboardButton("❌ Bekor", callback_data=f"sch:cancel:{token}"),
            ]
        ]
    )


def schedule_pick(token: str, candidates: list[Person]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{p.full_name or p.username or p.id}"
                + (f" (@{p.username})" if p.username else ""),
                callback_data=f"sch:pick:{token}:{p.id}",
            )
        ]
        for p in candidates
    ]
    rows.append([InlineKeyboardButton("❌ Bekor", callback_data=f"sch:cancel:{token}")])
    return InlineKeyboardMarkup(rows)


def scheduled_list(items) -> InlineKeyboardMarkup:
    from ..services.scheduler import TASHKENT_OFFSET

    rows = [
        [
            InlineKeyboardButton(
                f"❌ {item.person_name} — {(item.send_at + TASHKENT_OFFSET).strftime('%d.%m %H:%M')}",
                callback_data=f"sch:del:{item.id}",
            )
        ]
        for item in items
    ]
    rows.append([InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def settings_menu(values: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"🧠 Model: {values['model']}", callback_data="st:model")],
            [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu:main")],
        ]
    )
