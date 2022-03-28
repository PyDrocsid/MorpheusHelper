FROM python:3.10-alpine AS builder

RUN apk add --no-cache gcc g++ musl-dev libffi-dev postgresql14-dev git

WORKDIR /build

RUN pip install poetry

COPY pyproject.toml /build/
COPY poetry.lock /build/

RUN set -ex \
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
    && adduser -G bot -u 1000 -s /bin/bash -D -H bot \
    && touch health && chown 1000:1000 health

USER bot

COPY --from=builder /build/.venv/lib /usr/local/lib
COPY --from=builder /build/VERSION /app/

COPY config.yml /app/
COPY bot /app/bot/

HEALTHCHECK --interval=10s --timeout=5s --retries=1 \
    CMD sh -c 'test $(expr $(date +%s) - $(cat health)) -lt 30'

CMD ["python", "bot/morpheushelper.py"]
