import json
from datetime import datetime
from functools import lru_cache
from unittest.mock import patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from api.app import app
from common.database import DataBase
from common.models import User, Order, OrderStatuses
from worker.tasks import create_order
from common.text import get_text as _



client = TestClient(app)
ITEM_DATA = {"article": "string", "name": "string",
             "price": 0, "shop_id": 1, "quantity": 0,
             "total_price": 0, "discount": 0}
ORDER_DATA = {'number': 1, 'order_sum': 1,
              'total_price': 1, 'delivery_price': 1,
              'discount': 1, 'items': [ITEM_DATA], 'shop_id': 1}
ADDRESS_DATA = {'city': 'Волгоград', 'address': 'Невская 12', 'floor': 1,
                'apartment': 12, 'is_default': True}
CARD_DATA = {"number": "123412341234", "is_default": True}
SHOP_DATA = {'name': 'другой магазин', 'site_url': 'https://cool.site.com/',
             'api_endpoint': '/some/other/endpoint', 'is_active': True}


@pytest.fixture
@lru_cache
def user_token(phone='+79999999955'):
    """Получение токена для авторизации."""
    client.post('/api/v1/auth/sms-send', data='{"phone":"' + phone + '"}')
    auth = client.post('/api/v1/auth/login',
                       data='{"phone":"' + phone + '","code":111111}')
    db = DataBase()
    user, _ = db.get_or_create(User, phone=phone)
    user.is_admin = True
    db.save()
    return auth.json()['access_token']


def default_data(user_token):
    """Вспомогательная функция создания необходимых для заказа данных."""
    address = client.post('/api/v1/addresses/',
                          headers={'Authorization': f'Bearer {user_token}'},
                          data=json.dumps(ADDRESS_DATA))
    card = client.post('/api/v1/cards/',
                       headers={'Authorization': f'Bearer {user_token}'},
                       data=json.dumps(CARD_DATA))
    shop = client.post('/internal/v1/shops/',
                       headers={'Authorization': f'Bearer {user_token}'},
                       data=json.dumps(SHOP_DATA))
    return address, card, shop


def create_multiple_orders(address: int, shop: int, card: int,
                           phone='+79999999955'):
    """Вспомогательная функция создания заказов для проверки фильтров."""
    db = DataBase()
    user, _ = db.get_or_create(User, phone=phone)
    order_1 = {'date': datetime.strptime('01.01.2021', '%d.%m.%Y'),
             'number': 11, 'address_id': address, 'card_id': card,
    'shop_id': shop, 'user_id': user.id, 'order_sum': 11, 'total_price': 11,
    'delivery_price': 11, 'discount': 11}
    order_2 = {'date': datetime.strptime('15.01.2021', '%d.%m.%Y'),
               'number': 11, 'address_id': address, 'card_id': card,
               'shop_id': shop, 'user_id': user.id, 'status':
                   OrderStatuses.CANCELED,
               'order_sum': 22, 'total_price': 22, 'delivery_price': 22,
               'discount': 22}
    dataset = [order_1, order_2]
    for data in dataset:
        db.add(Order(**data))
    db.save()


def create_order_mock(*args):
    """Вспомогательная mock функция, выполняющая запрос на создание заказа."""
    return create_order(*args)


def test_get_empty_orders(user_token):
    """Тест получения пустого списка заказов."""
    orders = client.get('/internal/v1/orders/?page=1&per_page=10',
                        headers={'Authorization': f'Bearer {user_token}'})
    assert orders.json()['orders'] == []


@patch('api.handlers.order.tasks.create_order.delay',
       side_effect=create_order_mock)
def test_create_order(delay_mock,user_token):
    """Тест создания заказа."""
    order = client.post('/api/v1/orders/create',
                        headers={'Authorization': f'Bearer {user_token}'},
                        data=json.dumps(ORDER_DATA))

    # проверяем ответ сервера без учета адреса и карты по умолчанию
    assert order.status_code == status.HTTP_400_BAD_REQUEST
    # вводим адрес и карту по умолчанию и повторяем
    # так же нужен магазин для создания заказа
    default_data(user_token)

    correct_order = client.post('/api/v1/orders/create',

                                headers={'Authorization': f'Bearer {user_token}'},
                                data=json.dumps(ORDER_DATA))
    assert correct_order.status_code == status.HTTP_201_CREATED
    assert correct_order.json()['order_id'] == 1


