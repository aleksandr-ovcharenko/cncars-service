import logging
import re
from typing import Dict, Optional
from aiogram import types

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_car_info(text: str) -> Optional[Dict[str, float]]:
    """Синхронный парсинг данных авто"""
    try:
        year = int(re.search(r'(20\d{2})', text).group(1))
        engine = float(re.search(r'(\d+\.?\d*)\s*л', text).group(1))
        power = int(re.search(r'(\d+)\s*(л\.с\.|hp)', text, re.IGNORECASE).group(1))
        price = int(re.search(r'(\d+)\s*\$', text).group(1))
        mileage = int(re.search(r'(\d+)\s*(км|тыс)', text).group(1)) if re.search(r'(\d+)\s*(км|тыс)', text) else 0

        return {
            'year': year,
            'engine': engine,
            'power': power,
            'price': price,
            'mileage': mileage
        }
    except (AttributeError, ValueError) as e:
        return None
