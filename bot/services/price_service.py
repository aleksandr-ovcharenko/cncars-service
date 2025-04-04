import aiohttp

from bot.parsers.drom_parser import DromDetailedParser


class PriceService:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    # Получаем данные с Drom
    async def get_market_prices(self, brand: str, model: str, year: int) -> dict:
        async with aiohttp.ClientSession() as session:
            drom_parser = DromDetailedParser(session)
            drom_prices_raw = await drom_parser.get_prices({
                'brand': brand,
                'model': model,
                'year': year
            })

            # Подготовим данные для ответа
            if drom_prices_raw:
                result = {
                    'drom': drom_prices_raw.get('listings', []),
                    'price_min': drom_prices_raw.get('price_min', 'N/A'),
                    'price_max': drom_prices_raw.get('price_max', 'N/A'),
                    'ads_count': drom_prices_raw.get('ads_count', 'N/A'),
                    'url': drom_prices_raw.get('url', ''),
                    'page_title': drom_prices_raw.get('page_title', 'N/A')
                }

                # Возвращаем словарь, а не строку
                return result

            return {}  # Возвращаем пустой словарь, если данных нет