def test_detail_order_data(user_token):
    """Тест получения отдельного заказа."""
    # проверяем, что есть заказ
    orders = client.get('/internal/v1/orders/?page=1&per_page=10',
                        headers={'Authorization': f'Bearer {user_token}'})
    assert len(orders.json()['orders']) == 1
    order = orders.json()['orders'][0]
    # пробуем получить детальную информацию о нем
    detail_order_data = client.get('/api/v1/orders/' + str(order['id']),
                                   headers={'Authorization': f'Bearer {user_token}'})
    # проверяем ответ сервера
    assert detail_order_data.status_code == status.HTTP_200_OK
    assert detail_order_data.json()['number'] == ORDER_DATA['number']
    assert detail_order_data.json()['order_sum'] == ORDER_DATA['order_sum']
    assert detail_order_data.json()['shop_id'] == ORDER_DATA['shop_id']


def test_get_orders(user_token):
    """Тест получения списка заказов."""
    orders = client.get('/internal/v1/orders/?page=1&per_page=10',
                        headers={'Authorization': f'Bearer {user_token}'})
    assert len(orders.json()['orders'])> 0
    assert orders.status_code == status.HTTP_200_OK


def test_get_orders_with_filters(user_token):
    """Тест получения списка заказов с учетом фильтров  ."""
    # создаем несколько объектов
    address, card, shop = default_data(user_token)
    create_multiple_orders(address.json()['id'],shop.json()['id'],card.json()['id'])
    # проверяем фильтр начала поиска
    orders = client.get('/internal/v1/orders/?page=1&per_page=10&date_from=10.01.2021',
                        headers={'Authorization': f'Bearer {user_token}'})
    assert len(orders.json()['orders']) > 1
    # проверяем фильтр ограничения поиска
    orders = client.get('/internal/v1/orders/?page=1&per_page=10&date_to=16.01'
                        '.2021',
                        headers={'Authorization': f'Bearer {user_token}'})
    assert len(orders.json()['orders']) > 1
    # проверяем оба фильтра
    orders = client.get('/internal/v1/orders/?page=1&per_page=10&date_from=01.01.2021&date_to=16.01.2021',
                        headers={'Authorization': f'Bearer {user_token}'})
    assert len(orders.json()['orders']) > 1
    # проверяем оба фильтра, в диапазоне которых не существует заказов
    orders = client.get('/internal/v1/orders/?page=1&per_page=10&date_from=21'
                        '.01.2020&date_to=26.01.2020',
                        headers={'Authorization': f'Bearer {user_token}'})
    assert len(orders.json()['orders']) == 0


def test_update_order(user_token):
    """Тест обновления заказа."""
    data = {"status": "string", "address_id": 1,
            "card_id": 1}
    # пробуем обновить данные, если статус заказа не "Новый"
    # в бд есть заказ со статусом "Отменен"
    cancelled_order = client.put('/api/v1/orders/3',
                                         headers={'Authorization': f'Bearer {user_token}'},
                                         data=json.dumps(data))
    assert cancelled_order.status_code == status.HTTP_400_BAD_REQUEST
    assert cancelled_order.json()['detail'][0]['msg'] == _('cannot_change_error')
    # пробуем обновить данные, если статус не "Отменен"
    incorrect_updated_order = client.put('/api/v1/orders/1',
                                         headers={'Authorization': f'Bearer {user_token}'},
                                         data=json.dumps(data))
    # проверяем ответ сервера
    assert incorrect_updated_order.status_code == status.HTTP_400_BAD_REQUEST
    assert incorrect_updated_order.json()['detail'][0]['msg'] == _('cannot_change_error')
    # указываем правильный статус
    correct_data = {"status": OrderStatuses.CANCELED.value, "address_id": 4,
                    "card_id": 1}
    correct_update_order = client.put('/api/v1/orders/1',
                                      headers={'Authorization': f'Bearer {user_token}'},
                                      data=json.dumps(correct_data))
    # проверяем обновленные данные
    assert correct_update_order.status_code == status.HTTP_200_OK
    # создаем новый адрес и карту, пробуем обновить данные
    address, card, shop = default_data(user_token)
    correct_data.update(address_id=address.json()['id'],
                                   card_id=card.json()['id'])
    new_update = client.put('/api/v1/orders/1',
                                      headers={'Authorization': f'Bearer {user_token}'},
                                      data=json.dumps(correct_data))
    assert new_update.status_code == status.HTTP_200_OK
    # пробуем обновить с несуществующим адресом и картой
    correct_data.update(address_id=10, card_id=10)
    incorrect_update = client.put('/api/v1/orders/1',
                                  headers={'Authorization': f'Bearer {user_token}'},
                                  data=json.dumps(correct_data))
    assert incorrect_update.status_code == status.HTTP_404_NOT_FOUND
    assert incorrect_update.json()['error'] == _('address_not_found')
