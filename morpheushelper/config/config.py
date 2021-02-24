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

CACHED_CONFIG: dict[str, any] = dict.fromkeys(DEFAULT_CONFIG.keys(), [])


def get_config_entry(key: str) -> Optional[any]:
    if key in CACHED_CONFIG:
        return CACHED_CONFIG[key]

    if key in environ:
        value: any = environ[key]
        CACHED_CONFIG[key] = value

        if not value:
            logging.error("Required environment variable called %s NOT in environment found.", key)

        return value

    if key in DEFAULT_CONFIG:
        value: any = DEFAULT_CONFIG[key]
        CACHED_CONFIG[key] = value

        if not value:
            logging.error("Required environment variable called %s NOT in DEFAULT config found.", key)

        return value

    return None
