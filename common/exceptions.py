"""Классы для ошибок приложения."""


class ModelException(Exception):
    """Класс для обработки ошибок моделей."""

    def __init__(self, msg, status_code=400):
        """Создание кастомной ошибки со статусом для ответа."""
        self.message = msg
        self.status = status_code


class AddressException(ModelException):
    """Ошибки при проверке нахождения адреса."""


class CardException(ModelException):
    """Ошибки при проверке нахождения карты."""


class NotFoundException(ModelException):
    """Ошибки при проверке нахождения объекта."""
