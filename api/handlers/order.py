"""Обработчики запросов для заказов."""
import json
from datetime import datetime
from math import ceil
from typing import List

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from api.handlers.common import get_user
from common import schemas
from common.database import DataBase, get_db
from common.exceptions import ModelException, NotFoundException
from common.models import Order, User, OrderStatuses
from worker import tasks

router = APIRouter()
internal_router = APIRouter()


@router.post('/create', tags=['orders'], status_code=status.HTTP_201_CREATED,
             summary='Создание нового заказа',
             responses={status.HTTP_400_BAD_REQUEST:
             {'model': schemas.ErrorResponse},
             status.HTTP_201_CREATED:
             {'model': schemas.OrderOut}})
def create_order(order_data: schemas.OrderCreate,  # noqa: B008
                 user: User = Depends(get_user),  # noqa: B008
                 db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Создание заказа.

    Создание заказа в статусе "Новый". Спустя 5 минут перейдет в статус
    "Создан" и пойдет в работу.
    :param db:
    :param user:
    :param order_data: данные для создания заказа
    :return:
    """
    order_data_dict = order_data.dict()
    order_data_dict['user_id'] = user.id.hex
    order, created = db.get_or_create(Order, number=order_data_dict['number'])
    order_data_dict['id'] = order.id
    tasks.create_order.delay(order_data_dict)
    response = {'order_id': order.id}
    try:
        user.get_default_address()
        user.get_default_card()
    except NotFoundException as e:
        response['error'] = str(e)
        return JSONResponse(response, status_code=status.HTTP_400_BAD_REQUEST)
    return JSONResponse(response, status_code=status.HTTP_201_CREATED)


@router.get('/{order_id}', tags=['orders'],
            summary='Получение детальной информации о заказе',
            response_model=schemas.Order)
def get_order(order_id: int, user=Depends(get_user)):  # noqa: B008
    """
    Получение детальной информации о заказе.

    :param user:
    :param order_id: идентификатор заказа в нашей системе
    :return:
    """
    order = user.get_order(order_id)
    return JSONResponse(json.loads(schemas.Order.from_orm(order).json()),
                        status_code=status.HTTP_200_OK)


@router.put('/{order_id}', tags=['orders'],
            summary='Обновление информации о заказе',
            response_model=List[schemas.Order])
def update_order(order_id: int, data: schemas.OrderUpdate,
                 user: User = Depends(get_user)):  # noqa: B008
    """
    Обновление заказа.

    После перехода заказа в статус "Создан" нельзя изменить карту оплаты и
    адрес доставки. Можно поменять только информацию о товарах, без изменения
    цены.
    :param order_id: идентификатор в нашей системе
    :param data: данные модели
    :return:
    """
    order = Order.get(order_id)
    if not order.status == OrderStatuses.NEW:
        raise ModelException('Изменения невозможны', 400)
    user.get_address(data.dict()['address_id'])
    user.get_card(data.dict()['card_id'])
    tasks.update_order.delay(order_id, data.dict())
    return JSONResponse({}, status_code=status.HTTP_200_OK)


@internal_router.get('/', tags=['orders'], summary='Получение списка заказов',
                     response_model=List[schemas.Order])
def get_orders(page: int = 1, per_page: int = 10,
               date_from: str = None, date_to: str = None,
               user=Depends(get_user)):  # noqa: B008
    """
    Получить список заказов пользователя.

    :return:
    """
    orders = user.orders
    if date_from:
        date_from = datetime.strptime(date_from, '%d.%m.%Y')
        date_from = date_from.replace(hour=0, minute=0, second=0)
        orders = orders.filter(Order.date >= date_from)
    if date_to:
        date_to = datetime.strptime(date_to, '%d.%m.%Y')
        date_to = date_to.replace(hour=23, minute=59, second=59)
        orders = orders.filter(Order.date <= date_to)
    all_count = orders.count()
    pages = ceil(all_count / per_page)
    orders = orders.offset((page - 1) * per_page).limit(per_page)
    response = {'has_orders': user.orders.count() > 0, 'count': all_count,
                'page': page, 'pages': pages, 'orders': []}
    for order in orders:
        order_data = schemas.Order.from_orm(order)
        response['orders'].append(json.loads(order_data.json()))
    return JSONResponse(response, status_code=status.HTTP_200_OK)
