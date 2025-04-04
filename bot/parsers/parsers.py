import json
import logging
import re
from typing import Dict, Optional, List

import aiohttp

from utils.logger import setup_logging

# Настройка логирования
setup_logging()


class CarPriceParser:
    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.session.close()

    async def parse_avito(self, brand: str, model: str, year: float) -> Optional[List[Dict]]:
        """Парсинг цен с Avito"""
        try:
            url = f"https://www.avito.ru/web/1/main/items?key=auto&categoryId=9"
            params = {
                "params": f"pmax=1000000&sort=price&search_title={brand}+{model}&year_from={year - 1}&year_to={year + 1}"
            }

            async with self.session.get(url, params=params) as response:
                data = await response.json()
                return [{
                    'price': item['price'],
                    'url': f"https://www.avito.ru{item['url']}",
                    'source': 'avito'
                } for item in data.get('items', [])[:3]]  # Топ 3 объявления

        except Exception as e:
            logging.error(f"Avito parsing error: {e}")
            return None

    async def parse_autoru(self, brand: str, model: str, year: float) -> Optional[List[Dict]]:
        """Парсинг цен с Auto.ru"""
        try:
            url = "https://auto.ru/-/ajax/desktop/listing/"
            payload = {
                "category": "cars",
                "section": "all",
                "mark": brand.lower(),
                "model": model.lower(),
                "year_from": year - 1,
                "year_to": year + 1,
                "sort": "price-asc"
            }

            async with self.session.post(url, json=payload) as response:
                data = await response.json()
                return [{
                    'price': offer['price'],
                    'url': offer['url'],
                    'source': 'auto.ru'
                } for offer in data.get('offers', [])[:3]]  # Топ 3 объявления

        except Exception as e:
            logging.error(f"Auto.ru parsing error: {e}")
            return None


async def get_market_prices(brand: str, model: str, year: float) -> Dict[str, List[Dict]]:
    """Получение цен с всех площадок"""
    async with CarPriceParser() as parser:
        avito_prices = await get_avito_prices(brand, model, year)
        # autoru_prices = await parser.parse_autoru(brand, model, year)

        return {
            'avito': avito_prices or [],
            # 'autoru': autoru_prices or []
        }


class AvitoParser:
    def __init__(self):
        self.session = aiohttp.ClientSession()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
        }

    async def _make_request(self, url: str, params: dict) -> Optional[dict]:
        """Базовый метод для запросов с логгированием"""
        try:
            logging.debug(f"Отправка запроса на {url} с параметрами: {params}")

            async with self.session.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
            ) as response:

                logging.debug(f"Получен ответ: статус {response.status}")

                if response.status != 200:
                    logging.error(f"Ошибка HTTP: {response.status}")
                    logging.debug(f"Заголовки ответа: {dict(response.headers)}")
                    return None

                content_type = response.headers.get('Content-Type', '')
                if 'application/json' not in content_type:
                    logging.error(f"Неожиданный Content-Type: {content_type}")
                    text = await response.text()
                    logging.debug(f"Тело ответа: {text[:500]}...")  # Логируем первые 500 символов
                    return None

                data = await response.json()
                logging.debug(f"Успешно получены данные: {json.dumps(data, indent=2)[:500]}...")
                return data

        except aiohttp.ClientError as e:
            logging.error(f"Ошибка сети: {str(e)}", exc_info=True)
        except json.JSONDecodeError as e:
            logging.error(f"Ошибка парсинга JSON: {str(e)}")
            text = await response.text()
            logging.debug(f"Сырой ответ: {text[:500]}...")
        except Exception as e:
            logging.error(f"Неожиданная ошибка: {str(e)}", exc_info=True)

        return None

    async def parse_avito(self, brand: str, model: str, year: float) -> Optional[List[Dict]]:
        """Парсинг цен с Avito с детальным логгированием"""
        try:
            logging.info(f"Начало парсинга Avito для {brand} {model} {year}")

            url = "https://www.avito.ru/web/1/main/items"
            params = {
                "key": "auto",
                "categoryId": 9,
                "params": f"pmax=1000000&sort=price&search_title={brand}+{model}&year_from={year - 1}&year_to={year + 1}&localPriority=0"
            }

            data = await self._make_request(url, params)
            if not data:
                logging.warning("Не удалось получить данные с Avito")
                return None

            items = data.get('items', [])
            logging.info(f"Найдено {len(items)} объявлений")

            results = []
            for item in items[:3]:  # Берем первые 3 результата
                try:
                    price = item.get('price')
                    item_url = f"https://www.avito.ru{item.get('url', '')}"

                    if not price or not item_url:
                        logging.debug(f"Пропущен элемент с неполными данными: {item}")
                        continue

                    results.append({
                        'price': price,
                        'url': item_url,
                        'source': 'avito'
                    })

                    logging.debug(f"Добавлено объявление: {price} ₽ - {item_url}")

                except Exception as e:
                    logging.error(f"Ошибка обработки элемента: {str(e)}")
                    logging.debug(f"Проблемный элемент: {item}")

            logging.info(f"Успешно обработано {len(results)} объявлений")
            return results if results else None

        except Exception as e:
            logging.error(f"Критическая ошибка в parse_avito: {str(e)}", exc_info=True)
            return None

    async def close(self):
        await self.session.close()


