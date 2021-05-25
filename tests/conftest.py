"""Настройка pytest."""
import inspect
import sys

import redis

from common import models
from common.database import DataBase
from common.settings import settings


def pytest_sessionstart(session):
    """
    Запускается перед тестами.

    Очищает редис от всех ключей, необходимо для сброса попыток перед тестами.
    Очищает все БД для чистого запуска.
    """
    redis_conn = redis.Redis(host=settings.redis_host,
                             port=settings.redis_port,
                             db=settings.redis_db,
                             decode_responses=True)
    redis_conn.flushdb()

    db = DataBase()
    tables = []
    for name, obj in inspect.getmembers(sys.modules[models.__name__]):
        if inspect.isclass(obj) and issubclass(obj, models.BaseModel) and obj != models.BaseModel:
            tables.append(obj.__tablename__)
    truncate_sql = 'TRUNCATE ' + ', '.join(tables) + ' RESTART IDENTITY;'
    db.db.bind.engine.execute(truncate_sql)
