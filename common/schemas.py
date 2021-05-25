"""Схемы вылидации моделей проекта."""
import re
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, validator, UUID4
from pydantic.schema import date

from common.models import OrderStatuses
from common.text import get_text as _


class UserCreate(BaseModel):
    """Валидация для создания объекта User."""

    phone: str


class User(UserCreate):
    """Класс работы с моделью Пользователя из БД."""

    id: Optional[UUID4] = None  # noqa: A003
    name: Optional[str]
    lastname: Optional[str]
    birthday: Optional[date]
    email: Optional[EmailStr]

    class Config:
        """Настройки валидации."""

        orm_mode = True
        json_encoders = {date: lambda v: v.strftime('%Y-%m-%d')}


class UpdateUser(BaseModel):
    """Данные для обновления пользователя в профиле."""

    name: Optional[str]
    lastname: Optional[str]
    birthday: Optional[date]
    email: Optional[EmailStr]


class AddressCreate(BaseModel):
    """Валидация для создания адреса."""

    city: str = Field(None, title='Город')
    address: str = Field(None, title='Адрес')
    floor: str = Field(None, title='Этаж')
    apartment: str = Field(None, title='Квартира')
    is_default: bool = False
    comment: str = Field(None, title='Комментарий к адресу')


class AddressUpdate(BaseModel):
    """Валидация пришедших данных при обновлении адреса."""

    city: Optional[str]
    address: Optional[str]
    floor: Optional[str]
    apartment: Optional[str]
    is_default: Optional[bool]
    comment: Optional[str]

    @staticmethod
    @validator('city', 'address', 'floor',
               'apartment', 'is_default', 'comment')
    def prevent_none(cls, v):
        """Пустые поля игнорим, но None недопустим."""
        assert v is not None, _('none_field_error')  # noqa: S101
        return v


class Address(AddressCreate):
    """Класс для работы с моделью Адреса из БД."""

    id: int  # noqa: A003

    class Config:
        """Настройки валидации."""

        orm_mode = True


class ShopCreate(BaseModel):
    """Валидация данных для создания Магазина."""

    name: str
    site_url: str
    api_endpoint: str
    is_active: bool


class Shop(ShopCreate):
    """Модель для работы с Магазином из БД."""

    id: int  # noqa: A003

    class Config:
        """Настройки валидации."""

        orm_mode = True


class ShopUpdate(BaseModel):
    """Валидация пришедших данных при обновлении магазина."""

    name: str
    site_url: str
    api_endpoint: str
    is_active: bool

    @staticmethod
    @validator('name', 'site_url', 'api_endpoint', 'is_active')
    def prevent_none(cls, v):
        """Пустые поля игнорим, но None недопустим."""
        assert v is not None, _('none_field_error')  # noqa: S101


class CardCreate(BaseModel):
    """Валидация создания Карты."""

    number: str
    is_default: bool = False

    @validator('number')
    def get_number_length(cls, v):  # noqa: N805
        """Валидация по длине номера карты."""
        if not re.match(r'^\d{12,19}$', v):
            raise ValueError(_('card_length_error'))
        return v


class Card(CardCreate):
    """Модель для работы с Картой из БД."""

    id: int  # noqa: A003

    class Config:
        """Настройка валидации."""

        orm_mode = True


class CardUpdate(BaseModel):
    """Валидация пришедших данных при обновлении рты."""

    number: Optional[int]
    user: Optional[int]
    is_default: Optional[bool]

    @staticmethod
    @validator('number', 'user', 'is_default')
    def prevent_none(cls, v):
        """Пустые поля игнорим, но None недопустим."""
        assert v is not None, _('none_field_error')  # noqa: S101
        return v


class ItemCreate(BaseModel):
    """Валидация создания товара для заказа."""

    article: str
    name: str
    price: int
    shop_id: int
    quantity: int
    total_price: int
    discount: int


class Item(ItemCreate):
    """Модель для работы с Товарами из БД."""

    id: int  # noqa: A003

    class Config:
        """Настройки валидации."""

        orm_mode = True


class OrderCreate(BaseModel):
    """Валидация для создания заказа."""

    number: int
    order_sum: int
    total_price: int
    delivery_price: int
    discount: int
    items: List[ItemCreate]
    shop_id: int


class Order(OrderCreate):
    """Модель для работы с заказом из БД."""

    id: int  # noqa: A003
    shop: Shop
    items: Optional[List[Item]]
    date: date

    class Config:
        """Настройки модели."""

        orm_mode = True
        json_encoders = {date: lambda v: v.strftime('%m %d %Y %H:%M:%S')}


class OrderUpdate(BaseModel):
    """Валидация пришедших данных при обновлении заказа."""

    status: str = None
    address_id: int = None
    card_id: int = None

    @validator('status')
    def status_match(cls, v):  # noqa: N805
        """Валидация по статусу."""
        if v is not None and v != OrderStatuses.CANCELED.value:
            raise ValueError(_('cannot_change_error'))
        return v


class OrderOut(BaseModel):
    """Поля для ответа на запрос создания заказа."""

    order_id: int


class ErrorResponse(BaseModel):
    """Поля для ответа на запрос создания заказа 400 ошибкой."""

    order_id: int
    error: str


class BasePhoneValidator(BaseModel):
    """Базовый класс для общей валидации номера в разных схемах."""

    phone: str

    @validator('phone', pre=True)
    def phone_format(cls, v):  # noqa: N805
        """Валидация формата номера."""
        assert v[0] == '+', _('phone_field_error')  # noqa: S101
        assert len(v) == 12, _('phone_field_error')  # noqa: S101
        return v


class SendSmsForm(BasePhoneValidator):
    """Тело запроса на отправку смс."""


class LoginForm(BasePhoneValidator):
    """Тело запроса на авторизацию."""

    code: str


class DeactivateSessionBody(BaseModel):
    """Валидация id refresh токена."""

    refresh_id: str
