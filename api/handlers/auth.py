"""Обработчики запросов для авторизации."""
import secrets

from fastapi import APIRouter, Depends, status, Header, Request
from fastapi.responses import JSONResponse, Response
from fastapi_jwt_auth import AuthJWT

from common.database import get_db
from common.models import User, ActiveTokens
from common.schemas import LoginForm, SendSmsForm
from common.services import PhoneAttempts, TokensDenyList, user_agent_parser
from common.settings import settings


router = APIRouter()


@router.post('/login', tags=['auth'], summary='Авторизации')
def login(data: LoginForm, request: Request,
          jwt_service: AuthJWT = Depends(),  # noqa: B008
          db=Depends(get_db), user_agent: str = Header(None)):  # noqa: B008
    """
    Авторизация пользователя.

    :return:
    """
    phone_service = PhoneAttempts(data.phone)
    phone_service.check_code(data.code)

    user, created = db.get_or_create(User, phone=data.phone)

    access_token = jwt_service.create_access_token(subject=user.id.hex)
    refresh_token = jwt_service.create_refresh_token(subject=user.id.hex)

    create_active_session(access_token, refresh_token, user, user_agent,
                          request, jwt_service, db)
    agent, platform, _ = user_agent_parser(user_agent, request)
    res = {'access_token': access_token, 'agent': agent, 'platform': platform}
    if settings.debug:
        res['user_id'] = user.id.hex
    response = JSONResponse(res, status_code=status.HTTP_200_OK)
    jwt_service.set_access_cookies(access_token, response,
                                   settings.auth_access_token_lifetime)
    jwt_service.set_refresh_cookies(refresh_token, response,
                                    settings.auth_refresh_token_lifetime)
    return response


@router.post('/refresh', tags=['auth'], summary='Обновление JWT токена')
def refresh(request: Request, jwt_service: AuthJWT = Depends(),  # noqa: B008
            db=Depends(get_db), user_agent: str = Header(None)):  # noqa: B008
    """
    Обновляет jwt токен пользователя.

    Создает новую пару access и refresh токенов.
    :return:
    """
    jwt_service.jwt_refresh_token_required()

    phone = jwt_service.get_jwt_subject()
    user, created = db.get_or_create(User, phone=phone)

    TokensDenyList().add_token(jwt_service.get_raw_jwt()['jti'])

    access_token = jwt_service.create_access_token(subject=user.id.hex)
    refresh_token = jwt_service.create_refresh_token(subject=user.id.hex)

    create_active_session(access_token, refresh_token, user, user_agent,
                          request, jwt_service, db)

    response = JSONResponse({'access_token': access_token},
                            status_code=status.HTTP_200_OK)
    jwt_service.set_access_cookies(access_token, response)
    jwt_service.set_refresh_cookies(refresh_token, response)
    return response


@router.post('/logout', tags=['auth'], summary='Выход')
def logout(jwt_service: AuthJWT = Depends()):  # noqa: B008
    """
    Выход для пользователя.

    :return:
    """
    jwt_service.jwt_required()

    res = JSONResponse({}, status_code=status.HTTP_200_OK)
    __remove_cookie(jwt_service, res, jwt_service._access_cookie_key,
                    jwt_service._access_cookie_path)

    __remove_cookie(jwt_service, res, jwt_service._refresh_cookie_key,
                    jwt_service._refresh_cookie_path)

    TokensDenyList().add_token(jwt_service.get_raw_jwt()['jti'])

    return res


@router.post('/sms-send', tags=['auth'], summary='Отправка смс для входа')
def send_sms(data: SendSmsForm):
    """Запрос на отправку СМС."""
    phone_service = PhoneAttempts(data.phone)
    phone_service.can_send_sms()

    code = 111111
    if not settings.debug:
        # генерация кода в диапазоне 100000 - 999999
        code = 100000 + secrets.randbelow(899999)

    phone_service.set_phone_code(str(code))
    # TODO добавить отправку кода
    return JSONResponse({}, status_code=status.HTTP_200_OK)


def __remove_cookie(jwt_service: AuthJWT, response: Response, cookie_key: str,
                    cookie_path: str, http_only: bool = True):
    """
    Вспомогательная функция нормального удаления куков из ответа.

    Проблема в том, что Response.delete_cookie неправильно выставляет samesite,
    httponly и прочие флаги в set-cookies.

    :param jwt_service: сервис от библиотеки JWT, оттуда нужны настройки
    :param response: объект ответа, где нужно удалить куки
    :param cookie_key: ключ куков
    :param cookie_path: путь куков
    :param http_only: httpOnly флаг куков
    :return:
    """
    response.set_cookie(cookie_key, '', max_age=0, path=cookie_path,
                        domain=jwt_service._cookie_domain,
                        secure=jwt_service._cookie_secure,
                        httponly=http_only,
                        samesite=jwt_service._cookie_samesite)
    return response


def create_active_session(access_token: str, refresh_token: str, user: User,
                          user_agent: str, request: Request,
                          jwt_service: AuthJWT,
                          db=Depends(get_db)):  # noqa: B008
    """
    Вспомогательная функция для создания объектов активной сессии.

    :param access_token: access токен
    :param refresh_token: refresh токен
    :param user: пользователь сессии
    :param user_agent: устройство входа в сессию
    :param request: объект запроса
    :param jwt_service: сервис от библиотеки JWT
    :param db: связь с БД
    :return: возвращает объект бд активной сессии
    """
    agent, platform, location = user_agent_parser(user_agent, request)
    jti_access = jwt_service.get_raw_jwt(access_token)['jti']
    access_expired_date = jwt_service.get_raw_jwt(access_token)['exp']
    jti_refresh = jwt_service.get_raw_jwt(refresh_token)['jti']
    refresh_expired_date = jwt_service.get_raw_jwt(access_token)['exp']
    token_data = {'access_id': jti_access,
                  'access_expired_date': access_expired_date,
                  'refresh_id': jti_refresh,
                  'refresh_expired_date': refresh_expired_date,
                  'user_agent': user_agent, 'user_id': user.id.hex,
                  'region': location, 'agent': agent, 'platform': platform}
    active_token = ActiveTokens(**token_data)
    db.add(active_token)
    db.save()
