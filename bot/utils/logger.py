import logging
import sys

def setup_logging():
    """Настройка логгирования для всего проекта"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(filename)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler('car_parser.log'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Уменьшаем логирование для сторонних библиотек
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)