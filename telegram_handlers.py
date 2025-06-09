import logging
import os
import time # For sleep in message splitting
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

from character_generator import generate_dnd_character_profile_for_bot

logger = logging.getLogger(__name__)

# --- Состояния ConversationHandler ---
(CHOOSE_RACE, CHOOSE_CLASS, CHOOSE_BACKGROUND, CHOOSE_ALIGNMENT,
 GET_LOCATION, GET_STATS_PREF, GET_DETAILS) = range(7)

# --- Опции для клавиатур ---
srd_races_options = ["Человек", "Эльф (Высший)", "Дварф (Холмовой)", "Полурослик (Легконогий)",
                     "Драконорожденный", "Гном (Лесной)", "Полуэльф", "Полуорк", "Тифлинг", "Авто (SRD раса)"]
srd_classes_options = ["Варвар", "Бард", "Жрец", "Друид", "Воин", "Монах",
                       "Паладин", "Следопыт", "Плут", "Чародей", "Колдун (Исчадие)", "Волшебник", "Авто (SRD класс)"]
srd_backgrounds_options = ["Прислужник", "Шарлатан", "Преступник", "Артист", "Народный Герой",
                           "Ремесленник Гильдии", "Отшельник", "Благородный", "Чужеземец",
                           "Мудрец", "Моряк", "Солдат", "Беспризорник", "Авто (SRD предыстория)"]
srd_alignments_options = [
    "Законно-Добрый", "Нейтрально-Добрый", "Хаотично-Добрый",
    "Законно-Нейтральный", "Истинно Нейтральный", "Хаотично-Нейтральный",
    "Законно-Злой", "Нейтрально-Злой", "Хаотично-Злой", "Авто (подходящее)"
]

def create_reply_keyboard(options_list, items_per_row=2):
    return [options_list[i:i + items_per_row] for i in range(0, len(options_list), items_per_row)]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    await update.message.reply_html(
        rf"Привет, {user.mention_html()}! Я D&D Генератор Персонажей v0.4 (с PDF!). "
        "Давай создадим персонажа. Используй /create для начала или /cancel для отмены.",
    )
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.info(f"Пользователь {user.first_name} отменил диалог.")
    await update.message.reply_text("Создание персонажа отменено. Начать заново: /create.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END

async def create_character_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    reply_keyboard = create_reply_keyboard(srd_races_options)
    await update.message.reply_text(
        "Начинаем создание персонажа! 🧙‍♂️\nВыбери расу или 'Авто'.",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder="Раса или 'Авто'")
    )
    return CHOOSE_RACE

async def _handle_choice_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   current_data_key: str,
                                   next_prompt_text: str,
                                   next_options_list: list | None,
                                   next_state: int,
                                   items_per_row_for_next: int = 2) -> int:
    user_choice = update.message.text.strip()
    chosen_value_display = "Авто"

    is_auto = any(auto_keyword in user_choice.lower() for auto_keyword in ["авто", "случайная", "подходящее", "пропустить"])

    if is_auto or not user_choice: # Also treat empty message as auto/skip
        context.user_data[current_data_key] = None
    else:
        context.user_data[current_data_key] = user_choice
        chosen_value_display = user_choice

    # Clarify the key being set for logging/debugging
    key_display_name = current_data_key.replace('_', ' ').capitalize()
    if current_data_key == "background": key_display_name = "Предыстория (Background)"
    elif current_data_key == "stats_preference": key_display_name = "Пожелания по статам"


    await update.message.reply_text(f"{key_display_name}: {chosen_value_display}.")

    if next_options_list:
        reply_keyboard = create_reply_keyboard(next_options_list, items_per_row_for_next)
        placeholder_text = f"{next_options_list[0].split(' ')[0]} или 'Авто'" if next_options_list else "Ваш выбор"
        await update.message.reply_text(
            next_prompt_text,
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True, input_field_placeholder=placeholder_text)
        )
    else: # Text input
         await update.message.reply_text(next_prompt_text, reply_markup=ReplyKeyboardRemove())
    return next_state

