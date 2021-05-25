"""Обработчики запросов для адресов."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from api.handlers.common import get_user
from common import schemas
from common.database import DataBase, get_db
from common.models import Address, User

router = APIRouter()
internal_router = APIRouter()


def check_default_address(address, user: User):
    """Изменение адреса по умолчанию."""
    if address.is_default:
        # todo сделать bulk_update
        for addr in user.addresses:
            addr.is_default = False
        address.is_default = True


@router.get('/', tags=['addresses'], summary='Получение списка адресов',
            response_model=List[schemas.Address])
def get_addresses(user=Depends(get_user)):  # noqa: B008
    """
    Получение списка адресов с пользователем.

    Первым вернется дефолтный адрес пользователя, который необходимо
     использовать для заказа.
    """
    addresses = []
    for address in user.addresses:
        addresses.append(schemas.Address.from_orm(address).dict())
    addresses = sorted(addresses, key=lambda el: not el['is_default'])
    return JSONResponse(addresses, status_code=status.HTTP_200_OK)


@router.post('/', tags=['addresses'], summary='Создание адреса',
             response_model=schemas.Address)
def create_address(address_data: schemas.AddressCreate,
                   user: User = Depends(get_user),  # noqa: B008
                   db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Создание нового адреса доставки.

    :return:
    """
    address = Address(**address_data.dict(), user=user)
    check_default_address(address, user)
    db.add(address)
    db.save()
    address = schemas.Address.from_orm(address)
    return JSONResponse(address.dict(), status_code=status.HTTP_200_OK)


@internal_router.put('/{address_id}', tags=['addresses'],
                     summary='Обновление адреса',
                     response_model=schemas.Address)
def update_address(address_id, data: schemas.AddressUpdate,
                   user: User = Depends(get_user),  # noqa: B008
                   db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Обновление адреса доставки.

    :param db:
    :param data:
    :param user:
    :param address_id: идентификатор адреса для обновления
    :return:
    """
    address = user.get_address(address_id)
    address.update(data)
    check_default_address(address, user)
    db.save()
    db.refresh(address)
    return JSONResponse(schemas.Address.from_orm(address).dict(),
                        status_code=status.HTTP_200_OK)


@internal_router.delete('/{address_id}', tags=['addresses'],
                        summary='Удаление адреса')
def delete_address(address_id, user: User = Depends(get_user),  # noqa: B008
                   db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Удаление адреса.

    Удаление адреса скрывает его из списка доступных, но оставляет отображение
     в старых заказах.

    :param db:
    :param user:
    :param address_id: идентификатор адреса
    :return:
    """
    address = user.get_address(address_id)
    db.delete(Address, address)
    return JSONResponse({}, status_code=status.HTTP_200_OK)
