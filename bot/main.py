import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.handlers import commands, messages
from utils.logger import setup_logging

setup_logging()


async def main():
    bot = Bot(token="7549988426:AAGZj8Jt9QWt1HeJhcCp5VgjP-XBCKtHQIc")  # Используем токен из конфига
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(commands.router)
    dp.include_router(messages.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
