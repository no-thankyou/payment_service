"""Вспомогательные функции для разлчных обработчиков."""
from fastapi import Depends
from fastapi_jwt_auth import AuthJWT

from common.database import get_db
from common.models import User


def get_user(jwt_service: AuthJWT = Depends(),  # noqa: B008
             db=Depends(get_db)):  # noqa: B008
    """Метод получения текущего пользователя."""
    jwt_service.jwt_required()
    user_id = jwt_service.get_jwt_subject()
    user, created = db.get_or_create(User, id=user_id)
    return user
