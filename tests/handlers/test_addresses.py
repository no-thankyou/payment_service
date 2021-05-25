import json
from functools import lru_cache

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


@pytest.fixture
@lru_cache
def user_token(phone='+79999999998'):
    """Получение токена для авторизации."""
    client.post('/api/v1/auth/sms-send', data='{"phone":"' + phone + '"}')
    auth = client.post('/api/v1/auth/login',
                       data='{"phone":"' + phone + '","code":111111}')
    return auth.json()['access_token']


def test_get_empty_addresses(user_token):
    """Тест получения пустого списка адресов."""
    addresses = client.get('/api/v1/addresses',
                           headers={'Authorization': f'Bearer {user_token}'})
    assert addresses.json() == []


def test_add_address(user_token):
    """Тест добавления адреса."""
    data = {'city': 'Волгоград', 'address': 'Невская 12', 'floor': 1,
            'apartment': 12, 'is_default': True}
    address = client.post('/api/v1/addresses/',
                          headers={'Authorization': f'Bearer {user_token}'},
                          data=json.dumps(data))

    # проверяем ответ сервера
    assert address.status_code == status.HTTP_200_OK
    # проверяем данные из ответа
    address = address.json()
    assert address['city'] == data['city']
    assert address['address'] == data['address']

    # проверяем что объект добавился и есть в списке
    addresses = client.get('/api/v1/addresses',
                           headers={'Authorization': f'Bearer {user_token}'})
    assert len(addresses.json()) == 1


def test_set_new_default_address(user_token):
    """Тест установки нового адреса по умолчанию."""
    # проверяем наличие адреса у юзера
    addresses = client.get('/api/v1/addresses',
                           headers={'Authorization': f'Bearer {user_token}'})
    assert len(addresses.json()) == 1

    # добавляем новый дефолтный адрес
    data = {'city': 'Москва', 'address': 'Рижское шоссе 10', 'floor': 2,
            'apartment': 12, 'is_default': True}
    address = client.post('/api/v1/addresses/',
                          headers={'Authorization': f'Bearer {user_token}'},
                          data=json.dumps(data))

    # проверяем ответ сервера
    assert address.status_code == status.HTTP_200_OK
    # проверяем данные из ответа
    address = address.json()
    assert address['city'] == data['city']
    assert address['address'] == data['address']
    address_id = address['id']

    # проверяем что дефолтный адрес только один
    addresses = client.get('/api/v1/addresses',
                           headers={'Authorization': f'Bearer {user_token}'})
    assert len(addresses.json()) == 2
    for address in addresses.json():
        if address['id'] == address_id:
            assert address['is_default'] == True
        else:
            assert address['is_default'] == False


def test_update_address(user_token):
    """Тест обновления существующего адреса."""
    # проверяем что есть адреса
    addresses = client.get('/api/v1/addresses',
                           headers={'Authorization': f'Bearer {user_token}'})
    assert len(addresses.json()) > 0

    # выбираем адес для обновления
    address = addresses.json()[0]
    data = {'floor': '5', 'apartment': '60'}
    updated_address = client.put('/internal/v1/addresses/' + str(address['id']),
                                 headers={'Authorization': f'Bearer {user_token}'},
                                 data=json.dumps(data))

    # проверяем ответ сервера
    assert updated_address.status_code == status.HTTP_200_OK
    # проверяем обновленные данные
    updated_address = updated_address.json()
    assert updated_address['floor'] == data['floor']
    assert updated_address['apartment'] == data['apartment']
    assert updated_address['address'] == address['address']
    assert updated_address['city'] == address['city']


def test_get_addresses(user_token):
    """Тест получения созданных адресов."""
    addresses = client.get('/api/v1/addresses',
                           headers={'Authorization': f'Bearer {user_token}'})
    assert len(addresses.json()) > 0


def test_delete_address(user_token):
    """Тест удаления адреса."""
    # проверяем что есть адреса для удаления
    addresses = client.get('/api/v1/addresses',
                           headers={'Authorization': f'Bearer {user_token}'})
    current_len = len(addresses.json())
    assert current_len > 0

    # выбираем последний адрес для удаления
    address = addresses.json()[-1]
    client.delete('/internal/v1/addresses/' + str(address['id']),
                  headers={'Authorization': f'Bearer {user_token}'})

    # проверяем что адрес удалился
    addresses = client.get('/api/v1/addresses',
                           headers={'Authorization': f'Bearer {user_token}'})

    assert len(addresses.json()) == current_len - 1
