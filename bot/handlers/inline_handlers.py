from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

# Обработчик кнопки "Новый расчет"
@router.callback_query(F.data == "new_calc")
async def handle_new_calc(callback: types.CallbackQuery):
    await callback.message.answer(
        "Введите данные авто в формате:\n"
        "<code>Модель, год, объем, мощность, цена</code>",
        parse_mode="HTML"
    )
    await callback.answer()

# Обработчик кнопки "Пример"
@router.callback_query(F.data == "show_example")
async def handle_show_example(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "Пример ввода:\n"
        "<code>BMW X5 2022, 3.0 л, 249 л.с., 50000$</code>\n\n"
        "Скопируйте и отправьте боту",
        parse_mode="HTML"
    )
    await callback.answer()