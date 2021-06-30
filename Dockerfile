FROM python:3.9.6-alpine AS builder

RUN apk add --no-cache gcc~=10.3 g++~=10.3 musl-dev~=1.2 git~=2.32

WORKDIR /build

RUN pip install pipenv==2020.11.15

COPY Pipfile /build/
COPY Pipfile.lock /build/

ARG PIPENV_NOSPIN=true
ARG PIPENV_VENV_IN_PROJECT=true
RUN pipenv install --deploy --ignore-pipfile

COPY .git /build/.git/
RUN git describe --tags --always > VERSION

FROM python:3.9.6-alpine

LABEL org.opencontainers.image.source=https://github.com/PyDrocsid/template

RUN set -x \
    && addgroup -g 1000 bot \
    && adduser -G bot -u 1000 -s /bin/bash -D -H bot

WORKDIR /app

USER bot

COPY --from=builder /build/.venv/lib /usr/local/lib
COPY --from=builder /build/VERSION /app/

COPY config.yml /app/
COPY bot /app/bot/

CMD ["python", "bot/pydrocsid_bot.py"]
