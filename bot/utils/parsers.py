import logging
import re
from typing import Dict, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_car_info(text: str) -> Optional[Dict[str, float]]:
    """Парсинг данных авто с поддержкой произвольных форматов"""
    try:
        # Нормализация текста: удаление лишних пробелов, приведение к нижнему регистру
        normalized_text = ' '.join(text.split()).lower()

        # Парсинг года (поддержка разных форматов: 2023, 23 г., 2024 г.в.)
        year_match = re.search(
            r'(?:20)?(\d{2})\s*(?:г\.?|год|г\.в\.|выпуска|в\.)',
            normalized_text
        )
        year = int(f"20{year_match.group(1)}") if year_match else None

        # Парсинг объёма двигателя (поддержка: 2.0л, 2.0 см3, 2.0 л., 2л и т.д.)
        engine_match = re.search(
            r'(\d+\.?\d*)\s*(?:л|литр|см3|см\^3|л\.|литра)',
            normalized_text
        )
        engine = float(engine_match.group(1)) if engine_match else None

        # Парсинг мощности (поддержка: л.с., hp, кВт, kW)
        power_match = re.search(
            r'(\d+)\s*(?:л\.с\.|hp|квт|kw|лошад|сил)',
            normalized_text
        )
        power = int(power_match.group(1)) if power_match else None

        # Парсинг цены (поддержка: $34000, 29 500 $, 34000USD и т.д.)
        price_match = re.search(
            r'(\d[\d\s]*)\s*(?:\$|usd|долл)',
            normalized_text
        )
        price = int(price_match.group(1).replace(' ', '')) if price_match else None

        # Парсинг пробега (поддержка: 100тыс, 100000 км, 100км и т.д.)
        mileage_match = re.search(
            r'(\d+)\s*(?:км|тыс|к\.м\.|километр)',
            normalized_text
        )
        if mileage_match:
            mileage = int(mileage_match.group(1))
            if 'тыс' in normalized_text[mileage_match.start():mileage_match.end()+5]:
                mileage *= 1000
        else:
            mileage = None

        # Собираем результат только с найденными полями
        result = {}
        if year: result['year'] = year
        if engine: result['engine'] = engine
        if power: result['power'] = power
        if price: result['price'] = price
        if mileage: result['mileage'] = mileage

        return result if result else None

    except Exception as e:
        logger.error(f"Ошибка парсинга: {e}")
        return None