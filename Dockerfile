FROM python:3.8-slim

RUN mkdir /app
WORKDIR /app
ADD Pipfile /app/Pipfile
ADD Pipfile.lock /app/Pipfile.lock

RUN python -m pip install pipenv && pipenv install --dev --system

ADD . /app

CMD bash /app/start.sh
