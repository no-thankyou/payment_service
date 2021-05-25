"""Обработчики запросов для профиля."""
import json

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from api.handlers.common import get_user
from common import schemas
from common.database import DataBase, get_db
from common.models import User

internal_router = APIRouter()


@internal_router.get('/', tags=['profile'], summary='Получение профиля',
                     response_model=schemas.User)
def get_profile(user=Depends(get_user)):  # noqa: B008
    """
    Получить профиль пользователя.

    :return:
    """
    # todo переделать ответ без перегона из json в dict и обратно
    return JSONResponse(json.loads(schemas.User.from_orm(user).json()),
                        status_code=status.HTTP_200_OK)


@internal_router.put('/', tags=['profile'], summary='Обновление профиля',
                     response_model=schemas.User)
def update_profile(data: schemas.UpdateUser,
                   user: User = Depends(get_user),  # noqa: B008
                   db: DataBase = Depends(get_db)):  # noqa: B008
    """
    Обновление профиля пользователя.

    Изменить номер на текущий момент нельзя.
    :return:
    """
    user.update(data)
    db.save()
    db.refresh(user)
    # todo переделать ответ без перегона из json в dict и обратно
    return JSONResponse(json.loads(schemas.User.from_orm(user).json()),
                        status_code=status.HTTP_200_OK)
