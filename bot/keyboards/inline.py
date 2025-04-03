from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

def get_main_menu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        types.InlineKeyboardButton(
            text="📊 Новый расчет",
            callback_data="new_calc"
        ),
        types.InlineKeyboardButton(
            text="📋 Пример данных",
            callback_data="show_example"
        )
    )
    builder.row(
        types.InlineKeyboardButton(
            text="ℹ️ Помощь",
            callback_data="help"
        )
    )
    return builder.as_markup(resize_keyboard=True)