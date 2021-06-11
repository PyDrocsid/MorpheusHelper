from pathlib import Path

from PyDrocsid.config import Config, load_config_file, load_version
from PyDrocsid.environment import SENTRY_DSN
from PyDrocsid.logger import setup_sentry, get_logger

logger = get_logger(__name__)

logger.debug("loading config")
load_config_file(Path("config.yml"))

logger.debug("loading version")
load_version()

print(
    "\033[1m\033[36m"
    r"""

        __  ___                 __                    __  __     __
       /  |/  /___  _________  / /_  ___  __  _______/ / / /__  / /___  ___  _____
      / /|_/ / __ \/ ___/ __ \/ __ \/ _ \/ / / / ___/ /_/ / _ \/ / __ \/ _ \/ ___/
     / /  / / /_/ / /  / /_/ / / / /  __/ /_/ (__  ) __  /  __/ / /_/ /  __/ /
    /_/  /_/\____/_/  / .___/_/ /_/\___/\__,_/____/_/ /_/\___/_/ .___/\___/_/
                     /_/                                      /_/

    """
    "\033[0m",
)

logger.info(f"Starting {Config.NAME} v{Config.VERSION} ({Config.REPO_LINK})\n")

if SENTRY_DSN:
    logger.debug("initializing sentry")
    setup_sentry(SENTRY_DSN, Config.NAME, Config.VERSION)

from bot import run  # noqa: E402

run()
