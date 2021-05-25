"""Вспомогательные сервисы."""
from datetime import datetime, timedelta

import redis
import requests
from fastapi import Request
from common.settings import settings
from common.text import get_text as _

from user_agents import parse


class PhoneException(Exception):
    """Ошибки при проверке телефона или смс."""


class PhoneAttempts:
    """Класс для попыток ввода кода из смс."""

    def __init__(self, phone: str):
        """Инициализация попыток для номера."""
        self._redis = redis.Redis(host=settings.redis_host,
                                  port=settings.redis_port,
                                  db=settings.redis_db,
                                  decode_responses=True)
        self.phone = phone
        self.code_key = f'code-{phone}'
        self.attempts_key = f'attempts-{phone}'

    def set_phone_code(self, code: str):
        """Сохранение в redis последнего отправленного кода."""
        self._redis.set(self.code_key, code)
        self._redis.rpush(self.attempts_key, datetime.now().timestamp())

    def check_code(self, code: str) -> bool:
        """Проверка кода из смс."""
        in_redis_code = self._redis.get(self.code_key) or None
        if self.__check_last_send():
            raise PhoneException(_('code_expires_error'))
        if not in_redis_code == code:
            raise PhoneException(_('wrong_sms_code'))
        self.set_phone_code('------')
        return True

    def can_send_sms(self) -> bool:
        """Проверка возможности отправки смс."""
        if settings.sms_counts <= self.__get_counts():
            raise PhoneException(_('attempts_error'))
        if not self.__check_last_send():
            raise PhoneException(_('timeout_error'))
        return True

    def __get_counts(self) -> int:
        """Подсчет количества попыток отправки смс."""
        time_border = (datetime.now() - timedelta(minutes=settings.time_limit))
        attempts = 0
        for attempt in self._redis.lrange(self.attempts_key, 0, 10):
            if float(attempt) > time_border.timestamp():
                attempts += 1
        return attempts

    def __check_last_send(self) -> bool:
        """Проверка времени последней отправки смс."""
        last = self._redis.lrange(self.attempts_key, -1, -1)
        minute_ago = (datetime.now() - timedelta(minutes=1)).timestamp()
        if last and float(last[0]) > minute_ago:
            return False
        return True


class TokensDenyList:
    """Класс для управления отозванными токенами."""

    def __init__(self):
        """Создание подключения к Redis."""
        self._redis = redis.Redis(host=settings.redis_host,
                                  port=settings.redis_port,
                                  db=settings.redis_db,
                                  decode_responses=True)

    def check_token(self, decrypted_token: dict) -> bool:
        """Проверяется отозван ли токен."""
        jti = decrypted_token['jti']
        entry = self._redis.get(jti)
        return entry and entry == 'true'

    def add_token(self, jti: str):
        """Добаваляем токен в отозванные."""
        self._redis.setex(jti, settings.refresh_expires, 'true')


def user_agent_parser(user_agent: str, request: Request):
    """
    Вспомогательная функция для получения устройства, ос пользователя и ip.

    :param user_agent: данные из user-agent
    :param request: данные из запроса
    """
    ip_address = request.scope.get('root_path')
    agent_from_user = f'{request.headers.get("Agent", "")}/ '
    platform_from_user = f'{request.headers.get("platform", "")}/ '
    user_agent_data = parse(user_agent)
    agent = (f'{agent_from_user}{user_agent_data.browser[0]}'
             f'{user_agent_data.browser[2]}')
    platform = (f'{platform_from_user}{user_agent_data.device[0]}',
                f' {user_agent_data.os[0]}{user_agent_data.os[2]}')
    return agent, platform, get_location_user(ip_address)


def get_location_user(ip_address: str):
    """
    Вспомогательная функция для получения города пользователя.

    :param ip_address: ip пользователя
    """
    geo_data = (requests.get(settings.geo_data_by_ip
                             .format(ip=ip_address)).json())

    return f'{geo_data["country_name"]}, {geo_data["city"]}'
