"""Таски проекта."""
from datetime import datetime

from celery import Celery

from common.database import DataBase
from common.models import Order, OrderStatuses, Item, User
from common.settings import settings

REDIS_URL = f'redis://{settings.redis_host}:{settings.redis_port}/0'
app = Celery('tasks', broker=REDIS_URL, backend=REDIS_URL)


@app.task
def add(x, y):
    """Пример."""
    return x + y


@app.task
def get_users_list(skip, limit):
    """Пример работы с бд из очереди."""
    return []


@app.task
def check_card(user_id, card_id):
    """Валидация карты при добавлении."""
    pass


@app.task
def hold_money(order_id, user_id, card_id):
    """
    Замораживает средства на карте для последующей оплаты.

    При невозможности заморозить средства должна отправляться ошибка юзеру.
    """
    pass


@app.task
def free_money(order_id, user_id, card_id):
    """Снять холд с карты."""
    pass


@app.task
def withdrawal_money(order_id, user_id, card_id):
    """Снять средства в счет оплаты заказа."""
    pass


@app.task
def create_order(data):
    """
    Задача создания заказа.

    :param data: валидные данные о заказе

    Создается заказ и отложенная задача на обработку заказа, для оплаты и т.д.
    """
    db = DataBase()
    item_data = data['items']  # список из словарей с товарами
    del data['items']
    user = User.get(data['user_id'])
    data['address_id'] = user.get_default_address().id
    data['card_id'] = user.get_default_card().id
    data['date'] = datetime.now()
    order = Order.get(data['id'])
    del data['id']
    for key, val in data.items():
        setattr(order, key, val)

    for item in item_data:
        item.update(order_id=order.id,
                    shop_id=order.shop_id)
        db.get_or_create(Item, **item)
    process_order.apply_async((order.id,), countdown=settings.process_timeout)
    # TODO переделать под работу с фронтом


@app.task
def update_order(order_id, data):
    """Задача обновление заказа."""
    db = DataBase()
    order = Order.get(order_id)
    order.address_id = data['address_id']
    order.card_id = data['card_id']
    db.save()
    # TODO поправить работу с БД


@app.task
def process_order(order_id):
    """Задача оплаты заказа и передачи в магазин информации."""
    order = Order.get(order_id)
    if order.status == OrderStatuses.NEW.value:
        # todo тут процесс оплаты с ожиданием
        order.status = OrderStatuses.CREATED.value
        DataBase().save()


@app.task
def send_order(order_id):
    """Задача для отправки данных об оплаченном/отмененном заказе в магазин."""
    pass


@app.task
def cancel_order(order_id):
    """
    Задача отмены заказа.

    Переводит статус заказа в шлюзе и в магазине, снимает холд с карты.
    """
    order = Order.get(order_id)
    if order.status == OrderStatuses.NEW.value:
        order.status = OrderStatuses.CANCELED.value
        DataBase().save()
