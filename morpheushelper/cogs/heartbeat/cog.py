import os
from datetime import datetime
from typing import Optional

from discord import User, Forbidden
from discord.ext import tasks

from PyDrocsid.cog import Cog
from PyDrocsid.config import Config
from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations
from PyDrocsid.util import send_editable_log
from ..contributor import Contributor


class HeartbeatCog(Cog, name="Heartbeat"):
    CONTRIBUTORS = [Contributor.Defelo, Contributor.wolflu]
    PERMISSIONS = BasePermission

    def __init__(self):
        self.initialized = False

    def get_owner(self) -> Optional[User]:
        owner_id = os.getenv("OWNER_ID")
        if owner_id and owner_id.isnumeric():
            return self.bot.get_user(int(owner_id))
        return None

    @tasks.loop(seconds=20)
    async def status_loop(self):
        if (owner := self.get_owner()) is None:
            return
        try:
            await send_editable_log(
                owner,
                translations.online_status,
                translations.f_status_description(Config.VERSION),
                translations.heartbeat,
                datetime.utcnow().strftime("%d.%m.%Y %H:%M:%S UTC"),
            )
        except Forbidden:
            pass

    async def on_ready(self):
        if (owner := self.get_owner()) is not None:
            try:
                await send_editable_log(
                    owner,
                    translations.online_status,
                    translations.f_status_description(Config.VERSION),
                    translations.logged_in,
                    datetime.utcnow().strftime("%d.%m.%Y %H:%M:%S UTC"),
                    force_resend=True,
                    force_new_embed=not self.initialized,
                )
            except Forbidden:
                pass

        if owner is not None:
            try:
                self.status_loop.start()
            except RuntimeError:
                self.status_loop.restart()

        self.initialized = True
