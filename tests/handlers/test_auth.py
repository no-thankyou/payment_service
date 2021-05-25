"""Тесты процесса авторизации."""
import json
from datetime import datetime, timedelta

import pytest
import redis
from fastapi.testclient import TestClient

from api.app import app, status
from common.database import DataBase
from common.models import ActiveTokens
from common.settings import settings

client = TestClient(app)


def add_timestamp(phone):
    """Вспомогательная функция для добавения устаревшего кода."""
    redis_conn = redis.Redis(host=settings.redis_host,
                             port=settings.redis_port,
                             db=settings.redis_db,
                             decode_responses=True)
    time = (datetime.now() - timedelta(minutes=1, seconds=1)).timestamp()
    redis_conn.rpush(f'attempts-{phone}', time)


def test_anon_refresh():
    """Тест попытки обновления токена без авторизации."""
    refresh = client.post('/api/v1/auth/refresh')
    assert refresh.status_code == status.HTTP_401_UNAUTHORIZED


def test_send_sms_without_params():
    """Тест отправки запроса на смс без параметров."""
    sms = client.post('/api/v1/auth/sms-send')
    assert sms.status_code == status.HTTP_400_BAD_REQUEST


def test_send_sms_with_wrong_phone():
    """Тест отправки запроса на смс с неверным форматом номера."""
    sms = client.post('/api/v1/auth/sms-send',
                      data=json.dumps({'phone': '12345'}))
    assert sms.status_code == status.HTTP_400_BAD_REQUEST
    assert sms.json()['detail'][0]['msg'] == 'Неверный формат телефона'


def test_send_sms():
    """Тест успешной отправки смс."""
    sms = client.post('/api/v1/auth/sms-send',
                      data=json.dumps({'phone': '+71234567890'}))
    assert sms.status_code == status.HTTP_200_OK
    assert sms.json() == {}


def test_send_sms_in_timeout():
    """Тест повторной попытки отправки смс менее чем через минуту."""
    sms = client.post('/api/v1/auth/sms-send',
                      data=json.dumps({'phone': '+71234567890'}))
    assert sms.status_code == status.HTTP_400_BAD_REQUEST
    assert sms.json()['error'] == 'Повторная отправка смс будет доступна через минуту'


def test_login_with_wrong_code():
    """Тест попытки авторизации с неверным кодом."""
    data = {'phone': '+71234567890', 'code': 123456}
    auth = client.post('/api/v1/auth/login', data=json.dumps(data))
    assert auth.status_code == status.HTTP_400_BAD_REQUEST
    assert auth.json()['error'] == 'Неверный код из СМС'


def test_login_after_timeout():
    """Тест попытки авторизации через минуту после отправки."""
    add_timestamp('+71234567890')
    data = {'phone': '+71234567890', 'code': 111111}
    auth = client.post('/api/v1/auth/login', data=json.dumps(data))
    assert auth.status_code == status.HTTP_400_BAD_REQUEST
    assert auth.json()['error'] == 'Время кода истекло'


def test_success_login():
    """Тест успешной авторизации."""
    # отправляем смс
    sms = client.post('/api/v1/auth/sms-send',
                      data=json.dumps({'phone': '+71234567890'}))
    assert sms.status_code == status.HTTP_200_OK
    assert sms.json() == {}

    # авторизуемся
    data = {'phone': '+71234567890', 'code': 111111}
    auth = client.post('/api/v1/auth/login', data=json.dumps(data))
    assert auth.status_code == status.HTTP_200_OK
    assert auth.cookies.get('access_token_cookie') is not None
    assert auth.cookies.get('refresh_token_cookie') is not None

    auth = auth.json()
    assert 'access_token' in auth.keys()


def test_login_after_success():
    """Тест попытки авторизации после входа."""
    data = {'phone': '+71234567890', 'code': 111111}
    auth = client.post('/api/v1/auth/login', data=json.dumps(data))
    assert auth.status_code == status.HTTP_400_BAD_REQUEST
    assert auth.json()['error'] == 'Неверный код из СМС'


def test_refresh_token():
    """Тест обновления токена."""
    old_access_token = client.cookies.get('access_token_cookie')
    old_refresh_token = client.cookies.get('refresh_token_cookie')
    headers = {'Authorization': f'Bearer {old_refresh_token}'}
    refresh = client.post('/api/v1/auth/refresh', headers=headers,
                          cookies=client.cookies)
    assert refresh.status_code == status.HTTP_200_OK, refresh.json()

    assert refresh.cookies.get('access_token_cookie') != old_access_token
    assert refresh.cookies.get('refresh_token_cookie') != old_refresh_token


def test_logout():
    """Тест запроса на выход."""
    headers = {'Authorization':
                   f"Bearer {client.cookies.get('access_token_cookie')}"}
    logout = client.post('/api/v1/auth/logout', headers=headers,
                         cookies=client.cookies)
    assert logout.status_code == status.HTTP_200_OK
    assert logout.json() == {}

    assert logout.cookies.get('access_token_cookie') is None
    assert logout.cookies.get('refresh_token_cookie') is None


def test_anon_logout():
    """Тест запроса на выход без авторизации."""
    logout = client.post('/api/v1/auth/logout', cookies=client.cookies)
    assert logout.status_code == status.HTTP_401_UNAUTHORIZED
    assert logout.json()['error'] == 'Требуется авторизация'


def test_list_of_active_sessions():
    """Тест списка активных сессий."""
    active_session = client.get('/api/v1/sessions/active_sessions')
    assert len(active_session.json()) > 0


def test_deactivate_session():
    """Тест прекращения сессии."""
    client.post('/api/v1/auth/sms-send',
                data=json.dumps({'phone': '+71234567891'}))
    data = {'phone': '+71234567891', 'code': 111111}
    client.post('/api/v1/auth/login', data=json.dumps(data))

    headers = {'Authorization':
                   f"Bearer {client.cookies.get('access_token_cookie')}"}
    active_session_list = DataBase().get_all_objects(ActiveTokens)
    body_request = {"refresh_id": active_session_list[3].refresh_id}
    deactivate_session = client.post('/internal/v1/sessions/deactivate',
                                     headers=headers, cookies=client.cookies,
                                     data=json.dumps(body_request))
    assert deactivate_session.status_code == status.HTTP_200_OK


def test_create_active_session():
    """Тест создания объекта активной сессии."""
    client.post('/api/v1/auth/sms-send',
                data=json.dumps({'phone': '+71234567890'}))
    data = {'phone': '+71234567890', 'code': 111111}
    client.post('/api/v1/auth/login', data=json.dumps(data))
    active_session_list = DataBase().get_all_objects(ActiveTokens)
    assert len(active_session_list) > 0