# Пример использования с дополнительным логгированием
async def get_avito_prices(brand: str, model: str, year: float):
    parser = AvitoParser()
    try:
        logging.info(f"Запрос цен для {brand} {model} ({year})")
        result = await parser.parse_avito(brand, model, year)
        logging.info(f"Результат запроса: {'успех' if result else 'неудача'}")
        return result
    finally:
        await parser.close()
        logging.info("Сессия парсера закрыта")


def log_parse_attempt(field: str, pattern: str, text: str, success: bool, match=None):
    """Логирование попытки парсинга"""
    status = "УСПЕХ" if success else "НЕУДАЧА"
    message = f"Парсинг {field}: {status} | Паттерн: {pattern}"
    if match:
        message += f" | Найдено: {match.group()}"
    logging.debug(message)
    if not success:
        logging.debug(f"Текст для анализа: {text[:100]}...")


def parse_car_info(text: str) -> Optional[Dict[str, float]]:
    """Парсинг данных авто с поддержкой произвольных форматов и логгированием"""
    logging.info(f"\nНачало парсинга текста: {text[:50]}...")

    try:
        # Нормализация текста
        normalized_text = ' '.join(text.split()).lower()
        logging.debug(f"Нормализованный текст: {normalized_text}")

        result = {}

        # Извлечение марки и модели (примерная реализация)
        brand_model = re.search(r'([a-zA-Zа-яА-ЯёЁ]+)\s*([a-zA-Zа-яА-ЯёЁ0-9]*)', text)
        if brand_model:
            result['brand'] = str(f"{brand_model.group(1)}")
            result['model'] = str(f"{brand_model.group(2)}")

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
        mileage_pattern = r'(\d[\d\s,]*)\s*(?:км|тыс|к\.м\.|километр)'
        mileage_match = re.search(mileage_pattern, normalized_text)
        log_parse_attempt("пробега", mileage_pattern, normalized_text, bool(mileage_match), mileage_match)
        if mileage_match:
            mileage_cleaned = mileage_match.group(1).replace(" ", "").replace(",", "")
            mileage = int(mileage_cleaned)
            match_text = normalized_text[mileage_match.start():mileage_match.end() + 5]
            if 'тыс' in match_text:
                mileage *= 1000
                logging.debug(f"Пробег в тыс. км, преобразован в: {mileage} км")
            result['mileage'] = mileage

        if result:
            logging.info(f"Успешно распарсено: {result}")
            return result
        else:
            logging.warning("Не удалось распарсить ни одного поля")
            return None

    except Exception as e:
        logging.error(f"Критическая ошибка при парсинге: {str(e)}", exc_info=True)
        return None


# Тестовые примеры
test_cases = [
    "Volkswagen Tiguan L 2024 г.в. 2.0см3 Цена 29 500 $",
    "Некорректная строка без данных",
    "Только цена: 30000$"
]

for test in test_cases:
    print(f"\nТестируем: {test}")
    parsed = parse_car_info(test)
    print(f"Результат: {parsed}")
