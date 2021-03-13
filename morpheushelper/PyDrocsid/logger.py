import logging

import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from PyDrocsid.environment import DEBUG


def setup_sentry(dsn: str, name: str, version: str):
    sentry_sdk.init(
        dsn=dsn,
        attach_stacktrace=True,
        shutdown_timeout=5,
        integrations=[
            AioHttpIntegration(),
            SqlalchemyIntegration(),
            LoggingIntegration(
                level=logging.DEBUG,
                event_level=logging.WARNING,
            ),
        ],
        release=f"{name}@{version}",
    )


logging_handler = logging.StreamHandler()
logging_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")


def get_logger() -> logging.Logger:
    logger: logging.Logger = logging.getLogger(__name__)
    logging_handler.setFormatter(logging_formatter)
    logger.addHandler(logging_handler)
    logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

    return logger
