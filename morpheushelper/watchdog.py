from discord import Client, Message, DMChannel
import logging
from warn.user_warn_level import increase_warn_score
from config.config import get_config_entry


class WatchDogClient(Client):
    """
    This feature, appropriately named `WatchDog`, connects to multiple accounts as self bots to prevent unwanted
    advertising via direct messages. A warn score is increased as soon as any user writes to the bot. With this,
    from a warning score threshold unwanted users can be banned from the server.
    """

    ACTIVE_WATCHDOGS: dict[int, "WatchDogClient"] = []

    async def on_ready(self):
        WatchDogClient.ACTIVE_WATCHDOGS[self.user.id] = self
        logging.info("Started watchdog on %s", self.user.id)

    async def on_message(self, message: Message):
        if not isinstance(message.channel, DMChannel):
            return

        # maybe add regex match here to ensure that the received message contains an malicious url

        await increase_warn_score(message.author)

    @staticmethod
    async def start_watchdogs():
        tokens = get_config_entry("WATCHDOG_TOKENS")

        if not tokens:
            return

        for token in tokens.split(","):
            if not isinstance(token, str):
                continue

            watchdog: WatchDogClient = WatchDogClient()
            watchdog.run(token)
