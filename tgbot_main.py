import nest_asyncio
nest_asyncio.apply()

import logging
import os
import datetime

from telegram import Update
from telegram.ext import Application, ConversationHandler, MessageHandler, CommandHandler, filters

from config import (
    TELEGRAM_BOT_TOKEN,
    TEXT_OUTPUT_DIR,
    GOOGLE_API_KEY
)

from logger_setup import logger

from pdf_generator import register_font # Импортируем функцию регистрации шрифта
from gemini_utils import init_gemini

# --- Telegram Handlers ---
from telegram_handlers import (
    start,
    cancel,
    create_character_start,
    choose_race,
    choose_class,
    choose_background,
    choose_alignment,
    get_location,
    get_stats_preference,
    get_details_and_generate,
    CHOOSE_RACE, CHOOSE_CLASS, CHOOSE_BACKGROUND, CHOOSE_ALIGNMENT,
    GET_LOCATION, GET_STATS_PREF, GET_DETAILS,
)

def main() -> None:
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "api_ключ_google_ai_studio" or \
       not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "токен_твоего_телеграм_бота":
        logger.error("ОШИБКА: API ключ Google или токен Telegram-бота не установлен в config.py.")
        logger.error("Пожалуйста, отредактируйте config.py и введите свои ключи.")
        exit(1)

    if not init_gemini():
        logger.error("Не удалось инициализировать Gemini. Проверьте API ключ и настройки. Бот не может запуститься.")
        exit(1)

    # Создаем директорию только для текстовых логов LLM
    os.makedirs(TEXT_OUTPUT_DIR, exist_ok=True)
    logger.info(f"Директория для текстовых логов LLM создана/проверена: {TEXT_OUTPUT_DIR}")

    register_font() # Регистрируем шрифт для PDF при старте бота

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(30)
        .pool_timeout(60)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("create", create_character_start)],
        states={
            CHOOSE_RACE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_race)],
            CHOOSE_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_class)],
            CHOOSE_BACKGROUND: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_background)],
            CHOOSE_ALIGNMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_alignment)],
            GET_LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_location)],
            GET_STATS_PREF: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_stats_preference)],
            GET_DETAILS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_details_and_generate)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
        per_user=True,
        conversation_timeout=datetime.timedelta(minutes=20)
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("cancel", cancel))

    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
