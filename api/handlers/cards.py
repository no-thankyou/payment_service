"""Обработчики запросов для карт."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from api.handlers.common import get_user
from common import schemas
from common.database import DataBase, get_db
from common.models import Card, User

router = APIRouter()
internal_router = APIRouter()


@router.get('/', tags=['cards'], summary='Получение списка карт',
            response_model=List[schemas.Card])
def get_cards(user: User = Depends(get_user)):  # noqa: B008
    """
    Получение списка карт пользователя.

    Первой возвращается карта по умолчанию у пользователя.
    :param user: связь с пользователем
    :return:
    """
    cards = []
    for card in user.cards:
        card.append(schemas.Card.from_orm(card).dict())
    cards = sorted(cards, key=lambda el: not el['is_default'])

    return JSONResponse(cards, status_code=status.HTTP_200_OK)


@router.post('/', tags=['cards'], summary='Создание карты',
             response_model=List[schemas.Card])
def create_card(card_data: schemas.CardCreate,
                user: User = Depends(get_user),  # noqa: B008
                db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Создание карты.

    TODO: исследовать подключение банка.
    :param card_data: данные для валидации созданной карты
    :param db: связь с БД
    :param user: связь с пользователем
    :return:
    """
    card = Card(**card_data.dict(), user=user)
    db.add(card)
    db.save()
    card = schemas.Card.from_orm(card)
    return JSONResponse(card.dict(), status_code=status.HTTP_200_OK)


@internal_router.put('/{card_id}', tags=['cards'], summary='Обновление карты',
                     response_model=schemas.CardUpdate)
def update_card(card_id, data: schemas.CardCreate,
                user: User = Depends(get_user),  # noqa: B008
                db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Обновление карты пользователя.

    :param db: связь с БД
    :param data: данные модели
    :param user: связь с пользователем
    :param card_id: идентификатор карты для обновления
    :return:
    """
    card = user.get_card(card_id)
    card.update(data)
    db.save()
    db.refresh(card)
    return JSONResponse(schemas.Card.from_orm(card).dict(),
                        status_code=status.HTTP_200_OK)


@internal_router.delete('/{card_id}', tags=['cards'],
                        summary='Удаление карты')
def delete_card(card_id: int, user: User = Depends(get_user),  # noqa: B008
                db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Удаление карты.

    Удаление карты скрывает ее из списка доступных, но оставляет отображение
    в старых заказах.
    :param card_id: идентификатор карты для обновления
    :param db: связь с БД
    :param user: связь с пользователем
    :return:
    """
    card = user.get_card(card_id)
    db.delete(Card, card)
    return JSONResponse({}, status_code=status.HTTP_200_OK)
