import nest_asyncio
nest_asyncio.apply() # Apply this early

import logging
import os
import datetime # For ConversationHandler timeout

from telegram import Update # For type hinting if needed, though mostly handled in telegram_handlers
from telegram.ext import Application, ConversationHandler

# --- Config and Setup ---
from config import (
    TELEGRAM_BOT_TOKEN,
    PDF_OUTPUT_DIR,
    TEXT_OUTPUT_DIR,
    GOOGLE_API_KEY # For initial check
)
# Logger setup must be one of the first imports to configure logging early
from logger_setup import logger # Imports the already configured logger instance

from pdf_generator import register_font
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
from telegram.ext import MessageHandler, CommandHandler, filters # Ensure these are imported if used directly


def main() -> None:
    # --- Initial Checks and Setup ---
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "api_ключ_google_ai_studio" or \
       not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "токен_твоего_телеграм_бота":
        logger.error("ОШИБКА: API ключ Google или токен Telegram-бота не установлен в config.py.")
        logger.error("Пожалуйста, отредактируйте config.py и введите свои ключи.")
        exit(1)

    if not init_gemini(): # Initialize Gemini and check for success
        logger.error("Не удалось инициализировать Gemini. Проверьте API ключ и настройки. Бот не может запуститься.")
        exit(1)

    os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEXT_OUTPUT_DIR, exist_ok=True)
    logger.info(f"Директории для вывода созданы/проверены: {PDF_OUTPUT_DIR}, {TEXT_OUTPUT_DIR}")

    register_font() # Register custom font for PDF if specified

    # --- Telegram Bot Application ---
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(30)
        .write_timeout(30)
        .connect_timeout(30)
        .pool_timeout(30) # For HTTPX connection pooling
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
        per_user=True, # Important for user-specific conversation data
        conversation_timeout=datetime.timedelta(minutes=15) # Use datetime.timedelta
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)
    # Adding cancel as a top-level command as well, in case it's missed in fallbacks
    # (though fallbacks should catch it if user is in a conversation)
    application.add_handler(CommandHandler("cancel", cancel))


    logger.info("Бот запускается...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()