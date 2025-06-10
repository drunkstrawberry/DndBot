import logging
import os
import re
import time
import datetime
import google.generativeai as genai
from config import (
    GOOGLE_API_KEY,
    GEMINI_MODEL_NAME,
    GEMINI_SAFETY_SETTINGS,
    SYSTEM_MESSAGE_FULL_CHAR_GEMINI_PREFIX
)

logger = logging.getLogger(__name__)
model_gemini = None

def init_gemini():
    global model_gemini
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "api_ключ_google_ai_studio":
        logger.error("ОШИБКА: API ключ Google не установлен в config.py.")
        return False

    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        logger.info("API ключ Google AI Studio успешно сконфигурирован.")

        model_gemini = genai.GenerativeModel(
            GEMINI_MODEL_NAME,
            safety_settings=GEMINI_SAFETY_SETTINGS
        )
        logger.info(f"Модель '{GEMINI_MODEL_NAME}' успешно инициализирована.")
        return True
    except Exception as e:
        logger.error(f"Ошибка инициализации Gemini: {e}")
        return False

def get_timestamp_filename(base_name, extension, model_name_for_file=""):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_model_name = ""
    if model_name_for_file:
        safe_model_name = "_" + model_name_for_file.replace(":", "_").replace("/", "_").replace(".", "_")
    return f"{base_name}{safe_model_name}_{timestamp}.{extension}"

def generate_content_with_gemini(prompt_parts, temperature=0.7, retries=3, delay=5):
    if not model_gemini:
        logger.error("Модель Gemini не инициализирована. Вызовите init_gemini() сначала.")
        return "ОШИБКА: Модель Gemini не инициализирована."

    logger.info(f"Отправка запроса к модели: {GEMINI_MODEL_NAME}...")
    current_retry = 0

    while current_retry < retries:
        try:
            generation_config = genai.types.GenerationConfig(temperature=temperature)
            response = model_gemini.generate_content(
                contents=prompt_parts,
                generation_config=generation_config
            )

            if response.prompt_feedback and response.prompt_feedback.block_reason:
                reason = response.prompt_feedback.block_reason_message
                logger.warning(f"Промпт был заблокирован: {reason}")
                return f"ЗАПРОС ЗАБЛОКИРОВАН: {reason}"

            if not response.candidates:
                logger.warning("Модель не вернула кандидатов.")
                return "Модель не вернула кандидатов."

            generated_text = ""
            if hasattr(response, 'text'):
                 generated_text = response.text
            elif response.parts:
                 generated_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))


            candidate = response.candidates[0]
            if candidate.finish_reason.name == "SAFETY":
                safety_info = "Нет деталей"
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    safety_info = "; ".join(
                        f"{r.category.name}: {r.probability.name}"
                        for r in candidate.safety_ratings
                    )
                logger.warning(f"Контент заблокирован (SAFETY). Детали: {safety_info}")
                return f"КОНТЕНТ ЗАБЛОКИРОВАН (SAFETY): {generated_text or safety_info}"

            if not generated_text:
                reason = candidate.finish_reason.name
                if reason != "STOP":
                    logger.warning(f"Пустой текст, причина: {reason}")
                if not response.parts and not hasattr(response, 'text'):
                     logger.warning("Модель вернула пустой ответ без явной причины.")

            logger.info(f"Ответ от {GEMINI_MODEL_NAME} получен.")
            return generated_text

        except Exception as e:
            current_retry += 1
            error_message = str(e)
            logger.error(f"Ошибка API (попытка {current_retry}/{retries}): {error_message}")

            if "429" in error_message or "quota" in error_message.lower() or "resource_exhausted" in error_message.lower():
                return "Ошибка квоты API."
            if "API key not valid" in error_message or "permission_denied" in error_message.lower():
                return "Неверный API ключ или права."

            if current_retry < retries:
                time.sleep(delay)
            else:
                return f"ОШИБКА API: Макс. попыток. Ошибка: {error_message}"

    return f"ОШИБКА API: Нет ответа после {retries} попыток."


def parse_character_profile(raw_text):
    profile = {}
    fields_ordered = [
        ("Имя", "name"),
        ("Раса", "race"),
        ("Класс", "class"),
        ("Предыстория (Background)", "background_name"),
        ("Мировоззрение", "alignment"),
        ("Характеристики", "stats"),
        ("Инвентарь", "inventory"),
        ("Черта Характера", "trait"),
        ("Идеал", "ideal"),
        ("Привязанность", "bond"),
        ("Слабость", "flaw")
    ]

    current_text = raw_text
    for field_ru, field_en in fields_ordered:
        pattern = re.compile(rf"^{re.escape(field_ru)}:\s*([\s\S]+?)(?=\n[А-ЯЁ][\w\s\(\)-]+:|$)", re.MULTILINE | re.UNICODE)
        match = pattern.search(current_text)
        if match:
            value = match.group(1).strip()
            profile[field_en] = value
        else:
            pattern_looser = re.compile(rf"{re.escape(field_ru)}:\s*([\s\S]+?)(?=\n[А-ЯЁ][\w\s\(\)-]+:|$)", re.MULTILINE | re.UNICODE)
            match_looser = pattern_looser.search(raw_text)
            if match_looser:
                 profile[field_en] = match_looser.group(1).strip()
            else:
                profile[field_en] = "Не указано"
                logger.warning(f"Не удалось извлечь поле '{field_ru}' из ответа LLM.")

    backstory_text_match = re.search(
        r"\nИнвентарь:[^\n]*\n+Предыстория:\s*([\s\S]+?)(?=\nЧерта Характера:|$)",
        raw_text,
        re.MULTILINE | re.UNICODE
    )
    if backstory_text_match:
        profile["backstory_text"] = backstory_text_match.group(1).strip()
    else:
        simple_bs_match = re.search(r"(?<!\(Background\):\s*\n)Предыстория:\s*([\s\S]+?)(?=\n[А-ЯЁ][\w\s\(\)-]+:|$)", raw_text, re.MULTILINE | re.UNICODE)
        if simple_bs_match:
            if "Предыстория (Background):" not in simple_bs_match.group(0):
                 profile["backstory_text"] = simple_bs_match.group(1).strip()
            else:
                 profile["backstory_text"] = "Не удалось извлечь описание предыстории."
                 logger.warning("Не удалось извлечь текстовое описание 'Предыстория:' (возможно, конфликт с 'Предыстория (Background):').")
        else:
            profile["backstory_text"] = "Не удалось извлечь описание предыстории."
            logger.warning("Не удалось извлечь текстовое описание 'Предыстория:'. Проверьте структуру ответа LLM.")


    logger.info(f"Распарсенный профиль (первые несколько полей): "
                f"Name: {profile.get('name')}, Race: {profile.get('race')}, Class: {profile.get('class')}")
    return profile