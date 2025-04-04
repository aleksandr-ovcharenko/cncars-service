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
    BASE_URL = "https://moscow.drom.ru"  # Основной домен
    REGIONAL_URLS = {
        'spb': 'https://spb.drom.ru',
        'msk': 'https://moskva.drom.ru',
    }

    def __init__(self, session: aiohttp.ClientSession, region: str = None):
        self.session = session
        self.base_url = self.REGIONAL_URLS.get(region, self.BASE_URL)

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
        """Формирование полного URL с учетом всех параметров авто"""
        params = {
            'order': 'price',
            'unsold': '1',
            'minyear': car_data.get('year', datetime.now().year) - 1,
            'maxyear': car_data.get('year', datetime.now().year) + 1,
        }
        logging.info(f"car_data: {car_data}")

        # Параметры двигателя (±20% от указанного объема)
        if car_data.get('engine'):
            engine = float(car_data['engine'])
            delta = engine * 0.2  # 20% в обе стороны
            params.update({
                'mv': round(max(0.1, engine - delta), 1),
                'xv': round(engine + delta, 1)
            })

        # Параметры мощности (±20% от указанной)
        if car_data.get('power'):
            power = int(car_data['power'])

            delta = power * 0.2  # 20% в обе стороны
            params.update({
                'minpower': int(max(10, power - delta)),
                'maxpower': int(power + delta)
            })

        # Параметры пробега (+50% от указанного)
        if car_data.get('mileage'):
            mileage = int(car_data['mileage'])
            params.update({
                'maxprobeg': int(mileage * 1.5)  # Ищем авто с пробегом до +50% от указанного
            })

        # Параметры цены (если нужно)
        if car_data.get('price'):
            price = float(car_data['price'])
            params.update({
                'minprice': int(price * 0.8),  # -20%
                'maxprice': int(price * 1.2)  # +20%
            })

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

    def extract_listings_data(self, soup: BeautifulSoup) -> Optional[List[Dict]]:
        """Извлечение данных объявлений с улучшенным логгированием"""
        try:

            # Пытаемся найти JSON с данными
            script_tags = soup.find_all('script', {'type': 'application/ld+json'})
            listings = []

            for idx, script_tag in enumerate(script_tags[:5], 1):  # Ограничиваем 10 первыми скриптами
                try:
                    # Парсинг JSON данных
                    data = json.loads(script_tag.string)

                    # Извлекаем нужные данные из каждого объекта
                    if isinstance(data, dict):  # Проверяем, что это объект
                        listing = {
                            'price': data.get('offers', {}).get('price', 0),
                            'title': data.get('name', ''),
                            'url': data.get('url', ''),
                            'year': data.get('vehicleModelDate', '').split('-')[0] if data.get(
                                'vehicleModelDate') else '',
                            'mileage': data.get('mileageFromOdometer', {}).get('value', 0),
                            'engine': data.get('engineSpecification', {}).get('engineDisplacement', 0),
                            'power': data.get('vehicleEngine', {}).get('horsepower', 0)
                        }

                        listings.append(listing)
                        logging.debug(f"Обработано объявление #{idx}: {listing}")

                except Exception as e:
                    logging.warning(f"Ошибка парсинга JSON объявления #{idx}: {str(e)}")

            logging.info(f"Успешно извлечено {len(listings)} объявлений")
            return listings if listings else None

        except Exception as e:
            logging.error(f"Ошибка при извлечении объявлений: {str(e)}", exc_info=True)
            return None

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
            label = element.select_one('.bull-description-label')
            value = element.select_one('.bull-description-value')
            if label and value:
                details[label.text.strip()] = value.text.strip()

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
