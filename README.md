# Бекенд MVP версии платежного шлюза
![Build Status](https://github.com/no-thankyou/payment_service/actions/workflows/github-actions.yml/badge.svg?branch=main)

### Запуск
```bash
$ cp .env.example .env
$ docker-compose build
$ docker-compose up
```

Бекенд будет доступен по адресу: http://localhost:8000
API документация: http://localhost:8000/docs

### Создание миграций
Работа с миграциями происходит внутри контейнера с api. Для применения миграций используются команды:
```bash
$ docker-compose run api bash
$ PYTHONPATH=. alembic upgrade head
```

Для содания новых миграций (без автогенерации):
```bash
$ docker-compose run api bash
$ PYTHONPATH=. alembic revision -m "описание миграции"
```
С автогенеацией:
Для содания новых миграций:
```bash
$ docker-compose run api bash
$ PYTHONPATH=. alembic revision --autogenerate
```
