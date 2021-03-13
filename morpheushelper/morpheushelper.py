from pathlib import Path

from PyDrocsid.config import Config, load_config_file, load_version
from PyDrocsid.database import db
from PyDrocsid.environment import SENTRY_DSN
from PyDrocsid.logger import setup_sentry

load_config_file(Path("config.yml"))
load_version()

banner = r"""

        __  ___                 __                    __  __     __
       /  |/  /___  _________  / /_  ___  __  _______/ / / /__  / /___  ___  _____
      / /|_/ / __ \/ ___/ __ \/ __ \/ _ \/ / / / ___/ /_/ / _ \/ / __ \/ _ \/ ___/
     / /  / / /_/ / /  / /_/ / / / /  __/ /_/ (__  ) __  /  __/ / /_/ /  __/ /
    /_/  /_/\____/_/  / .___/_/ /_/\___/\__,_/____/_/ /_/\___/_/ .___/\___/_/
                     /_/                                      /_/

""".splitlines()
print("\n".join(f"\033[1m\033[36m{line}\033[0m" for line in banner))
print(f"Starting {Config.NAME} v{Config.VERSION} ({Config.REPO_LINK})\n")

if SENTRY_DSN:
    setup_sentry(SENTRY_DSN, Config.NAME, Config.VERSION)

db.create_tables()

__import__("bot").run()
