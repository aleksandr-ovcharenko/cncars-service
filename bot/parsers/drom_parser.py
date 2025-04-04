import json
import logging
import re
from datetime import datetime
from typing import Dict, Optional, List
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

import aiohttp
from bs4 import BeautifulSoup

from utils.logger import setup_logging

# Настройка логгирования
setup_logging()


class DromDetailedParser:
    BASE_URL = "https://auto.drom.ru"  # Основной домен
    REGIONAL_URLS = {
        'spb': 'https://spb.drom.ru',
        'msk': 'https://moskva.drom.ru',
    }

    def __init__(self, session: aiohttp.ClientSession, region: str = None):
        self.session = session
        self.base_url = self.REGIONAL_URLS.get(region, self.BASE_URL)
        logging.info(f"Инициализирован парсер Drom для региона: {region or 'общий'}")

    async def get_prices(self, car_data: Dict) -> Optional[Dict]:
        """Получение цен с расширенными параметрами"""
        try:
            logging.info(f"Начало парсинга для {car_data.get('brand')} {car_data.get('model')}")

            # Формирование URL с параметрами
            url_params = self.build_url_params(car_data)
            logging.debug(f"Сформированные параметры: {url_params}")

            url = f"{self.base_url}/{self.normalize_brand(car_data['brand'])}/{self.normalize_model(car_data['model'])}/?{url_params}"
            logging.info(f"Итоговый URL запроса: {url}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept-Language": "ru-RU,ru;q=0.9",
                "Referer": f"{self.base_url}/"
            }

            async with self.session.get(url, headers=headers) as response:
                if response.status != 200:
                    logging.error(f"Ошибка HTTP: {response.status}")
                    return None

                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')

                # Сохраняем HTML для отладки
                with open("last_debug_page.html", "w", encoding="utf-8") as f:
                    f.write(html)

                return self.parse_page_data(soup, url)

        except Exception as e:
            logging.error(f"Ошибка парсинга: {str(e)}", exc_info=True)
            return None

    def build_url_params(self, car_data: Dict) -> str:
        """Формирование полного набора параметров URL"""
        params = {
            'order': 'price',
            'unsold': '1',
            'minyear': car_data.get('year', datetime.now().year) - 1,
            'maxyear': car_data.get('year', datetime.now().year) + 1,
        }

        # Добавляем параметры, если они есть в car_data
        optional_params = {
            'engine': ('mv', 'xv', 0.3),
            'power': ('minpower', 'maxpower', 30),
            'mileage': ('minprobeg', 'maxprobeg', 20000),
            'price': ('minprice', 'maxprice', 200000)
        }

        for param, (min_key, max_key, delta) in optional_params.items():
            if param in car_data:
                value = float(car_data[param])
                params[min_key] = max(0, value - delta)
                params[max_key] = value + delta

        # Добавляем специфичные параметры
        if 'transmission' in car_data:
            params['transmission'] = self.normalize_transmission(car_data['transmission'])

        if 'drive_type' in car_data:
            params['privod'] = self.normalize_drive_type(car_data['drive_type'])

        return urlencode(params)

    def parse_page_data(self, soup: BeautifulSoup, url: str) -> Dict:
        """Парсинг данных со страницы"""
        result = {
            'url': self._clean_url(url),  # Нормализуем URL
            'source': 'drom.ru',
            'timestamp': datetime.now().isoformat()
        }

        # 1. Мета-данные
        meta_data = self.extract_meta_data(soup)
        if meta_data:
            result.update(meta_data)
            # Переносим цены в корень результата для удобства
            if 'price_stats' in meta_data:
                result['price_min'] = meta_data['price_stats'].get('min')
                result['price_max'] = meta_data['price_stats'].get('max')
                result['price_avg'] = meta_data['price_stats'].get('avg')

        # 2. Заголовок страницы
        title_data = self.extract_title_stats(soup)
        if title_data:
            result.update(title_data)

        # 3. Список объявлений
        listings_data = self.extract_listings_data(soup)
        if listings_data:
            result['listings'] = listings_data

        logging.info("Успешно собраны данные: %s", json.dumps(result, indent=2, ensure_ascii=False))
        return result

    def _clean_url(self, url: str) -> str:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        # Удаляем пустые параметры
        clean_query = {k: v for k, v in query.items() if any(v)}
        return urlunparse(parsed._replace(query=urlencode(clean_query, doseq=True)))

    def extract_meta_data(self, soup: BeautifulSoup) -> Dict:
        """Извлечение статистики цен с проверкой данных"""
        try:
            meta_tag = soup.find('meta', {'name': 'candy.config'})
            if not meta_tag:
                return {}

            config = json.loads(meta_tag.get('content', '{}'))
            cf = config.get('cf', {})
            p_data = cf.get('p', {})

            # Проверяем и форматируем цены
            price_min = int(p_data.get('min', 0)) or None
            price_max = int(p_data.get('max', 0)) or None
            price_avg = int(p_data.get('avg', 0)) or None

            return {
                'price_stats': {
                    'min': price_min,
                    'max': price_max,
                    'avg': price_avg,
                    'formatted': {
                        'min': f"{price_min:,} ₽".replace(',', ' ') if price_min else 'N/A',
                        'max': f"{price_max:,} ₽".replace(',', ' ') if price_max else 'N/A',
                        'avg': f"{price_avg:,} ₽".replace(',', ' ') if price_avg else 'N/A'
                    }
                },
                'price_min': int(cf.get('p', {}).get('min', 0)),
                'price_max': int(cf.get('p', {}).get('max', 0)),
                'year_min': int(cf.get('y', {}).get('min', 0)),
                'year_max': int(cf.get('y', {}).get('max', 0)),
                'engine_min': float(cf.get('v', {}).get('min', 0)),
                'engine_max': float(cf.get('v', {}).get('max', 0))
            }
        except Exception as e:
            logging.error(f"Ошибка парсинга мета-данных: {str(e)}")
            return {}

    def extract_title_stats(self, soup: BeautifulSoup) -> Dict:
        """Извлечение данных из заголовка страницы с улучшенным парсингом"""
        try:
            title_tag = soup.find('title')
            if not title_tag:
                return {}

            title = title_tag.text.strip()
            stats = {
                'page_title': title,
                'ads_count': 0,
                'price_from': 0
            }

            # Парсинг количества объявлений
            count_match = re.search(r'(\d[\d\s]*) объявлени[йяе]', title)
            if count_match:
                stats['ads_count'] = int(count_match.group(1).replace(' ', ''))

            # Парсинг начальной цены
            price_match = re.search(r'от ([\d\s]+)\s?руб', title.replace('\xa0', ' '))
            if price_match:
                stats['price_from'] = int(price_match.group(1).replace(' ', ''))

            return stats
        except Exception as e:
            logging.error(f"Ошибка парсинга заголовка: {str(e)}")
            return {}

    def extract_listings_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Извлечение данных объявлений с расширенной информацией"""
        try:
            items = soup.select('a[data-ftid="bulls-list_bull"]')[:5]  # Берем больше объявлений
            if not items:
                return []

            listings = []
            for item in items:
                try:
                    # Основные данные
                    price = self.parse_price(item.select_one('[data-ftid="bull_price"]'))
                    title = item.select_one('[data-ftid="bull_title"]').text.strip()
                    url = item['href']

                    # Дополнительные данные
                    description = self.parse_description(item)
                    details = self.parse_details(item)
                    location = self.parse_location(item)

                    listings.append({
                        'price': price,
                        'title': title,
                        'url': self.ensure_absolute_url(url),
                        'description': description,
                        'details': details,
                        'location': location,
                        'timestamp': datetime.now().isoformat()
                    })
                except Exception as e:
                    logging.debug(f"Ошибка парсинга объявления: {str(e)}")
                    continue

            return listings
        except Exception as e:
            logging.error(f"Ошибка парсинга списка объявлений: {str(e)}")
            return []

    # Дополнительные методы парсинга
    def parse_price(self, price_element) -> int:
        """Парсинг цены с обработкой разных форматов"""
        if not price_element:
            return 0

        price_text = price_element.text
        return int(re.sub(r'[^\d]', '', price_text)) if price_text else 0

    def parse_description(self, item) -> str:
        """Парсинг описания объявления"""
        desc_element = item.select_one('[data-ftid="bull_description"]')
        return desc_element.text.strip() if desc_element else ""

    def parse_details(self, item) -> Dict:
        """Парсинг характеристик автомобиля"""
        details = {}
        info_elements = item.select('[data-ftid="bull_description-item"]')

        for element in info_elements:
            text = element.text.strip()
            if 'год' in text:
                details['year'] = int(re.search(r'\d{4}', text).group())
            elif 'км' in text:
                details['mileage'] = int(re.sub(r'[^\d]', '', text))
            elif 'л.с.' in text:
                details['power'] = int(re.sub(r'[^\d]', '', text))
            elif 'л' in text and 'л.с.' not in text:
                details['engine'] = float(re.search(r'[\d\.]+', text).group())

        return details

    def ensure_absolute_url(self, url: str) -> str:
        """Преобразование относительных URL в абсолютные"""
        if url.startswith('http'):
            return url
        return f"{self.base_url}{url}"

    # Нормализация параметров
    @staticmethod
    def normalize_brand(brand: str) -> str:
        brand = brand.lower().strip()
        brand_map = {
            'mercedes': 'mercedes-benz',
            'vw': 'volkswagen',
            'bmw': 'bmw',
            'toyota': 'toyota',
            'lada': 'vaz',
            'volkswagen': 'volkswagen'
        }
        return brand_map.get(brand, brand.replace(' ', '-'))

    @staticmethod
    def normalize_model(model: str) -> str:
        model = model.lower().strip()
        model_map = {
            'x5': 'x5',
            'camry': 'camry',
            'e-class': 'e-klasse',
            'c-class': 'c-klasse',
            'tiguan': 'tiguan'
        }
        return model_map.get(model, model.replace(' ', '-'))

    @staticmethod
    def normalize_transmission(transmission: str) -> str:
        transmission = transmission.lower().strip()
        return {
            'автомат': '2',
            'механика': '1',
            'робот': '3',
            'вариатор': '4'
        }.get(transmission, '1')

    @staticmethod
    def normalize_drive_type(drive_type: str) -> str:
        drive_type = drive_type.lower().strip()
        return {
            'передний': '1',
            'задний': '2',
            'полный': '3'
        }.get(drive_type, '1')


async def main():
    """Пример использования с расширенными параметрами"""
    async with aiohttp.ClientSession() as session:
        parser = DromDetailedParser(session, region='spb')

        car_data = {
            'brand': 'Volkswagen',
            'model': 'Tiguan',
            'year': 2024,
            'engine': 2.0,
            'power': 200,
            'mileage': 40000,
            'transmission': 'автомат',
            'drive_type': 'полный',
            'minprice': 2000000,
            'maxprice': 5000000
        }

        result = await parser.get_prices(car_data)

        if result:
            print("\nРезультаты парсинга:")
            print(f"URL: {result['url']}")
            print(f"Статистика цен: {result.get('price_stats', {})}")
            print(f"Количество объявлений: {result.get('ads_count', 0)}")

            if result.get('listings'):
                print("\nОбъявления:")
                for idx, item in enumerate(result['listings'], 1):
                    print(f"{idx}. {item['title']}")
                    print(f"   Цена: {item['price']:,} ₽")
                    print(f"   Пробег: {item['details'].get('mileage', 'N/A')} км")
                    print(f"   Год: {item['details'].get('year', 'N/A')}")
                    print(f"   Ссылка: {item['url']}")
                    print()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
