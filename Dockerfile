FROM python:3.10-alpine AS builder

RUN apk add --no-cache build-base gcc g++ musl-dev libffi-dev postgresql14-dev git python3-dev openssl-dev cargo

WORKDIR /build

RUN pip install poetry

COPY pyproject.toml /build/
COPY poetry.lock /build/
COPY library /build/library

RUN set -ex \
    && sed -i 's/develop = true/develop = false/' pyproject.toml poetry.lock \
    && virtualenv .venv \
    && . .venv/bin/activate \
    && poetry install -n --no-root --no-dev

COPY .git /build/.git/
RUN git describe --tags --always > VERSION

FROM python:3.10-alpine

LABEL org.opencontainers.image.source=https://github.com/PyDrocsid/MorpheusHelper

WORKDIR /app

RUN set -x \
    && apk add --no-cache libpq \
    && addgroup -g 1000 bot \
    && adduser -G bot -u 1000 -s /bin/sh -D -H bot \
    && touch health && chown 1000:1000 health

COPY --from=builder /build/.venv/lib /usr/local/lib
COPY --from=builder /build/VERSION /app/

COPY config.yml /app/
COPY bot /app/bot/

RUN pip uninstall -y pip setuptools

USER bot

HEALTHCHECK --interval=10s --timeout=5s --retries=1 \
    CMD sh -c 'test $(expr $(date +%s) - $(cat health)) -lt 30'

CMD ["python", "bot/morpheushelper.py"]
