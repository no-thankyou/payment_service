import json
from functools import lru_cache

import pytest
from fastapi.testclient import TestClient

from api.app import app, status
from common.database import DataBase
from common.models import User

client = TestClient(app)
user_without_access = '+79999999977'


@pytest.fixture
@lru_cache
def user_token(phone='+79999999988'):
    """Получение токена для авторизации."""
    client.post('/api/v1/auth/sms-send', data='{"phone":"' + phone + '"}')
    auth = client.post('/api/v1/auth/login',
                       data='{"phone":"' + phone + '","code":111111}')
    db = DataBase()
    user, _ = db.get_or_create(User, phone=phone)
    user.is_admin = True
    db.save()
    return auth.json()['access_token']


def test_add_shop(user_token):
    """Тест добавления магазина."""
    data = {'name': 'Магазин', 'site_url': 'https://cool.site.com/',
            'api_endpoint': '/some/other/endpoint', 'is_active': True}
    shop = client.post('/internal/v1/shops/',
                       headers={'Authorization': f'Bearer {user_token}'},
                       data=json.dumps(data))

    # проверяем ответ сервера
    assert shop.status_code == status.HTTP_200_OK
    # проверяем данные из ответа
    shop = shop.json()
    assert shop['name'] == data['name']
    assert shop['site_url'] == data['site_url']

    # проверяем что объект добавился и есть в списке
    shops = client.get('/internal/v1/shops',
                       headers={'Authorization': f'Bearer {user_token}'})
    assert len(shops.json()) > 0

def test_update_shop(user_token):
    """Тест обновления существующего магазина."""
    # проверяем что есть магазины
    shops = client.get('/internal/v1/shops',
                       headers={'Authorization': f'Bearer {user_token}'})
    assert len(shops.json()) > 0

    # выбираем магазин для обновления
    shop = shops.json()[0]
    data = {'name': 'some_name', 'site_url': 'some_url',
            'api_endpoint': '/hello/is_it_me/yor`re_looking_for',
            'is_active': True}
    updated_shop = client.put('/internal/v1/shops/' + str(shop['id']),
                              headers={'Authorization': f'Bearer {user_token}'},
                              data=json.dumps(data))

    # проверяем ответ сервера
    assert updated_shop.status_code == status.HTTP_200_OK
    # проверяем обновленные данные
    updated_shop = updated_shop.json()
    assert updated_shop['name'] == data['name']
    assert updated_shop['site_url'] == data['site_url']
    assert updated_shop['api_endpoint'] == data['api_endpoint']
    assert updated_shop['is_active'] == shop['is_active']


def test_get_one_shop(user_token):
    """Тест получения отдельного магазина."""
    # проверяем что есть магазины
    shops = client.get('/internal/v1/shops/',
                       headers={'Authorization': f'Bearer {user_token}'})
    # выбираем магазин для обновления
    shop = shops.json()[0]
    # получаем конкретный магазин
    one_shop = client.get('/internal/v1/shops/' + str(shop['id']),
                          headers={'Authorization': f'Bearer {user_token}'})
    one_shop = one_shop.json()
    assert one_shop['name'] == shop['name']
    assert one_shop['site_url'] == shop['site_url']
    assert one_shop['api_endpoint'] == shop['api_endpoint']
    assert one_shop['is_active'] == shop['is_active']


def test_get_shops(user_token):
    """Тест получения созданных магазинов."""
    shops = client.get('/internal/v1/shops/',
                       headers={'Authorization': f'Bearer {user_token}'})
    assert len(shops.json()) > 0


def test_delete_shop(user_token):
    """Тест удаления магазина."""
    # проверяем что есть магазин для удаления
    shops = client.get('/internal/v1/shops/',
                       headers={'Authorization': f'Bearer {user_token}'})
    current_len = len(shops.json())
    assert current_len > 0

    # выбираем магазин для удаления
    shop = shops.json()[2]
    client.delete('/internal/v1/shops/' + str(shop['id']),
                  headers={'Authorization': f'Bearer {user_token}'})

    # проверяем что магазин удалился
    shops = client.get('/internal/v1/shops',
                       headers={'Authorization': f'Bearer {user_token}'})

    assert len(shops.json()) == current_len - 1


def test_without_access(phone=user_without_access):
    """Тест CRUD для пользователя без прав."""
    # Токен без прав админа
    client.post('/api/v1/auth/sms-send', data='{"phone":"' + phone + '"}')
    auth = client.post('/api/v1/auth/login',
                       data='{"phone":"' + phone + '","code":111111}')
    token = auth.json()['access_token']
    # тест GET запроса
    shops = client.get('/internal/v1/shops/',
                       headers={'Authorization': f'Bearer {token}'})
    assert shops.status_code == status.HTTP_404_NOT_FOUND
    # тест POST запроса
    data = {'name': 'Магазин', 'site_url': 'https://cool.site.com/',
            'api_endpoint': '/some/other/endpoint', 'is_active': True}
    shop = client.post('/internal/v1/shops/',
                       headers={'Authorization': f'Bearer {token}'},
                       data=json.dumps(data))
    assert shop.status_code == status.HTTP_404_NOT_FOUND
    # тест PUT запроса
    updated_shop = client.put('/internal/v1/shops/' + str(1),
                              headers={'Authorization': f'Bearer {token}'},
                              data=json.dumps(data))
    assert updated_shop.status_code == status.HTTP_404_NOT_FOUND
    # тест DELETE запроса
    del_shop = client.delete('/internal/v1/shops/' + str(1),
                             headers={'Authorization': f'Bearer {token}'})
    assert del_shop.status_code == status.HTTP_404_NOT_FOUND


