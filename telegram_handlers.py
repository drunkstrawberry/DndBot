# -*- coding: utf-8 -*-
# telegram_handlers.py
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

from character_generator import generate_dnd_character_profile_for_bot # Убедитесь, что этот импорт правильный

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
        rf"Привет, {user.mention_html()}! Я D&D Генератор Персонажей v0.5 (PDF в памяти!). " # Версия обновлена для примера
        "Давай создадим персонажа. Используй /create для начала или /cancel для отмены.",
    )
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    logger.info(f"Пользователь {user.first_name} ({user.id}) отменил диалог.")
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
    chosen_value_display = "Авто" # По умолчанию, если выбран авто-вариант или пропуск

    # Проверяем, является ли выбор авто-вариантом или пропуском
    is_auto = any(auto_keyword in user_choice.lower() for auto_keyword in ["авто", "случайная", "подходящее", "пропустить", "skip"])

    if is_auto or not user_choice: # Пустой ввод также считаем за "авто"
        context.user_data[current_data_key] = None
    else:
        context.user_data[current_data_key] = user_choice
        chosen_value_display = user_choice

    # Формируем имя ключа для отображения пользователю
    key_display_name_map = {
        'race': 'Раса',
        'class': 'Класс',
        'background': 'Предыстория (Background)',
        'alignment': 'Мировоззрение',
        'location': 'Локация/Происхождение',
        'stats_preference': 'Пожелания по характеристикам',
        'details': 'Дополнительные детали'
    }
    display_key = key_display_name_map.get(current_data_key, current_data_key.replace('_', ' ').capitalize())

    await update.message.reply_text(f"{display_key}: {chosen_value_display}.")

    if next_options_list:
        placeholder_text = f"{next_options_list[0].split(' ')[0]} или 'Авто'" if next_options_list else "Ваш выбор"
        reply_keyboard_markup = ReplyKeyboardMarkup(
            create_reply_keyboard(next_options_list, items_per_row_for_next),
            one_time_keyboard=True,
            resize_keyboard=True,
            input_field_placeholder=placeholder_text
        )
        await update.message.reply_text(next_prompt_text, reply_markup=reply_keyboard_markup)
    else: # Если следующий шаг - это текстовый ввод без кнопок
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
    is_auto = any(auto_keyword in user_details_input.lower() for auto_keyword in ["авто", "пропустить", "skip"])

    details_display = 'На усмотрение модели'
    if is_auto or not user_details_input:
        context.user_data['details'] = None
    else:
        context.user_data['details'] = user_details_input
        details_display = user_details_input

    await update.message.reply_text(
        f"Дополнительные детали: {details_display}.\n\n"
        "Спасибо! Начинаю генерацию персонажа и PDF. Это может занять до минуты...",
        reply_markup=ReplyKeyboardRemove()
    )

    ud = context.user_data
    await update.message.chat.send_action(action="typing")

    generation_result = await generate_dnd_character_profile_for_bot(
            user_race=ud.get('race'), user_class=ud.get('class'),
            user_background=ud.get('background'), user_alignment=ud.get('alignment'),
            user_location=ud.get('location'), user_stats_preference=ud.get('stats_preference'),
            user_details=ud.get('details'), user_id=str(update.effective_user.id)
        )

    text_profile = generation_result.get("text_profile")
    pdf_buffer = generation_result.get("pdf_buffer") # Получаем буфер PDF
    parsed_data = generation_result.get("parsed_data") # Получаем распарсенные данные для имени файла

    error_prefix_tuple = ("ЗАПРОС ЗАБЛОКИРОВАН", "КОНТЕНТ ЗАБЛОКИРОВАН", "ОШИБКА API", "Модель не вернула", "Модель вернула пустой")

    if text_profile and not any(text_profile.startswith(prefix) for prefix in error_prefix_tuple):
        # Отправка текстового профиля частями, если он слишком длинный
        if len(text_profile) > 4096: # Максимальная длина сообщения Telegram
             await update.message.reply_text("Сгенерированный текстовый профиль слишком длинный. Вот его части:")
             for i in range(0, len(text_profile), 4090): # Делим с небольшим запасом
                 await update.message.chat.send_action(action="typing")
                 await update.message.reply_text(text_profile[i:i + 4090])
                 # Используем context.application.bot.send_chat_action если бот инициализирован через Application v20+
                 if hasattr(context, 'application') and hasattr(context.application, 'bot'):
                     await context.application.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
                 time.sleep(0.5) # Небольшая задержка между частями
        else:
            await update.message.reply_text(text_profile)

        # Отправка PDF, если он был успешно сгенерирован (pdf_buffer не None)
        if pdf_buffer:
            try:
                await update.message.chat.send_action(action="upload_document")

                # Генерируем имя файла для пользователя
                char_name_for_file = "UnknownCharacter"
                if parsed_data and parsed_data.get('name'):
                    # Очищаем имя персонажа для использования в имени файла
                    char_name_for_file = "".join(c if c.isalnum() else "_" for c in parsed_data.get('name'))

                user_id_str = str(update.effective_user.id)
                # Формируем уникальное имя файла для пользователя
                pdf_filename_for_user = f"DND_Character_{char_name_for_file}_{user_id_str}.pdf"

                # pdf_buffer.seek(0) # Этот вызов теперь делается в pdf_generator.py перед возвратом буфера

                await update.message.reply_document(
                    document=pdf_buffer, # Отправляем буфер из памяти
                    filename=pdf_filename_for_user, # Имя файла, которое увидит пользователь
                    caption="Вот PDF с твоим персонажем!"
                )
                logger.info(f"PDF из памяти успешно отправлен пользователю {update.effective_user.id}")
            except Exception as e_send_pdf:
                logger.error(f"Ошибка при отправке PDF из памяти пользователю {update.effective_user.id}: {e_send_pdf}")
                await update.message.reply_text("К сожалению, не удалось отправить PDF файл персонажа. Пожалуйста, используйте текстовую версию выше.")
        else:
            # Это сообщение будет отправлено, если pdf_buffer равен None (например, ошибка при создании PDF)
            await update.message.reply_text("Не удалось создать PDF файл персонажа. Пожалуйста, используйте текстовую версию выше.")

    elif text_profile: # Если text_profile содержит сообщение об ошибке от LLM
        await update.message.reply_text(f"Произошла ошибка при генерации: {text_profile}\nПопробуйте еще раз: /create")
    else: # Если text_profile пуст (маловероятно, но на всякий случай)
        await update.message.reply_text("К сожалению, не удалось сгенерировать персонажа (не получен ответ от модели). Попробуйте еще раз: /create")

    await update.message.reply_text("Чтобы создать еще одного персонажа, используй /create.")
    context.user_data.clear() # Очищаем данные пользователя для следующей сессии
    return ConversationHandler.END