async def choose_race(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_choice_and_proceed(update, context, 'race', "Теперь выбери класс или 'Авто'.", srd_classes_options, CHOOSE_CLASS)

async def choose_class(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_choice_and_proceed(update, context, 'class', "Выбери предысторию (background) или 'Авто'.", srd_backgrounds_options, CHOOSE_BACKGROUND)

async def choose_background(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_choice_and_proceed(update, context, 'background', "Какое мировоззрение у твоего персонажа? Или 'Авто'.", srd_alignments_options, CHOOSE_ALIGNMENT, 3)

async def choose_alignment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_choice_and_proceed(update, context, 'alignment',
                                          "Откуда родом твой персонаж или где он сейчас находится?\n(например, 'тихая деревня Фандалин')\nЕсли не важно, напиши 'авто' или 'пропустить'.",
                                          None, GET_LOCATION)

async def get_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _handle_choice_and_proceed(update, context, 'location',
                                          "Есть ли пожелания по характеристикам (статам)?\n(например, 'главное - высокий Интеллект и Ловкость')\nЕсли нет, напиши 'авто' или 'пропустить'.",
                                          None, GET_STATS_PREF)

async def get_stats_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
     return await _handle_choice_and_proceed(update, context, 'stats_preference',
                                           "И наконец, какие-то особые детали, ключевые моменты предыстории или черты характера?\nЕсли нет, напиши 'авто' или 'пропустить'.",
                                           None, GET_DETAILS)

async def get_details_and_generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_details_input = update.message.text.strip()
    is_auto = any(auto_keyword in user_details_input.lower() for auto_keyword in ["авто", "пропустить"])

    if is_auto or not user_details_input:
        context.user_data['details'] = None
        details_display = 'На усмотрение модели'
    else:
        context.user_data['details'] = user_details_input
        details_display = user_details_input

    await update.message.reply_text(
        f"Доп. детали: {details_display}.\n\n"
        "Спасибо! Начинаю генерацию персонажа и PDF. Это может занять до минуты...",
        reply_markup=ReplyKeyboardRemove()
    )

    ud = context.user_data
    await update.message.chat.send_action(action="typing")

    # Use application.create_task for background execution if needed,
    # but direct await is fine for typical bot operations.
    generation_result = await generate_dnd_character_profile_for_bot(
            user_race=ud.get('race'), user_class=ud.get('class'),
            user_background=ud.get('background'), user_alignment=ud.get('alignment'),
            user_location=ud.get('location'), user_stats_preference=ud.get('stats_preference'),
            user_details=ud.get('details'), user_id=str(update.effective_user.id)
        )

    text_profile = generation_result.get("text_profile")
    pdf_filepath = generation_result.get("pdf_filepath")

    error_prefix = ("ЗАПРОС ЗАБЛОКИРОВАН", "КОНТЕНТ ЗАБЛОКИРОВАН", "ОШИБКА API", "Модель не вернула", "Модель вернула пустой")

    if text_profile and not any(text_profile.startswith(prefix) for prefix in error_prefix):
        if len(text_profile) > 4096: # Telegram message length limit
             await update.message.reply_text("Сгенерированный текстовый профиль слишком длинный. Вот его части:")
             for i in range(0, len(text_profile), 4090): # Split with a small margin
                 await update.message.chat.send_action(action="typing")
                 await update.message.reply_text(text_profile[i:i + 4090])
                 await context.application.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing") # Keep typing indicator
                 time.sleep(0.5) # Small delay between parts
        else:
            await update.message.reply_text(text_profile)

        if pdf_filepath and os.path.exists(pdf_filepath):
            try:
                await update.message.chat.send_action(action="upload_document")
                with open(pdf_filepath, 'rb') as pdf_file:
                    await update.message.reply_document(
                        document=pdf_file,
                        filename=os.path.basename(pdf_filepath),
                        caption="Вот PDF с твоим персонажем!"
                    )
                logger.info(f"PDF {pdf_filepath} успешно отправлен пользователю {update.effective_user.id}")
            except Exception as e_send_pdf:
                logger.error(f"Ошибка при отправке PDF {pdf_filepath} пользователю: {e_send_pdf}")
                await update.message.reply_text("Не удалось отправить PDF файл персонажа. Текстовая версия выше.")
        elif pdf_filepath: # File was expected but not found
             logger.error(f"PDF файл не найден по пути: {pdf_filepath}")
             await update.message.reply_text("Не удалось создать PDF файл персонажа (файл не найден). Пожалуйста, используйте текстовую версию выше.")
        else: # PDF creation failed or was skipped
            await update.message.reply_text("Не удалось создать PDF файл персонажа. Пожалуйста, используйте текстовую версию выше.")

    elif text_profile: # An error message from generation_result
        await update.message.reply_text(f"Произошла ошибка при генерации: {text_profile}\nПопробуйте еще раз: /create")
    else: # Should not happen if generate_dnd_character_profile_for_bot always returns a dict
        await update.message.reply_text("К сожалению, не удалось сгенерировать персонажа (нет ответа от LLM). Попробуйте еще раз: /create")

    await update.message.reply_text("Чтобы создать еще одного персонажа, используй /create.")
    context.user_data.clear()
    return ConversationHandler.END