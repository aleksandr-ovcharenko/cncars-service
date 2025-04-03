from pathlib import Path

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    TG_BOT_TOKEN: str

    class Config:
        # Указываем абсолютный путь к .env относительно расположения config.py
        env_file = Path(__file__).parent / '.env'
        env_file_encoding = 'utf-8'


def load_config() -> Config:
    return Config()
