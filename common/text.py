"""Файл с текстами и методом из получения."""

MESSAGES = {
    'none_field_error': 'field may not be None',
    'card_length_error': 'Неккоректная длина номера карты',
    'cannot_change_error': 'Изменения невозможны',
    'phone_field_error': 'Неверный формат телефона',
    'object_not_found': 'Объект не найден',
    'address_not_found': 'Адрес не найден',
    'card_not_found': 'Карта не найдена',
    'default_address_not_found': 'Введите адрес по умолчанию',
    'default_card_not_found': 'Введите карту по умолчанию',
    'code_expires_error': 'Время кода истекло',
    'wrong_sms_code': 'Неверный код из СМС',
    'attempts_error': 'Превышено количество попыток',
    'timeout_error': 'Повторная отправка смс будет доступна через минуту',
    'auth_required': 'Требуется авторизация',
    'order_not_found': 'Заказ не найден',
    'session_not_found': 'Сессия не найдена',
    'not_found_error': 'Раздел не найден',
}


def get_text(code: str) -> str:
    """
    Метод получения текстов.

    Обычно импортируется как ... import get_text as _
    """
    return MESSAGES.get(code, '')
