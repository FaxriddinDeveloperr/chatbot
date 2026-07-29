"""Kirish nuqtasi: application yig'ish, handlerlarni ro'yxatdan o'tkazish, polling.

Ishga tushirish (loyiha ildizidan):
    python -m src.main
"""

from __future__ import annotations

import logging
import sys

from telegram import BotCommand, Update
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
from .handlers import approval, business, commands, inputs, knowledge, people, settings
from .utils.logger import report_error, setup_logging

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand("start", "Bosh menyu"),
    BotCommand("off", "Men offlaynman — bot javob bersin"),
    BotCommand("on", "Men onlaynman — bot jim tursin"),
    BotCommand("status", "Hozirgi holat"),
    BotCommand("knowledge", "Bilim bazasi"),
    BotCommand("people", "Odamlar (whitelist/blacklist)"),
    BotCommand("settings", "Sozlamalar"),
    BotCommand("stats", "Statistika"),
    BotCommand("history", "Oxirgi javoblar"),
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
    logger.info("Bot tayyor. Owner ID: %s", config.owner_id or "SOZLANMAGAN!")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Global xatolik ushlagichi — ownerga xabar, odamga hech narsa."""
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
        logger.warning("GEMINI_API_KEY yo'q — LLM javoblari ishlamaydi!")

    app = ApplicationBuilder().token(config.bot_token).post_init(on_startup).build()

    # Business: ulanish va xabarlar
    app.add_handler(BusinessConnectionHandler(business.handle_business_connection))
    app.add_handler(
        MessageHandler(filters.UpdateType.BUSINESS_MESSAGE, business.handle_business_message)
    )

    # Owner komandalar (faqat shaxsiy chat)
    private = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", commands.cmd_start, filters=private))
    app.add_handler(CommandHandler("on", commands.cmd_on, filters=private))
    app.add_handler(CommandHandler("off", commands.cmd_off, filters=private))
    app.add_handler(CommandHandler("status", commands.cmd_status, filters=private))
    app.add_handler(CommandHandler("stats", commands.cmd_stats, filters=private))
    app.add_handler(CommandHandler("history", commands.cmd_history, filters=private))
    app.add_handler(CommandHandler("logs", commands.cmd_logs, filters=private))
    app.add_handler(CommandHandler("knowledge", knowledge.cmd_knowledge, filters=private))
    app.add_handler(CommandHandler("people", people.cmd_people, filters=private))
    app.add_handler(CommandHandler("settings", settings.cmd_settings, filters=private))

    # Inline tugmalar
    app.add_handler(CallbackQueryHandler(approval.handle_approval_callback, pattern=r"^ap:"))
    app.add_handler(CallbackQueryHandler(knowledge.handle_kb_callback, pattern=r"^kb:"))
    app.add_handler(CallbackQueryHandler(people.handle_people_callback, pattern=r"^pp:"))
    app.add_handler(CallbackQueryHandler(settings.handle_settings_callback, pattern=r"^st:"))
    app.add_handler(
        CallbackQueryHandler(commands.handle_menu_callback, pattern=r"^(menu:|mode:|sts:)")
    )

    # Ownerdan matn kutish (tahrirlash, yangi bo'lim, model nomi...)
    app.add_handler(
        MessageHandler(private & filters.TEXT & ~filters.COMMAND, inputs.handle_owner_text)
    )

    app.add_error_handler(on_error)

    logger.info("Polling boshlanmoqda...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
