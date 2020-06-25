FROM python:3.8-alpine

RUN apk add gcc musl-dev

WORKDIR /app

RUN pip install pipenv

COPY Pipfile /app/
COPY Pipfile.lock /app/

RUN pipenv sync

COPY . /app/

CMD pipenv run bot
