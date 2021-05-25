#!/usr/bin/env bash

./wait-for-it.sh $POSTGRES_DB:5432
PYTHONPATH=. alembic upgrade head
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000 --reload-dir api/ --reload-dir common/ --reload-dir worker/
