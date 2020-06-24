FROM python:3.8-alpine

RUN apk add gcc musl-dev

WORKDIR /app

RUN pip install pipenv

ADD Pipfile /app/
ADD Pipfile.lock /app/

RUN pipenv sync

ADD cleverbot.py /app/
ADD translations.py /app/
ADD multilock.py /app/
ADD database.py /app/
ADD permission.py /app/
ADD util.py /app/
ADD info.py /app/
ADD programmerhumor.py /app/
ADD models /app/models/
ADD cogs /app/cogs/
ADD morpheushelper.py /app/
ADD translations /app/translations/

CMD pipenv run bot
