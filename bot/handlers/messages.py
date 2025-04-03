from aiogram import Router, types
from aiogram.filters import Command
from bot.services.calculator import calculate_customs
from bot.utils.parsers import parse_car_info

router = Router()

@router.message()
async def handle_car_info(message: types.Message):
    parsed_data = parse_car_info(message.text)

    if not parsed_data:
        await message.answer(
            "❌ Ошибка формата. Пример:\n"
            "<i>BMW X5 2022, 3.0 л, 249 л.с., 50000$, 30000 км</i>",
            parse_mode="HTML"
        )
        return

    try:
        result = calculate_customs(
            price_usd=parsed_data['price'],
            engine=parsed_data['engine'],
            power=parsed_data['power'],
            year=parsed_data['year']
        )

        response = (
            f"🚗 <b>Результат:</b>\n"
            f"• Год: {parsed_data['year']}\n"
            f"• Объем: {parsed_data['engine']} л\n"
            f"• Мощность: {parsed_data['power']} л.с.\n"
            f"• Цена: {parsed_data['price']:,}$\n\n"
            f"📌 *Расчет растаможки:*\n"
            f"- Пошлина: {result['customs_duty']:,.0f} ₽\n"
            f"- Акциз: {result['excise']:,.0f} ₽\n"
            f"- НДС: {result['vat']:,.0f} ₽\n"
            f"- Утильсбор: {result['recycling_fee']:,.0f} ₽\n"
            f"- Доп. расходы: {result['additional_costs']:,.0f} ₽\n\n"
            f"💵 *Итого: {result['total']:,.0f} ₽*"
        )

        await message.answer(response, parse_mode="HTML")

    except Exception as e:
        await message.answer("⚠️ Ошибка расчета. Попробуйте позже")