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

        ____        ____                       _     __   ____        __
       / __ \__  __/ __ \_________  __________(_)___/ /  / __ )____  / /_
      / /_/ / / / / / / / ___/ __ \/ ___/ ___/ / __  /  / __  / __ \/ __/
     / ____/ /_/ / /_/ / /  / /_/ / /__(__  ) / /_/ /  / /_/ / /_/ / /_
    /_/    \__, /_____/_/   \____/\___/____/_/\__,_/  /_____/\____/\__/
          /____/

    """
    "\033[0m",
)

logger.info(f"Starting {Config.NAME} v{Config.VERSION} ({Config.REPO_LINK})\n")

if SENTRY_DSN:
    logger.debug("initializing sentry")
    setup_sentry(SENTRY_DSN, Config.NAME, Config.VERSION)

__import__("bot").run()
