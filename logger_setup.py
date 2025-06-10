import logging

def setup_logger():
    logger = logging.getLogger(__name__.split('.')[0])
    logger.setLevel(logging.INFO)

    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

# Инициализируем логгер при импорте модуля
logger = setup_logger()