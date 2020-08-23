FROM python:3.8-alpine

RUN apk add --no-cache gcc=9.3.0-r2 musl-dev=1.1.24-r9 git=2.26.2-r0

WORKDIR /app

RUN pip install pipenv==2020.6.2

COPY Pipfile /app/
COPY Pipfile.lock /app/

RUN pipenv sync

COPY . /app/

CMD pipenv run bot
