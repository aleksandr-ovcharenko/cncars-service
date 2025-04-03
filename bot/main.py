import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import commands, messages
from configs.config import load_config


async def main():
    try:
        config = load_config()
    except Exception as e:
        logging.critical(f"Ошибка загрузки конфига: {e}")
        raise
    bot = Bot(token=config.TG_BOT_TOKEN)  # Используем токен из конфига
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(commands.router)
    dp.include_router(messages.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
