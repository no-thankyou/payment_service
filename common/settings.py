"""Настройки для проекта."""
from datetime import timedelta

from pydantic import BaseSettings
from fastapi_jwt_auth import AuthJWT


class Settings(BaseSettings):
    """Класс с настройками из окружения."""

    debug: bool = True

    postgres_password: str
    postgres_user: str
    postgres_db: str
    postgres_host: str
    redis_host: str
    redis_port: int = 6379
    redis_db: int = 0

    sms_counts: int = 3
    time_limit: int = 5

    auth_access_token_lifetime: int = 15 * 60
    auth_refresh_token_lifetime: int = 15 * 60 * 60 * 24

    authjwt_secret_key: str = 'secret'
    authjwt_token_location: set = {'cookies', 'headers'}
    authjwt_cookie_csrf_protect: bool = False
    authjwt_cookie_secure: bool = True
    authjwt_denylist_enabled: bool = True
    authjwt_denylist_token_checks: set = {'access', 'refresh'}
    access_expires: int = timedelta(minutes=15).total_seconds()
    refresh_expires: int = timedelta(days=15).total_seconds()
    authjwt_cookie_samesite: str = 'lax'

    process_timeout: int = 300
    geo_data_by_ip = 'https://geolocation-db.com/json/{ip}&position=true'

    class Config:
        env_file = '.env.example'
        env_file_encoding = 'utf-8'


@AuthJWT.load_config
def get_config():
    """Функция для библиотеки с JWT."""
    return Settings()


settings = Settings()
