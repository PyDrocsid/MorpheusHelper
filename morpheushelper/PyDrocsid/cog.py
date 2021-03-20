from __future__ import annotations

from datetime import datetime
from os import getenv
from typing import Union, Type, Optional

from discord import (
    Member,
    Message,
    RawMessageDeleteEvent,
    VoiceState,
    Guild,
    Invite,
    PartialEmoji,
    Role,
)
from discord.abc import Messageable, User
from discord.ext.commands import Cog as DiscordCog, Bot, Context, CommandError

from PyDrocsid.config import Config, Contributor
from PyDrocsid.events import register_events, event_handlers
from PyDrocsid.logger import get_logger
from PyDrocsid.permission import BasePermission

logger = get_logger(__name__)


class Cog(DiscordCog):
    CONTRIBUTORS: list[Contributor]
    PERMISSIONS: Type[BasePermission]
    DEPENDENCIES: list[Type[Cog]] = []

    instance: Optional[Cog] = None
    bot: Bot

    def __new__(cls, *args, **kwargs):
        if cls.instance is None:
            cls.instance = super().__new__(cls, *args, **kwargs)

        return cls.instance

    @staticmethod
    def prepare() -> bool:
        return True

    async def on_ready(self):
        pass

    async def on_typing(self, channel: Messageable, user: Union[User, Member], when: datetime):
        pass

    async def on_self_message(self, message: Message):
        pass

    async def on_message(self, message: Message):
        pass

    async def on_bot_ping(self, message: Message):
        pass

    async def on_message_delete(self, message: Message):
        pass

    async def on_raw_message_delete(self, event: RawMessageDeleteEvent):
        pass

    async def on_message_edit(self, before: Message, after: Message):
        pass

    async def on_raw_message_edit(self, channel: Messageable, message: Message):
        pass

    async def on_raw_reaction_add(self, message: Message, emoji: PartialEmoji, user: Union[Member, User]):
        pass

    async def on_raw_reaction_remove(self, message: Message, emoji: PartialEmoji, user: Union[Member, User]):
        pass

    async def on_raw_reaction_clear(self, message: Message):
        pass

    async def on_raw_reaction_clear_emoji(self, message: Message, emoji: PartialEmoji):
        pass

    async def on_member_join(self, member: Member):
        pass

    async def on_member_remove(self, member: Member):
        pass

    async def on_member_nick_update(self, before: str, after: str):
        pass

    async def on_member_role_add(self, after, role: Role):
        pass

    async def on_member_role_remove(self, after, role: Role):
        pass

    async def on_user_update(self, before: User, after: User):
        pass

    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        pass

    async def on_member_ban(self, guild: Guild, user: Union[User, Member]):
        pass

    async def on_member_unban(self, guild: Guild, user: User):
        pass

    async def on_invite_create(self, invite: Invite):
        pass

    async def on_invite_delete(self, invite: Invite):
        pass

    async def on_command_error(self, ctx: Context, error: CommandError):
        pass


def check_dependencies(cogs: list[Cog]) -> set[Type[Cog]]:
    available: set[Type[Cog]] = {type(cog) for cog in cogs}
    required_by: dict[Type[Cog], list[Cog]] = {}
    for cog in cogs:
        for dependency in cog.DEPENDENCIES:
            required_by.setdefault(dependency, []).append(cog)

    disabled: set[Type[Cog]] = set()
    not_available: list[Type[Cog]] = [dependency for dependency in required_by if dependency not in available]
    while not_available:
        dependency: Type[Cog] = not_available.pop()
        if dependency not in required_by:
            continue

        for cog in required_by[dependency]:
            if type(cog) in disabled:
                continue

            logger.warning(
                "Cog '%s' has been disabled because the dependency '%s' is missing.",
                cog.__class__.__name__,
                dependency.__name__,
            )
            disabled.add(type(cog))
            not_available.append(type(cog))

    return disabled


def register_cogs(bot: Bot, *cogs: Cog):
    register_events(bot)

    for cog in cogs:
        cog.bot = bot
        for e in dir(Cog):
            func = getattr(cog, e)
            if e.startswith("on_") and callable(func) and getattr(type(cog), e) is not getattr(Cog, e):
                event_handlers.setdefault(e[3:], []).append(func)
        bot.add_cog(cog)
        Config.CONTRIBUTORS.update(cog.CONTRIBUTORS)
        Config.PERMISSIONS += cog.PERMISSIONS


def load_cogs(bot: Bot, *cogs: Cog):
    cog_blacklist = set(map(str.lower, getenv("DISABLED_COGS", "").split(",")))
    disabled_cogs: list[Cog] = []
    enabled_cogs: list[Cog] = []
    for cog in cogs:
        if cog.__class__.__name__.lower() in cog_blacklist or not cog.prepare():
            disabled_cogs.append(cog)
            continue

        enabled_cogs.append(cog)

    disabled: set[Type[Cog]] = check_dependencies(enabled_cogs)
    disabled_cogs += [cog for cog in enabled_cogs if type(cog) in disabled]
    enabled_cogs = [cog for cog in enabled_cogs if type(cog) not in disabled]

    register_cogs(bot, *enabled_cogs)

    if bot.cogs:
        logger.info("\033[1m\033[32m%s Cog%s enabled:\033[0m", len(bot.cogs), "s" * (len(bot.cogs) > 1))
        for cog in bot.cogs.values():
            commands = ", ".join(cmd.name for cmd in cog.get_commands())
            if commands:
                commands = f"({commands})"

            logger.info(" + %s %s", cog.__class__.__name__, commands)

    if disabled_cogs:
        logger.info("\033[1m\033[31m%s Cog%s disabled:\033[0m", len(disabled_cogs), "s" * (len(disabled_cogs) > 1))
        for name in disabled_cogs:
            logger.info(" - %s", name.__class__.__name__)
