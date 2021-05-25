"""Общая логика для настройки тестов."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.database import Base, get_db, DataBase
from api.app import app
from common.settings import settings

SQLALCHEMY_DATABASE_URL = (f'postgresql://{settings.postgres_user}:'
                           f'{settings.postgres_password}@'
                           f'{settings.postgres_host}/{settings.postgres_db}')

engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False,
                                   bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Получение БД с новым подключением."""
    db = DataBase(TestingSessionLocal)
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
