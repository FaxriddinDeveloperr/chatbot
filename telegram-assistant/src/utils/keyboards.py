"""Barcha inline klaviaturalar bir joyda."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ..database.models import (
    LEVEL_BLACKLIST,
    LEVEL_UNKNOWN,
    LEVEL_WHITELIST,
    KnowledgeSection,
    Person,
)

LEVEL_EMOJI = {LEVEL_WHITELIST: "⭐", LEVEL_UNKNOWN: "❓", LEVEL_BLACKLIST: "🚫"}
LEVEL_NAME = {LEVEL_WHITELIST: "Whitelist", LEVEL_UNKNOWN: "Notanish", LEVEL_BLACKLIST: "Blacklist"}


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📚 Bilim bazasi", callback_data="kb:menu"),
                InlineKeyboardButton("👥 Odamlar", callback_data="pp:menu"),
            ],
            [
                InlineKeyboardButton("⚙️ Sozlamalar", callback_data="st:menu"),
                InlineKeyboardButton("📊 Statistika", callback_data="sts:today"),
            ],
            [
                InlineKeyboardButton("📜 Tarix", callback_data="menu:history"),
                InlineKeyboardButton("🐞 Xatoliklar", callback_data="menu:logs"),
            ],
            [
                InlineKeyboardButton("📅 Yangi reja", callback_data="sch:start"),
                InlineKeyboardButton("🗓 Rejalar ro'yxati", callback_data="sch:list"),
            ],
            [
                InlineKeyboardButton("🔴 Off (bot ishlasin)", callback_data="mode:active"),
                InlineKeyboardButton("🟢 On (bot jim)", callback_data="mode:auto"),
            ],
        ]
    )


def approval_kb(approval_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Yubor", callback_data=f"ap:send:{approval_id}"),
                InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"ap:edit:{approval_id}"),
            ],
            [
                InlineKeyboardButton("🔄 Qayta yoz", callback_data=f"ap:rew:{approval_id}"),
                InlineKeyboardButton("❌ Bekor", callback_data=f"ap:cancel:{approval_id}"),
            ],
            [InlineKeyboardButton("⭐ Whitelist'ga qo'sh", callback_data=f"ap:wl:{approval_id}")],
        ]
    )


def kb_menu(sections: list[KnowledgeSection]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{i}. {s.title} {'✅' if s.is_active else '🔴'}",
                callback_data=f"kb:view:{s.id}",
            )
        ]
        for i, s in enumerate(sections, start=1)
    ]
    rows.append(
        [
            InlineKeyboardButton("➕ Yangi bo'lim", callback_data="kb:new"),
            InlineKeyboardButton("🔄 Tartib", callback_data="kb:order"),
        ]
    )
    rows.append([InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu:main")])
    return InlineKeyboardMarkup(rows)


def kb_section(section: KnowledgeSection) -> InlineKeyboardMarkup:
    toggle_label = "🔴 O'chirish" if section.is_active else "✅ Yoqish"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"kb:edit:{section.id}"),
                InlineKeyboardButton(toggle_label, callback_data=f"kb:toggle:{section.id}"),
            ],
            [InlineKeyboardButton("🗑 Butunlay o'chir", callback_data=f"kb:del:{section.id}")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data="kb:menu")],
        ]
    )


def kb_delete_confirm(section_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🗑 Ha, o'chir", callback_data=f"kb:delc:{section_id}"),
                InlineKeyboardButton("⬅️ Yo'q", callback_data=f"kb:view:{section_id}"),
            ]
        ]
    )


def kb_order(sections: list[KnowledgeSection]) -> InlineKeyboardMarkup:
    rows = []
    for s in sections:
        rows.append(
            [
                InlineKeyboardButton(f"⬆️", callback_data=f"kb:up:{s.id}"),
                InlineKeyboardButton(f"⬇️", callback_data=f"kb:down:{s.id}"),
                InlineKeyboardButton(s.title[:30], callback_data=f"kb:view:{s.id}"),
            ]
        )
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="kb:menu")])
    return InlineKeyboardMarkup(rows)


def people_menu(counts: dict[str, int]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"⭐ Whitelist ({counts.get(LEVEL_WHITELIST, 0)})",
                    callback_data=f"pp:list:{LEVEL_WHITELIST}",
                )
            ],
            [
                InlineKeyboardButton(
                    f"🚫 Blacklist ({counts.get(LEVEL_BLACKLIST, 0)})",
                    callback_data=f"pp:list:{LEVEL_BLACKLIST}",
                )
            ],
            [
                InlineKeyboardButton(
                    f"❓ So'nggi notanish ({counts.get(LEVEL_UNKNOWN, 0)})",
                    callback_data=f"pp:list:{LEVEL_UNKNOWN}",
                )
            ],
            [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu:main")],
        ]
    )


def people_list(people: list[Person]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{LEVEL_EMOJI[p.level]} {p.full_name or p.username or p.id}",
                callback_data=f"pp:view:{p.id}",
            )
        ]
        for p in people
    ]
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="pp:menu")])
    return InlineKeyboardMarkup(rows)


def person_view(person: Person) -> InlineKeyboardMarkup:
    rows = []
    for level in (LEVEL_WHITELIST, LEVEL_UNKNOWN, LEVEL_BLACKLIST):
        if person.level == level:
            continue
        rows.append(
            [
                InlineKeyboardButton(
                    f"{LEVEL_EMOJI[level]} {LEVEL_NAME[level]}'ga o'tkaz",
                    callback_data=f"pp:set:{person.id}:{level}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="pp:menu")])
    return InlineKeyboardMarkup(rows)


def settings_menu(values: dict[str, str]) -> InlineKeyboardMarkup:
    voice = "yoqilgan 🔊" if values["voice_enabled"] == "1" else "o'chirilgan 🔇"
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    f"🕐 Auto-offline: {values['auto_offline_minutes']} daqiqa",
                    callback_data="st:auto_off",
                )
            ],
            [InlineKeyboardButton(f"🔊 Ovozli javob: {voice}", callback_data="st:voice")],
            [
                InlineKeyboardButton(
                    f"📏 Ovoz uchun min uzunlik: {values['voice_min_chars']}",
                    callback_data="st:minchars",
                )
            ],
            [
                InlineKeyboardButton(
                    f"🌐 Standart til: {values['default_lang']}", callback_data="st:lang"
                )
            ],
            [InlineKeyboardButton(f"🧠 Model: {values['model']}", callback_data="st:model")],
            [
                InlineKeyboardButton(
                    f"💬 Kontekst: {values['context_depth']} xabar",
                    callback_data="st:context",
                )
            ],
            [
                InlineKeyboardButton(
                    f"⏱ Kechikish: {values['delay_min']}-{values['delay_max']} soniya",
                    callback_data="st:delay",
                )
            ],
            [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu:main")],
        ]
    )


def choices(prefix: str, options: list[str], back: str = "st:menu") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(opt, callback_data=f"{prefix}:{opt}") for opt in options[i : i + 3]]
        for i in range(0, len(options), 3)
    ]
    rows.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=back)])
    return InlineKeyboardMarkup(rows)


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


def stats_periods(active: str) -> InlineKeyboardMarkup:
    def label(key: str, title: str) -> str:
        return f"• {title} •" if key == active else title

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(label("today", "Bugun"), callback_data="sts:today"),
                InlineKeyboardButton(label("week", "Hafta"), callback_data="sts:week"),
                InlineKeyboardButton(label("month", "Oy"), callback_data="sts:month"),
            ],
            [InlineKeyboardButton("⬅️ Bosh menyu", callback_data="menu:main")],
        ]
    )
