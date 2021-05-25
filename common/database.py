"""Работа с базой данных."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import ClauseElement

from common.settings import settings

SQLALCHEMY_DATABASE_URL = (f'postgresql://{settings.postgres_user}:'
                           f'{settings.postgres_password}@'
                           f'{settings.postgres_host}/{settings.postgres_db}')

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

Base.metadata.create_all(bind=engine)


def get_db():
    """Функция получения коннекта к БД."""
    db = DataBase()
    try:
        yield db
    finally:
        db.close()


class MetaSingleton(type):
    """Метакласс для создания синглтонов."""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """Функция создает только 1 экземпляр любого класса."""
        if cls not in cls._instances:
            cls._instances[cls] = (super(MetaSingleton, cls)
                                   .__call__(*args, **kwargs))
        return cls._instances[cls]


class DataBase(metaclass=MetaSingleton):
    """Класс для работы с БД."""

    def __init__(self, session=SessionLocal):
        """Инициализируем БД."""
        self.db = session()

    def close(self):
        """Закрытие коннекта к базе."""
        self.db.close()

    def delete(self, model, instance):
        """Удаление объекта из БД."""
        self.db.query(model).filter(model.id == instance.id).delete()
        self.save()

    def get_or_create(self, model, defaults=None, **kwargs):
        """
        Получить или создать экземпляр модели.

        Реализовано по аналогии с Django, возвращает кортеж, где
        первый элемент - экземпляр модели
        второй элемент - bool признак создан ли экземпляр или уже был.
        """
        instance = self.get_by_id(model, **kwargs)
        if instance:
            return instance, False
        params = {k: v for k, v in kwargs.items()
                  if not isinstance(v, ClauseElement)}
        params.update(defaults or {})
        instance = model(**params)
        self.add(instance)
        self.save()
        return instance, True

    def get_by_id(self, model, **kwargs):
        """Получение объекта по идентификатору."""
        return self.db.query(model).filter_by(**kwargs).first()

    def get_all_objects(self, model):
        """Получает список всех объектов модели."""
        return self.db.query(model).all()

    def save(self):
        """Сохранение изменений в БД."""
        self.db.commit()

    def add(self, instance):
        """Добавление нового элемента в бд какой-либо модели."""
        self.db.add(instance)

    def filter(self, model, *args):  # noqa: A003
        """Фильтр объектов модели по параметрам."""
        return self.db.query(model).filter(*args)

    def refresh(self, instance):
        """Обновление конктретного экземпляра некотроой модели из БД."""
        self.db.refresh(instance)
