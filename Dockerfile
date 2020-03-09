FROM python:3.8-alpine

RUN apk add gcc musl-dev

WORKDIR /app

RUN pip install pipenv

ADD Pipfile /app/
ADD Pipfile.lock /app/

RUN pipenv sync

ADD voicechannelbot.py /app/
ADD database.py /app/
ADD models /app/models/

CMD pipenv run bot
