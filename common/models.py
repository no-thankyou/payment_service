"""Описание моделей БД."""
from __future__ import annotations

import enum
from uuid import uuid4
import pydantic
from sqlalchemy import (Boolean, Column, Date, DateTime, Enum, ForeignKey,
                        Integer, String)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from common.database import Base, DataBase
from common.exceptions import (AddressException, CardException,
                               ModelException, NotFoundException)
from common.text import get_text as _


class BaseModel(Base):
    """Общая логика объектов БД."""

    __abstract__ = True

    def update(self, info: pydantic.BaseModel):
        """
        Обновление модели.

        Не сохраняет изменения в БД, только меняет атрибуты у объекта.
        :param info: данные для заполнения
        :return:
        """
        for key, val in info.dict().items():
            if val is not None:
                setattr(self, key, val)

    @classmethod
    def get(cls, idx):
        """Получение объекта из бд по идентификатору."""
        instance = DataBase().get_by_id(cls, id=idx)
        if not instance:
            raise NotFoundException(_('object_not_found'))
        return instance


class User(BaseModel):
    """Класс Пользователя платформы."""

    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True,   # noqa: A003
                unique=True, index=True, default=uuid4)
    phone = Column(String, unique=True, index=True)
    name = Column(String, default='')
    lastname = Column(String, default='')
    birthday = Column(Date)
    email = Column(String, default=None)
    is_admin = Column(Boolean, default=False)
    cards = relationship('Card', back_populates='user', lazy='dynamic')
    addresses = relationship('Address', back_populates='user', lazy='dynamic')
    orders = relationship('Order', back_populates='user', lazy='dynamic')
    auths = relationship('AuthLog', back_populates='user', lazy='dynamic')

    def get_address(self, address_id: int):
        """Поиск адреса среди привязанных к пользователю."""
        address = self.addresses.filter(Address.id == address_id).one_or_none()
        if not address:
            raise AddressException(_('address_not_found'), 404)
        return address

    def get_card(self, card_id: int):
        """Поиск карты среди привязанных к пользователю."""
        card = self.cards.filter(Card.id == card_id).one_or_none()
        if not card:
            raise CardException(_('card_not_found'), 404)
        return card

    def get_default_address(self):
        """Получение дефолтного адреса, ошибка в противном случае."""
        default_address = (self.addresses
                           .filter(Address.is_default == True)  # noqa: E712
                           .one_or_none())
        if default_address:
            return default_address
        raise NotFoundException(_('default_address_not_found'))

    def get_default_card(self):
        """Получение дефолтноой карты, ошибка в противном случае."""
        default_card = (self.cards
                        .filter(Card.is_default == True)  # noqa: E712
                        .one_or_none())
        if default_card:
            return default_card
        raise NotFoundException(_('default_card_not_found'))

    def get_order(self, order_id: int):
        """Метод получения заказа пользователя."""
        order = self.orders.filter(Order.id == order_id).one_or_none()
        if not order:
            raise ModelException(_('order_not_found'), 404)
        return order


class Card(BaseModel):
    """Класс Карты пользователя."""

    __tablename__ = 'cards'

    id = Column(Integer, primary_key=True, index=True)  # noqa: A003
    number = Column(String)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    user = relationship('User', back_populates='cards')
    is_default = Column(Boolean)
    orders = relationship('Order', back_populates='card')

    # TODO добавлять поля


class Address(BaseModel):
    """Класс Адреса доставки пользователя."""

    __tablename__ = 'addresses'

    id = Column(Integer, primary_key=True, index=True)  # noqa: A003
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    user = relationship('User', back_populates='addresses')
    city = Column(String)
    address = Column(String)
    floor = Column(String)
    apartment = Column(String)
    is_default = Column(Boolean)
    comment = Column(String)
    orders = relationship('Order', back_populates='address')
    # phone TODO возможно стоит указывать номер тут


class Shop(BaseModel):
    """Класс информации о Магазине."""

    __tablename__ = 'shops'

    id = Column(Integer, primary_key=True, index=True)  # noqa: A003
    name = Column(String)
    # logo TODO реализовать самим или найти готовое решение под алхимию?
    site_url = Column(String)
    api_endpoint = Column(String)
    api_key = Column(String)
    user_id = Column(UUID(as_uuid=True))
    is_active = Column(Boolean, default=True)
    orders = relationship('Order', back_populates='shop')
    items = relationship('Item', back_populates='shop')
    auths = relationship('AuthLog', back_populates='shop')


class OrderStatuses(enum.Enum):
    """Константы для статусов заказа."""

    NEW = 'Новый'
    CREATED = 'Создан'
    HANDLING = 'В обработке'
    COMPLETED = 'Завершен'
    CANCELED = 'Отменен'


class Order(BaseModel):
    """Класс с информацией о Заказе пользователя."""

    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True, index=True)  # noqa: A003
    number = Column(Integer, index=True)
    status = Column(Enum(OrderStatuses, name='statuses'),
                    default=OrderStatuses.NEW)
    total_price = Column(Integer)
    order_sum = Column(Integer)
    delivery_price = Column(Integer)
    discount = Column(Integer)
    date = Column(DateTime)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    user = relationship('User', back_populates='orders')

    shop_id = Column(Integer, ForeignKey('shops.id'))
    shop = relationship('Shop', back_populates='orders')
    card = relationship('Card', back_populates='orders')
    card_id = Column(Integer, ForeignKey('cards.id'))
    address_id = Column(Integer, ForeignKey('addresses.id'))
    address = relationship('Address', back_populates='orders')

    items = relationship('Item', back_populates='order')


class Item(BaseModel):
    """Класс Купленного товара."""

    __tablename__ = 'items'

    id = Column(Integer, primary_key=True, index=True)  # noqa: A003
    article = Column(String, index=True)
    name = Column(String)
    price = Column(Integer)
    quantity = Column(Integer)
    total_price = Column(Integer)
    discount = Column(Integer)

    shop_id = Column(Integer, ForeignKey('shops.id'))
    shop = relationship('Shop', back_populates='items')

    order_id = Column(Integer, ForeignKey('orders.id'))
    order = relationship('Order', back_populates='items')


class AuthLog(BaseModel):
    """Класс информации об авторизации в Магазине."""

    __tablename__ = 'auth'

    id = Column(Integer, primary_key=True, index=True)  # noqa: A003

    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    user = relationship('User', back_populates='auths')

    shop_id = Column(Integer, ForeignKey('shops.id'))
    shop = relationship('Shop', back_populates='auths')


class ActiveTokens(BaseModel):
    """Класс для хранения активных сессий."""

    __tablename__ = 'active_tokens'

    id = Column(Integer, primary_key=True, index=True)  # noqa: A003
    access_id = Column(String)
    access_expired_date = Column(Integer)
    refresh_id = Column(String)
    refresh_expired_date = Column(Integer)
    user_agent = Column(String)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    region = Column(String)
    agent = Column(String)
    platform = Column(String)
