"""Точка входа для запуска API."""
import sqltap
from fastapi import Depends, FastAPI
from fastapi_jwt_auth import AuthJWT
from starlette.requests import Request

from api.handlers import (address, auth, cards, order, shop, user,
                          session_process)
from common.services import TokensDenyList

tags_metadata = [{'name': 'orders',
                  'description': 'Запросы для работы с заказами'},
                 {'name': 'addresses',
                  'description': 'Запросы для работы с адресами'},
                 {'name': 'cards',
                  'description': 'Запросы для работы с картами'},
                 {'name': 'profile',
                  'description': 'Запросы для работы с профилем'},
                 {'name': 'auth', 'description': 'Запросы для авторизации'}]

app = FastAPI(openapi_tags=tags_metadata, debug=True)

app.include_router(order.router, prefix='/api/v1/orders',
                   tags=['orders'])
app.include_router(order.internal_router,
                   prefix='/internal/v1/orders', tags=['orders'])

app.include_router(address.router, prefix='/api/v1/addresses',
                   tags=['addresses'])
app.include_router(address.internal_router,
                   prefix='/internal/v1/addresses', tags=['addresses'])

app.include_router(cards.router, prefix='/api/v1/cards',
                   tags=['cards'])
app.include_router(cards.internal_router,
                   prefix='/internal/v1/cards', tags=['cards'])

app.include_router(shop.internal_router,
                   prefix='/internal/v1/shops', tags=['shops'],
                   dependencies=[Depends(shop.is_admin)])  # noqa: B008

app.include_router(user.internal_router,
                   prefix='/internal/v1/profile', tags=['profile'])

app.include_router(auth.router, prefix='/api/v1/auth', tags=['auth'])

app.include_router(session_process.internal_router,
                   prefix='/internal/v1/sessions', tags=['sessions'])


# включать когда нужно проверить запросы, пока руками
# @app.middleware('http')
async def add_sql_tap(request: Request, call_next):
    """Функция для профилирования запросов к бд."""
    profiler = sqltap.start()
    response = await call_next(request)
    sqltap.report(profiler.collect(),
                  f'reports/{request.url.path.replace("/", "-")}.html')
    return response


@AuthJWT.token_in_denylist_loader
def check_if_token_in_denylist(decrypted_token):
    """Функция для проверки отозван ли токен."""
    return TokensDenyList().check_token(decrypted_token)


from api.handlers.exceptions import *  # noqa: F401, F403, E402
