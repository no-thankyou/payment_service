"""Обработчики ошибок приложения."""
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi_jwt_auth.exceptions import AuthJWTException
from starlette.responses import JSONResponse

from api.app import app
from common.exceptions import ModelException
from common.services import PhoneException
from common.text import get_text as _


@app.exception_handler(AuthJWTException)
def auth_jwt_exception_handler(request: Request, exc: AuthJWTException):
    """Обработчик ошибок JWT авторизации."""
    error = {'error': _('auth_required')}
    if app.debug:
        error['detail'] = exc.message
    return JSONResponse(error, status_code=status.HTTP_401_UNAUTHORIZED)


@app.exception_handler(PhoneException)
def phone_exception_handler(request: Request, exc: PhoneException):
    """Обработчик ошибок авторизации."""
    return JSONResponse({'error': str(exc)},
                        status_code=status.HTTP_400_BAD_REQUEST)


@app.exception_handler(ModelException)
def exception_handler(request: Request, exc: ModelException):
    """Обработчик ошибок работы с адресами, картами, магазинами доставки."""
    return JSONResponse({'error': exc.message}, status_code=exc.status)


@app.exception_handler(RequestValidationError)
def validation_handler(request: Request, exc: RequestValidationError):
    """Обработчик ошибок валидации входных данных в запросах."""
    return JSONResponse({'detail': exc.errors()}, status_code=400)
