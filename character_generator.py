
# character_generator.py
import logging
import os
from config import (
    TEXT_OUTPUT_DIR,
    GEMINI_MODEL_NAME,
    SYSTEM_MESSAGE_FULL_CHAR_GEMINI_PREFIX
)
from gemini_utils import (
    generate_content_with_gemini,
    parse_character_profile,
    get_timestamp_filename
)
from pdf_generator import create_character_sheet_pdf 

logger = logging.getLogger(__name__)

async def generate_dnd_character_profile_for_bot(
    user_race=None, user_class=None, user_background=None, user_alignment=None,
    user_location=None, user_stats_preference=None, user_details="", user_id="unknown_user"
):
    user_request_parts = ["Сгенерируй полного персонажа D&D 5e (SRD)."]
    def add_param(label, value, default_text_llm):
        if value: user_request_parts.append(f"{label}: {value} (из SRD 5.1, если применимо).")
        else: user_request_parts.append(f"{label}: {default_text_llm}")

    add_param("Раса", user_race, "Выбери подходящую расу из SRD 5.1.")
    add_param("Класс", user_class, "Выбери подходящий класс из SRD 5.1.")
    add_param("Предыстория (Background)", user_background, "Выбери подходящую предысторию (background) из SRD 5.1.")
    add_param("Мировоззрение", user_alignment, "Выбери подходящее мировоззрение.")

    if user_location: user_request_parts.append(f"Происхождение/Локация: {user_location}.")
    else: user_request_parts.append("Происхождение/Локация: Придумай подходящее.")

    if user_stats_preference: user_request_parts.append(f"Пожелания по характеристикам: {user_stats_preference}.")
    else: user_request_parts.append("Пожелания по характеристикам: Сбалансированное распределение.")

    if user_details: user_request_parts.append(f"Дополнительные детали/пожелания к текстовой предыстории и характеру: {user_details}")

    user_request_parts.append("\nПредставь результат в указанном структурированном формате, включая Черту Характера, Идеал, Привязанность и Слабость.")
    user_request_string = "\n".join(user_request_parts)

    full_prompt_for_gemini = [SYSTEM_MESSAGE_FULL_CHAR_GEMINI_PREFIX + user_request_string]

    logger.info(f"Запрос на генерацию от user_id: {user_id}. Параметры: Раса='{user_race}', Класс='{user_class}', Фон='{user_background}', Мировоззрение='{user_alignment}', Локация='{user_location}', Статы='{user_stats_preference}', Детали='{user_details}'")

    raw_llm_response = generate_content_with_gemini(full_prompt_for_gemini, temperature=0.85)

    pdf_buffer_to_return = None # Инициализируем буфер для возврата

    if raw_llm_response and not raw_llm_response.startswith(("ЗАПРОС ЗАБЛОКИРОВАН", "КОНТЕНТ ЗАБЛОКИРОВАН", "ОШИБКА API", "Модель не вернула", "Модель вернула пустой")):
        # Сохранение текстового файла ответа LLM 
        text_filename_base = f"character_profile_text_{user_id}"
        text_filename_ts = get_timestamp_filename(text_filename_base, "txt", GEMINI_MODEL_NAME)
        text_filepath = os.path.join(TEXT_OUTPUT_DIR, text_filename_ts)
        try:
            with open(text_filepath, "w", encoding="utf-8") as f:
                f.write(f"UserID: {user_id}\nМодель: {GEMINI_MODEL_NAME}\nТемпература: 0.85\n\n")
                f.write(f"--- ЗАПРОС ПОЛЬЗОВАТЕЛЯ (обработанный) ---\n{user_request_string}\n\n")
                f.write(f"--- ПОЛНЫЙ ПРОМПТ ДЛЯ GEMINI ---\n{full_prompt_for_gemini[0]}\n\n")
                f.write(f"--- ОТВЕТ LLM (СЫРОЙ) ---\n{raw_llm_response}")
            logger.info(f"Сырой текстовый результат для user_id {user_id} сохранен в: {text_filepath}")
        except Exception as e_save_text:
            logger.error(f"Ошибка при сохранении текстового файла {text_filepath}: {e_save_text}")

        parsed_profile = parse_character_profile(raw_llm_response)

        if parsed_profile: # Только если парсинг был успешным
            # Генерация PDF в памяти
            pdf_buffer_to_return = create_character_sheet_pdf(parsed_profile)


        return {
            "text_profile": raw_llm_response,
            "pdf_buffer": pdf_buffer_to_return, # Возвращаем буфер
            "parsed_data": parsed_profile
        }
    else:
        logger.error(f"Не удалось получить валидный ответ от LLM для user_id {user_id}. Ответ: {raw_llm_response}")
        return {
            "text_profile": raw_llm_response,
            "pdf_buffer": None, # Возвращаем None для буфера
            "parsed_data": None
        }
