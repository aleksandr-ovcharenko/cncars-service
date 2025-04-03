from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🚗 Отправьте данные авто в формате:\n"
        "<b>Модель, год, объем, мощность, цена в $</b>\n\n"
        "Пример: <i>BMW X5 2022, 3.0 л, 249 л.с., 50000$</i>",
        parse_mode="HTML"
    )