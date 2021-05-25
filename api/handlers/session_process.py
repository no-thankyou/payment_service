"""Обработчики запросов для сессий."""
import datetime

from fastapi import APIRouter, Depends
from starlette import status
from starlette.responses import JSONResponse

from api.handlers.common import get_user
from common.exceptions import ModelException
from common.schemas import DeactivateSessionBody
from common.services import TokensDenyList
from common.database import DataBase, get_db
from common.models import ActiveTokens, User
from common.text import get_text as _

internal_router = APIRouter()


@internal_router.get('/', tags=['sessions'],
                     summary='Получение списка активных сессий')
def get_active_sessions(db: DataBase = Depends(get_db)):  # noqa: B008
    """Получение списка активных сессий."""
    timestamp = int(datetime.datetime.now().timestamp())
    active_sessions = []
    for session in db.get_all_objects(ActiveTokens):
        data = {'jti': session.refresh_id}
        # словарь для метода класса TokenDenyList
        if ((session.refresh_expired_date > timestamp)
                and not TokensDenyList().check_token(data)):
            active_sessions.append({
                'refresh_id': session.refresh_id,
                'user_agent': session.user_agent, 'region': session.region,
                'online': session.access_expired_date > timestamp})
    return JSONResponse(active_sessions, status_code=status.HTTP_200_OK)


@internal_router.post('/deactivate', tags=['sessions'],
                      summary='Прекращение сессии')
def deactivate_session(data: DeactivateSessionBody,  # noqa: B008
                       user: User = Depends(get_user),  # noqa: B008
                       db: DataBase = Depends(get_db)):  # noqa: B008
    """Прекращение сессии."""
    active_session = (db.filter(ActiveTokens,
                                ActiveTokens.refresh_id == data.refresh_id,
                                ActiveTokens.user_id == user.id.hex)
                      .one_or_none())
    if not active_session:
        raise ModelException(_('session_not_found'), 404)

    TokensDenyList().add_token(active_session.access_id)
    TokensDenyList().add_token(active_session.refresh_id)
    return JSONResponse({}, status_code=status.HTTP_200_OK)
