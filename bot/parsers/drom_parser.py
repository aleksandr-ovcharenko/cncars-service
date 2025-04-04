import json
import logging
import re
from typing import Dict, Optional, List
from urllib.parse import urlencode

import aiohttp
from bs4 import BeautifulSoup

from utils.logger import setup_logging

# Настройка логгирования
setup_logging()


class DromDetailedParser:
    BASE_URL = "https://spb.drom.ru"  # Изменили на региональный URL

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        logging.info("Инициализирован расширенный парсер Drom")

    async def get_prices(self, car_data: Dict) -> Optional[Dict]:
        """Получение цен с учётом всех параметров"""
        try:
            logging.info(f"Начало парсинга для {car_data.get('brand')} {car_data.get('model')}")

            # Формирование URL с параметрами
            url_params = self.build_url_params(car_data)
            logging.debug(f"Сформированные параметры: {url_params}")

            url = f"{self.BASE_URL}/{self.normalize_brand(car_data['brand'])}/{self.normalize_model(car_data['model'])}/?{url_params}"
            logging.info(f"Итоговый URL запроса: {url[:100]}...")  # Логируем начало URL

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "ru-RU,ru;q=0.9",
                "Referer": f"{self.BASE_URL}/"
            }

            async with self.session.get(url, headers=headers) as response:
                logging.info(f"Получен ответ, статус: {response.status}")

                if response.status != 200:
                    logging.error(f"Ошибка HTTP: {response.status}")
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Сохраняем HTML для отладки
                with open("last_debug_page.html", "w", encoding="utf-8") as f:
                    f.write(html)
                logging.debug("HTML страницы сохранён в last_debug_page.html")

                # Извлечение данных
                result = {
                    'url': url,
                    'source': 'drom.ru'
                }

                # 1. Из мета-тегов
                meta_data = self.extract_meta_data(soup)
                if meta_data:
                    result.update(meta_data)

                # 2. Из заголовка страницы
                title_data = self.extract_title_data(soup)
                if title_data:
                    result.update(title_data)

                # 3. Из списка объявлений (первые 3)
                listings_data = self.extract_listings_data(soup)
                if listings_data:
                    result['listings'] = listings_data

                logging.info("Успешно собраны данные:")
                logging.info(json.dumps(result, indent=2, ensure_ascii=False))

                return result if result else None

        except Exception as e:
            logging.error(f"Критическая ошибка: {str(e)}", exc_info=True)
            return None

    def build_url_params(self, car_data: Dict) -> str:
        """Формирование параметров URL"""
        params = {
            'minyear': car_data.get('year', 2023) - 1,
            'maxyear': car_data.get('year', 2023) + 1,
            'unsold': '1',
            'order': 'price'
        }

        # Двигатель
        if car_data.get('engine'):
            params['mv'] = float(car_data['engine']) - 0.2
            params['xv'] = float(car_data['engine']) + 0.2
            logging.debug(f"Установлены параметры двигателя: {params['mv']}-{params['xv']} л")

        # Мощность
        if car_data.get('power'):
            params['minpower'] = int(car_data['power']) - 20
            params['maxpower'] = int(car_data['power']) + 20
            logging.debug(f"Установлены параметры мощности: {params['minpower']}-{params['maxpower']} л.с.")

        # Пробег
        if car_data.get('mileage'):
            params['minprobeg'] = int(car_data['mileage']) - 10000
            params['maxprobeg'] = int(car_data['mileage']) + 10000
            logging.debug(f"Установлены параметры пробега: {params['minprobeg']}-{params['maxprobeg']} км")

        return urlencode(params)

    def extract_meta_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Извлечение данных из мета-тегов"""
        try:
            meta_tag = soup.find('meta', {'name': 'candy.config'})
            if not meta_tag:
                logging.warning("Мета-тег candy.config не найден")
                return None

            config = json.loads(meta_tag.get('content', '{}'))
            cf = config.get('cf', {})

            return {
                'price_min': int(cf.get('p', {}).get('min', 0)),
                'price_max': int(cf.get('p', {}).get('max', 0)),
                'year_min': int(cf.get('y', {}).get('min', 0)),
                'year_max': int(cf.get('y', {}).get('max', 0)),
                'engine_min': float(cf.get('v', {}).get('min', 0)),
                'engine_max': float(cf.get('v', {}).get('max', 0))
            }
        except Exception as e:
            logging.error(f"Ошибка парсинга мета-данных: {str(e)}")
            return None

    def extract_title_data(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Извлечение данных из заголовка страницы"""
        try:
            title = soup.title.string
            if not title:
                return None

            ads_count = 0
            match = re.search(r'(\d+) объявлени[йяе]', title)
            if match:
                ads_count = int(match.group(1))

            price_match = re.search(r'от ([\d\s]+) руб', title.replace('\xa0', ' '))
            price_from = int(price_match.group(1).replace(' ', '')) if price_match else 0

            return {
                'ads_count': ads_count,
                'price_from': price_from,
                'page_title': title
            }
        except Exception as e:
            logging.error(f"Ошибка парсинга заголовка: {str(e)}")
            return None

    def extract_listings_data(self, soup: BeautifulSoup) -> Optional[List[Dict]]:
        """Извлечение данных из первых объявлений"""
        try:
            items = soup.select('a[data-ftid="bulls-list_bull"]')[:3]
            if not items:
                logging.warning("Не найдено объявлений на странице")
                return None

            listings = []
            for item in items:
                try:
                    price = int(item.select_one('[data-ftid="bull_price"]').text
                                .replace(' ', '').replace('₽', ''))
                    title = item.select_one('[data-ftid="bull_title"]').text.strip()
                    url = item['href']

                    listings.append({
                        'price': price,
                        'title': title,
                        'url': url if url.startswith('http') else f"{self.BASE_URL}{url}"
                    })
                except Exception as e:
                    logging.debug(f"Ошибка парсинга объявления: {str(e)}")
                    continue

            return listings if listings else None
        except Exception as e:
            logging.error(f"Ошибка парсинга списка объявлений: {str(e)}")
            return None

    def normalize_brand(self, brand: str) -> str:
        brand = brand.lower().strip()
        brand_map = {
            'mercedes': 'mercedes-benz',
            'vw': 'volkswagen',
            'bmw': 'bmw',
            'toyota': 'toyota',
            'lada': 'vaz'
        }
        return brand_map.get(brand, brand)

    def normalize_model(self, model: str) -> str:
        model = model.lower().strip()
        model_map = {
            'x5': 'x5',
            'camry': 'camry',
            'e-class': 'e_klasse',
            'c-class': 'c_klasse'
        }
        return model_map.get(model, model.replace(' ', '_'))


async def main():
    """Пример использования с полным набором параметров"""
    async with aiohttp.ClientSession() as session:
        parser = DromDetailedParser(session)

        car_data = {
            'brand': 'BMW',
            'model': 'X5',
            'year': 2023,
            'engine': 3.0,
            'power': 249,
            'mileage': 30000
        }

        result = await parser.get_prices(car_data)

        if result:
            print("\nРезультаты парсинга:")
            print(f"URL: {result['url']}")
            print(f"Диапазон цен: {result.get('price_min', 'N/A')} - {result.get('price_max', 'N/A')} ₽")
            print(f"Количество объявлений: {result.get('ads_count', 'N/A')}")

            if result.get('listings'):
                print("\nПримеры объявлений:")
                for idx, item in enumerate(result['listings'], 1):
                    print(f"{idx}. {item['price']:,} ₽ - {item['title']}")
                    print(f"   {item['url']}")
        else:
            print("Не удалось получить данные")


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
