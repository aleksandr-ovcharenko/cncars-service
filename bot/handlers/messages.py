import logging

from aiogram import Router, types

from bot.services.calculator import calculate_customs
from parsers.parsers import parse_car_info
from services.price_service import PriceService
from utils.logger import setup_logging

router = Router()

# Настройка логгирования
setup_logging()


@router.message()
async def handle_car_info(message: types.Message):
    try:
        logging.info(f"Начало обработки сообщения: {message.text[:50]}...")

        parsed_data = parse_car_info(message.text)
        if not parsed_data:
            logging.warning("Не удалось распарсить данные авто")
            await message.answer("❌ Не удалось распознать данные авто")
            return

        logging.info(f"Парсинг успешен: {parsed_data}")

        # Расчет таможни
        try:
            result = calculate_customs(
                price_usd=parsed_data['price'],
                engine=parsed_data['engine'],
                power=parsed_data['power'],
                year=parsed_data['year']
            )
            logging.info("Расчет таможни выполнен успешно")
        except Exception as e:
            logging.error(f"Ошибка расчета таможни: {str(e)}", exc_info=True)
            result = None

        # Получение рыночных цен
        market_data = {}
        try:
            async with PriceService() as price_service:
                market_data = await price_service.get_market_prices(
                    brand=parsed_data.get('brand', ''),
                    model=parsed_data.get('model', ''),
                    year=parsed_data['year']
                )
            logging.info(f"Результаты парсинга цен: {market_data}")
        except Exception as e:
            logging.error(f"Ошибка при получении рыночных цен: {str(e)}", exc_info=True)

        # Формирование ответа
        response = [
            f"🚗 <b>Данные авто:</b>",
            f"• Год: {parsed_data['year']}",
            f"• Объем: {parsed_data['engine']} л",
            f"• Мощность: {parsed_data['power']} л.с.",
            f"• Цена: {parsed_data['price']:,}$",
            f"• Пробег: {parsed_data['mileage']:,} км"
        ]

        if result:
            response.extend([
                f"\n📌 <b>Расчет растаможки:</b>",
                f"- Пошлина: {result['customs_duty']:,.0f} ₽",
                f"- Акциз: {result['excise']:,.0f} ₽",
                f"- НДС: {result['vat']:,.0f} ₽",
                f"- Утильсбор: {result['recycling_fee']:,.0f} ₽",
                f"- Доп. расходы: {result['additional_costs']:,.0f} ₽",
                f"- Сервис: {result['service_costs']:,.0f} ₽",
                f"\n💵 <b>Итого: {result['total']:,.0f} ₽</b>\n"
            ])
        else:
            response.append("\n⚠️ Не удалось рассчитать таможню")

        market_data = {}
        try:
            async with PriceService() as price_service:
                market_data = await price_service.get_market_prices(
                    brand=parsed_data.get('brand', ''),
                    model=parsed_data.get('model', ''),
                    year=parsed_data['year']
                )
            # Формируем сообщение с данными
            response += [
                f"🏷 <b>Цены на Drom.ru:</b>",
                f"Минимальная цена: {market_data.get('price_min', 'N/A')} ₽",
                f"Максимальная цена: {market_data.get('price_max', 'N/A')} ₽",
                f"Страница поиска: <a href='{market_data.get('url', '')}'>Перейти на страницу</a>",
                f"Заголовок страницы: {market_data.get('page_title', 'N/A')}"
            ]

            if isinstance(market_data, str):  # Добавляем проверку, что market_data — это словарь
                logging.error("Ожидался словарь, но получена строка.")
                market_data = {}
        except Exception as e:
            logging.error(f"Ошибка при получении рыночных цен: {str(e)}", exc_info=True)

        await message.answer("\n".join(response), parse_mode="HTML", disable_web_page_preview=True)
        logging.info("Сообщение успешно отправлено")

    except Exception as e:
        logging.critical(f"Непредвиденная ошибка: {str(e)}", exc_info=True)
        await message.answer("⚠️ Произошла непредвиденная ошибка. Попробуйте позже.")
