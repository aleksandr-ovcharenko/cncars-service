import logging
import re
from typing import Dict, Optional

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('car_parser.log')
    ]
)
logger = logging.getLogger(__name__)

def log_parse_attempt(field: str, pattern: str, text: str, success: bool, match=None):
    """Логирование попытки парсинга"""
    status = "УСПЕХ" if success else "НЕУДАЧА"
    message = f"Парсинг {field}: {status} | Паттерн: {pattern}"
    if match:
        message += f" | Найдено: {match.group()}"
    logger.debug(message)
    if not success:
        logger.debug(f"Текст для анализа: {text[:100]}...")

def parse_car_info(text: str) -> Optional[Dict[str, float]]:
    """Парсинг данных авто с поддержкой произвольных форматов и логгированием"""
    logger.info(f"\nНачало парсинга текста: {text[:50]}...")

    try:
        # Нормализация текста
        normalized_text = ' '.join(text.split()).lower()
        logger.debug(f"Нормализованный текст: {normalized_text}")

        result = {}

        # Парсинг года
        year_pattern = r'(?:20)?(\d{2})\s*(?:г\.?|год|г\.в\.|выпуска|в\.)'
        year_match = re.search(year_pattern, normalized_text)
        log_parse_attempt("года", year_pattern, normalized_text, bool(year_match), year_match)
        if year_match:
            result['year'] = int(f"20{year_match.group(1)}")

        # Парсинг объёма двигателя
        engine_pattern = r'(\d+\.?\d*)\s*(?:л|литр|см3|см\^3|л\.|литра)'
        engine_match = re.search(engine_pattern, normalized_text)
        log_parse_attempt("объёма двигателя", engine_pattern, normalized_text, bool(engine_match), engine_match)
        if engine_match:
            result['engine'] = float(engine_match.group(1))

        # Парсинг мощности
        power_pattern = r'(\d+)\s*(?:л\.с\.|hp|квт|kw|лошад|сил)'
        power_match = re.search(power_pattern, normalized_text)
        log_parse_attempt("мощности", power_pattern, normalized_text, bool(power_match), power_match)
        if power_match:
            result['power'] = int(power_match.group(1))

        # Парсинг цены
        price_pattern = r'(\d[\d\s]*)\s*(?:\$|usd|долл)'
        price_match = re.search(price_pattern, normalized_text)
        log_parse_attempt("цены", price_pattern, normalized_text, bool(price_match), price_match)
        if price_match:
            result['price'] = int(price_match.group(1).replace(' ', ''))

        # Парсинг пробега
        mileage_pattern = r'(\d+)\s*(?:км|тыс|к\.м\.|километр)'
        mileage_match = re.search(mileage_pattern, normalized_text)
        log_parse_attempt("пробега", mileage_pattern, normalized_text, bool(mileage_match), mileage_match)
        if mileage_match:
            mileage = int(mileage_match.group(1))
            match_text = normalized_text[mileage_match.start():mileage_match.end()+5]
            if 'тыс' in match_text:
                mileage *= 1000
                logger.debug(f"Пробег в тыс. км, преобразован в: {mileage} км")
            result['mileage'] = mileage

        if result:
            logger.info(f"Успешно распарсено: {result}")
            return result
        else:
            logger.warning("Не удалось распарсить ни одного поля")
            return None

    except Exception as e:
        logger.error(f"Критическая ошибка при парсинге: {str(e)}", exc_info=True)
        return None

# Тестовые примеры
test_cases = [
    "Бмв X3 М-пакет 23 г.выпуска Объем 2.0см3 Турбо 180 кW 100 пробег 34000$",
    "Volkswagen Tiguan L 2024 г.в. 2.0см3 Цена 29 500 $",
    "Некорректная строка без данных",
    "Audi A4 2021 2.0л 249л.с. 85тыс.км $25000",
    "Только цена: 30000$"
]

for test in test_cases:
    print(f"\nТестируем: {test}")
    parsed = parse_car_info(test)
    print(f"Результат: {parsed}")