from os import environ
import logging
from typing import Optional

# default config dictionary
# value = None => variable is REQUIRED
DEFAULT_CONFIG: dict[str, any] = {
    "TOKEN": None,
    "DB_HOST": "db",
    "DB_PORT": 3306,
    "DB_DATABASE": "morpheushelper",
    "DB_USER": "morpheushelper",
    "DB_PASSWORD": "morpheushelper",
    "REDIS_HOSTNAME": "redis",
    "REDIS_PORT": 6379,
    "WARN_LEVEL_THRESHOLD": 1,
    "SENTRY_DSN": None,
    "OWNER_ID": "",
    "DISABLED_COGS": "",
}


def get_config_entry(key: str) -> Optional[any]:
    if key in environ:
        return environ[key]

    if key in DEFAULT_CONFIG:
        value: any = DEFAULT_CONFIG[key]

        if not value:
            logging.error(f"Required environment variable called {key} NOT found.".format(key=key))

        return value

    return None
