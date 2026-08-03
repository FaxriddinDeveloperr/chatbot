"""Kirish nuqtasi: application yig'ish, handlerlarni ro'yxatdan o'tkazish, polling.

Ishga tushirish (loyiha ildizidan):
    python -m src.main
"""

from __future__ import annotations

import logging
import sys

from telegram import BotCommand, Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    ApplicationBuilder,
    BusinessConnectionHandler,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import config
from .database.seed import seed
from .database.session import init_db
from .handlers import business, commands, inputs, schedule, settings
from .services.scheduler import reschedule_all_pending
from .utils.logger import report_error, setup_logging

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand("start", "Bosh menyu"),
    BotCommand("schedule", "Xabarni vaqti-vaqtida yuborishni rejalashtirish"),
    BotCommand("scheduled", "Rejalashtirilgan xabarlar ro'yxati"),
    BotCommand("history", "Yuborilgan xabarlar tarixi"),
    BotCommand("settings", "Sozlamalar"),
    BotCommand("logs", "Oxirgi xatoliklar"),
]


async def on_startup(app: Application) -> None:
    """Baza yaratiladi, seed to'ldiriladi, komandalar ro'yxati o'rnatiladi."""
    await init_db()
    await seed()
    try:
        await app.bot.set_my_commands(BOT_COMMANDS)
    except Exception:  # noqa: BLE001
        logger.warning("Bot komandalarini o'rnatib bo'lmadi")
    await reschedule_all_pending(app)
    logger.info("Bot tayyor. Owner ID: %s", config.owner_id or "SOZLANMAGAN!")


# Bot uzoq vaqt o'chiq turgandan keyin to'plangan eskirgan yangilanishlarni
# qayta ishlashda chiqadigan, hech qanday zarar keltirmaydigan xatoliklar.
_BENIGN_BAD_REQUESTS = ("Message is not modified", "Query is too old")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global xatolik ushlagichi — ownerga xabar, odamga hech narsa."""
    if isinstance(context.error, BadRequest) and any(
        s in str(context.error) for s in _BENIGN_BAD_REQUESTS
    ):
        return
    await report_error(context, f"Kutilmagan xatolik: {context.error!r}")


def main() -> None:
    setup_logging()

    if not config.bot_token:
        logger.error("BOT_TOKEN .env faylda ko'rsatilmagan!")
        sys.exit(1)
    if not config.owner_id:
        logger.warning(
            "OWNER_ID sozlanmagan! Botga /start yozing — u sizning ID'ingizni aytadi."
        )
    if not config.gemini_api_key:
        logger.warning(
            "GEMINI_API_KEY yo'q — /schedule'ning bitta xabarli tahlili ishlamaydi "
            "(bosqichma-bosqich rejim baribir ishlayveradi)!"
        )

    app = ApplicationBuilder().token(config.bot_token).post_init(on_startup).build()

    # Business: ulanish (business_connection_id uchun) va kontaktlarni yozib olish
    app.add_handler(BusinessConnectionHandler(business.handle_business_connection))
    app.add_handler(
        MessageHandler(filters.UpdateType.BUSINESS_MESSAGE, business.handle_business_message)
    )

    # Owner komandalar (faqat shaxsiy chat)
    private = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", commands.cmd_start, filters=private))
    app.add_handler(CommandHandler("history", commands.cmd_history, filters=private))
    app.add_handler(CommandHandler("logs", commands.cmd_logs, filters=private))
    app.add_handler(CommandHandler("settings", settings.cmd_settings, filters=private))
    app.add_handler(CommandHandler("schedule", schedule.cmd_schedule, filters=private))
    app.add_handler(CommandHandler("scheduled", schedule.cmd_scheduled, filters=private))

    # Inline tugmalar
    app.add_handler(CallbackQueryHandler(settings.handle_settings_callback, pattern=r"^st:"))
    app.add_handler(CallbackQueryHandler(schedule.handle_schedule_callback, pattern=r"^sch:"))
    app.add_handler(CallbackQueryHandler(commands.handle_menu_callback, pattern=r"^menu:"))

    # Ownerdan matn kutish (rejalashtirish bosqichlari, model nomi...)
    app.add_handler(
        MessageHandler(private & filters.TEXT & ~filters.COMMAND, inputs.handle_owner_text)
    )

    app.add_error_handler(on_error)

    logger.info("Polling boshlanmoqda...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
