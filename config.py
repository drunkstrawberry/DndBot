import os

# --- Ключи и Настройки Модели ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")  # ЗАМЕНИТЕ ВАШИМ КЛЮЧОМ
GEMINI_MODEL_NAME = "gemini-1.5-flash-latest"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") # ЗАМЕНИТЕ ВАШИМ ТОКЕНОМ

# --- Пути к Директориям ---
OUTPUT_DIR_BOT_GENERATED = "telegram_bot_generated_characters"
PDF_OUTPUT_DIR = os.path.join(OUTPUT_DIR_BOT_GENERATED, "pdfs")
TEXT_OUTPUT_DIR = os.path.join(OUTPUT_DIR_BOT_GENERATED, "texts")
FONT_PATH_FOR_BOT_SESSION = os.getenv("FONT_PATH_FOR_BOT_SESSION", "")
# --- Путь к Шрифту для PDF ---
# Укажите путь к файлу шрифта DejaVuSans.ttf или другому .ttf шрифту с поддержкой кириллицы
# Например: FONT_PATH_FOR_BOT_SESSION = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
# Если оставить пустым или None, будет использован стандартный шрифт Helvetica (без кириллицы)


# --- Настройки Безопасности Gemini ---
GEMINI_SAFETY_SETTINGS = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
]

# --- Системное Сообщение для Gemini ---
SYSTEM_MESSAGE_FULL_CHAR_GEMINI_PREFIX = """Ты - ИИ-ассистент, создающий полных персонажей для Dungeons & Dragons 5-й редакции.
Твоя задача - сгенерировать Имя, Расу, Класс, Предысторию (Background), Мировоззрение, Характеристики (стандартный набор из 6), стартовый Инвентарь и Предысторию (текстовое описание), Черту Характера, Идеал, Привязанность и Слабость.
Строго придерживайся материалов из System Reference Document (SRD 5.1).
Если какой-либо параметр не указан пользователем, выбери подходящий из SRD 5.1.
Если характеристики не указаны или есть только пожелания, предложи типичное или сбалансированное распределение.
Инвентарь должен состоять из 3-5 предметов, подходящих для стартового персонажа.
Текстовая Предыстория должна быть на 2-5 предложений и соответствовать всем выбранным элементам.

Ответ должен быть структурирован СТРОГО следующим образом, с каждым заголовком на НОВОЙ СТРОКЕ:
Имя: [текст]
Раса: [текст]
Класс: [текст]
Предыстория (Background): [текст]
Мировоззрение: [текст]
Характеристики: [текст, например: Сила 10, Ловкость 14,...]
Инвентарь: [текст, предметы через запятую]
Предыстория: [многострочный текст]
Черта Характера: [текст]
Идеал: [текст]
Привязанность: [текст]
Слабость: [текст]

ВАЖНО: Убедись, что заголовок "Предыстория:" (для текстового описания) не конфликтует с "Предыстория (Background):" (для названия бэкграунда).
Каждый заголовок должен быть точно таким, как указано выше (например, "Предыстория (Background):", а не просто "Background:").
"""
