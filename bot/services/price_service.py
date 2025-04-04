from typing import List, Dict

import aiohttp

from bot.parsers.drom_parser import DromDetailedParser


class PriceService:
    async def __aenter__(self):
        # Инициализация (если нужно, например подключение к API, сессия и т.д.)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Очистка ресурсов, если нужно (закрытие сессии и т.д.)
        pass

    async def get_market_prices(self, brand: str, model: str, year: int) -> dict:
        async with aiohttp.ClientSession() as session:
            drom_parser = DromDetailedParser(session)
            drom_prices_raw = await drom_parser.get_prices({
                'brand': brand,
                'model': model,
                'year': year
            })
            return {
                'drom': drom_prices_raw.get('listings', []) if drom_prices_raw else []
            }
