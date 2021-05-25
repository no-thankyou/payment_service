"""Обработчики запросов для магазинов."""
from __future__ import annotations

from typing import List
import secrets
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from api.handlers.common import get_user
from common import schemas
from common.database import DataBase, get_db
from common.exceptions import NotFoundException
from common.models import Shop, User
from common.text import get_text as _

internal_router = APIRouter()


def is_admin(user: User = Depends(get_user)):  # noqa: B008
    """
    Проверка прав юзера.

    Пока такое решение, до изменения архитектуры запросов.
    """
    if not user.is_admin:
        raise NotFoundException(_('not_found_error'),
                                status_code=status.HTTP_404_NOT_FOUND)
    return user


@internal_router.get('/', tags=['shops'], summary='Получение списка магазинов',
                     response_model=List[schemas.Shop])
def get_shops(db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Получение списка магазинов.

    :param db: связь с БД
    :return:
    """
    shops = []
    for shop in db.get_all_objects(Shop):
        shops.append(schemas.Shop.from_orm(shop).dict())
    shops = sorted(shops, key=lambda el: not el['is_active'])
    return JSONResponse(shops, status_code=status.HTTP_200_OK)


@internal_router.get('/{shop_id}', tags=['shops'],
                     summary='Получение отдельного магазина',
                     response_model=schemas.Shop)
def get_shop(shop_id, db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Получение детальной инфромации о магазине.

    :param shop_id: идентификатор магазина
    :param db: связь с БД
    :return:
    """
    return JSONResponse(schemas.Shop.from_orm(Shop.get(shop_id)).dict(),
                        status_code=status.HTTP_200_OK)


@internal_router.post('/', tags=['shops'], summary='Создание магазина',
                      response_model=schemas.Shop)
def create_shop(shop_data: schemas.ShopCreate,  # noqa: B008
                db: DataBase = Depends(get_db),  # noqa: B008
                user: User = Depends(get_user)):  # noqa: B008
    """
    Добавление нового магазина.

    :param shop_data: данные для валидации созданного магазина
    :param db: связь с БД
    :return:
    """
    extra_info = {'api_key': secrets.token_hex(), 'user_id': user.id.hex}
    shop_data_dict = shop_data.dict()
    shop_data_dict.update(extra_info)
    shop, created = db.get_or_create(Shop, **shop_data_dict)
    shop = schemas.Shop.from_orm(shop)
    return JSONResponse(shop.dict(), status_code=status.HTTP_200_OK)


@internal_router.put('/{shop_id}', tags=['shops'],
                     summary='Обновление магазина',
                     response_model=schemas.Shop)
def update_shop(shop_id, data: schemas.ShopUpdate,  # noqa: B008
                db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Обновление магазина.

    :param db: связь с БД
    :param data: данные модели
    :param shop_id: идентификатор магазина для обновления
    :return:
    """
    shop = Shop.get(shop_id)
    shop.update(data)
    db.save()
    db.refresh(shop)
    return JSONResponse(schemas.Shop.from_orm(shop).dict(),
                        status_code=status.HTTP_200_OK)


@internal_router.delete('/{shop_id}', tags=['shops'],
                        summary='Удаление магазина')
def delete_shop(shop_id, db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Удаление магаизна.

    :param db: связь с БД
    :param shop_id: идентификатор магазина
    :return:
    """
    shop = Shop.get(shop_id)
    db.delete(Shop, shop)
    return JSONResponse({}, status_code=status.HTTP_200_OK)
