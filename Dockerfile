FROM python:3.10-alpine AS builder

RUN apk add --no-cache gcc~=10.3 g++~=10.3 musl-dev~=1.2 git~=2.34

WORKDIR /build

RUN pip install pipenv==2021.11.23

COPY Pipfile /build/
COPY Pipfile.lock /build/

ARG PIPENV_NOSPIN=true
ARG PIPENV_VENV_IN_PROJECT=true
RUN pipenv install --deploy --ignore-pipfile

COPY .git /build/.git/
RUN git describe --tags --always > VERSION

FROM python:3.10-alpine

LABEL org.opencontainers.image.source=https://github.com/PyDrocsid/template

WORKDIR /app

RUN set -x \
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

CMD ["python", "bot/pydrocsid_bot.py"]
