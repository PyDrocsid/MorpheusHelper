FROM python:3.8-alpine

RUN apk add gcc musl-dev

WORKDIR /app

RUN pip install pipenv

ADD Pipfile /app/
ADD Pipfile.lock /app/

RUN pipenv sync

ADD morpheushelper.py /app/
ADD database.py /app/
ADD util.py /app/
ADD multilock.py /app/
ADD models /app/models/
ADD cogs /app/cogs/

CMD pipenv run bot
