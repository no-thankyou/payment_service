"""Тесты запросов профиля."""
import json
from functools import lru_cache

import pytest
from fastapi.testclient import TestClient

from api.app import app, status

client = TestClient(app)


@pytest.fixture
@lru_cache
def user_token(phone='+79999999999'):
    """Получение токена для авторизации."""
    client.post('/api/v1/auth/sms-send', data='{"phone":"' + phone + '"}')
    auth = client.post('/api/v1/auth/login',
                       data='{"phone":"' + phone + '","code":111111}')
    return auth.json()['access_token']


def test_anon_profile():
    """Тест попытки получить профиль без авторизаци."""
    profile = client.get('/internal/v1/profile')
    assert profile.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_new_profile(user_token):
    """Тест получения незаполненного профиля."""
    profile = client.get('/internal/v1/profile',
                         headers={'Authorization': f'Bearer {user_token}'})
    # проверяем статус ответа
    assert profile.status_code == status.HTTP_200_OK
    # проверяем поля в ответе
    profile = profile.json()
    assert profile['phone'] == '+79999999999'
    assert profile['name'] == ''
    assert profile['lastname'] == ''
    assert profile['email'] is None
    assert profile['birthday'] is None


def test_update_profile(user_token):
    """Тест обновления полей профиля."""
    new_data = {'name': 'test user', 'email': 'some@email.domain'}
    profile = client.put('/internal/v1/profile/', data=json.dumps(new_data),
                         headers={'Authorization': f'Bearer {user_token}'})
    # проверяем статус
    assert profile.status_code == status.HTTP_200_OK
    updated_profile = profile.json()

    # проверяем обновление полей
    assert updated_profile['name'] == new_data['name']
    assert updated_profile['email'] == new_data['email']


def test_update_with_error(user_token):
    """Тест ошибки при обновлении полей профиля."""
    new_data = {'birthday': '00.123.12412'}
    profile = client.put('/internal/v1/profile/', data=json.dumps(new_data),
                         headers={'Authorization': f'Bearer {user_token}'})
    assert profile.status_code == status.HTTP_400_BAD_REQUEST
    profile = profile.json()
    assert 'birthday' in profile['detail'][0]['loc']


def test_get_full_profile(user_token):
    """Тест получения профиля после обновлений."""
    profile = client.get('/internal/v1/profile',
                         headers={'Authorization': f'Bearer {user_token}'})
    # проверяем статус ответа
    assert profile.status_code == status.HTTP_200_OK
    # проверяем поля в ответе
    profile = profile.json()
    assert profile['phone'] == '+79999999999'
    assert profile['name'] == 'test user'
    assert profile['lastname'] == ''
    assert profile['email'] == 'some@email.domain'
    assert profile['birthday'] is None
