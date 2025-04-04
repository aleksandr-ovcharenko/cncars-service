import logging
from datetime import datetime

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

        # Список обязательных полей
        required_fields = {
            'brand': "марку автомобиля",
            'model': "модель автомобиля",
            'year': "год выпуска",
            'engine': "объем двигателя",
            'power': "мощность двигателя",
            'price': "цену автомобиля",
            'mileage': "пробег автомобиля"
        }

        # Проверяем наличие всех обязательных полей
        missing_fields = [field_name for field, field_name in required_fields.items()
                          if field not in parsed_data or parsed_data[field] is None]

        if missing_fields:
            error_message = "❌ Не хватает данных:\n"
            error_message += "\n".join(f"• {field}" for field in missing_fields)
            error_message += "\n\nПожалуйста, укажите все необходимые параметры."
            example = "\n\nПример правильного формата:\nVolkswagen Tiguan\n2024 г.в.\n2.0 л\n200 л.с.\n50 000 км\n29 500 $"
            await message.answer(error_message + example)
            return

        validations = {
            'year': lambda x: 1900 < x < (datetime.now().year + 1),
            'engine': lambda x: 0.5 < x < 10,
            'power': lambda x: 50 < x < 1500,
            'price': lambda x: x > 100,
            'mileage': lambda x: x >= 0
        }

        invalid_fields = []
        for field, validator in validations.items():
            if field in parsed_data and not validator(parsed_data[field]):
                invalid_fields.append(field)

        if invalid_fields:
            await message.answer(f"❌ Некорректные значения для: {', '.join(invalid_fields)}")
            return

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
                    engine=parsed_data['engine'],
                    power=parsed_data['power'],
                    mileage=parsed_data['mileage'],
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

        # Получение рыночных цен
        try:
            async with PriceService() as price_service:
                market_data = await price_service.get_market_prices(
                    brand=parsed_data.get('brand', ''),
                    model=parsed_data.get('model', ''),
                    engine=parsed_data['engine'],
                    power=parsed_data['power'],
                    mileage=parsed_data['mileage'],
                    year=parsed_data['year']
                )

            if market_data and isinstance(market_data, dict):
                # Получаем цены напрямую из корня market_data, а не из price_stats
                price_min = market_data.get('price_min')
                price_max = market_data.get('price_max')

                # Форматируем цены с разделителями тысяч
                formatted_min = f"{price_min:,} ₽".replace(',', ' ') if price_min else 'N/A'
                formatted_max = f"{price_max:,} ₽".replace(',', ' ') if price_max else 'N/A'

                response.extend([
                    f"\n🏷 <b>Рыночные цены:</b>",
                    f"• Минимальная: {formatted_min}",
                    f"• Максимальная: {formatted_max}",
                    f"• Объявлений: {market_data.get('ads_count', 0)}",
                    f"• <a href='{market_data.get('url', '')}'>Ссылка на поиск</a>",
                    f"• Заголовок: {market_data.get('page_title', 'N/A')}"
                ])

                logging.info(f"Результаты парсинга цен: {market_data.get('listings')}")

                if market_data.get('listings'):
                    response.append("\n🔍 <b>Последние объявления:</b>")
                    for idx, item in enumerate(market_data['listings'][:5], 1):
                        # Проверяем, есть ли все обязательные данные и не равны ли они нулю
                        price = item.get('price')
                        mileage = item.get('mileage')
                        year = item.get('year')

                        if price and mileage and year:
                            # Форматируем цену и пробег с разделителями тысяч
                            formatted_price = f"{price:,}".replace(',', ' ') + " ₽"

                            response.append(f"   {formatted_price} | {year} г. | {mileage} км.")

        except Exception as e:
            logging.error(f"Ошибка при получении рыночных цен: {str(e)}", exc_info=True)

        await message.answer("\n".join(response), parse_mode="HTML", disable_web_page_preview=True)

    except Exception as e:
        logging.critical(f"Непредвиденная ошибка: {str(e)}", exc_info=True)
        await message.answer("⚠️ Произошла непредвиденная ошибка. Попробуйте позже.")
