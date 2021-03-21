import re
from datetime import datetime
from functools import partial
from typing import Optional, Union, Tuple, Callable

from discord import (
    Member,
    Message,
    Role,
    User,
    RawMessageDeleteEvent,
    RawMessageUpdateEvent,
    NotFound,
    RawReactionActionEvent,
    PartialEmoji,
    TextChannel,
    RawReactionClearEvent,
    RawReactionClearEmojiEvent,
    VoiceState,
    Guild,
    Invite,
)
from discord.abc import Messageable
from discord.ext.commands import Bot, Context, CommandError

from PyDrocsid.command_edit import handle_command_edit
from PyDrocsid.multilock import MultiLock


class StopEventHandling(Exception):
    pass


async def extract_from_raw_reaction_event(
    bot: Bot,
    event: RawReactionActionEvent,
) -> Optional[Tuple[Message, PartialEmoji, Union[User, Member]]]:
    channel: Optional[Messageable] = bot.get_channel(event.channel_id)
    if channel is None:
        return None

    if isinstance(channel, TextChannel):
        user: Member = channel.guild.get_member(event.user_id)
    else:
        user: User = bot.get_user(event.user_id)
    if user is None:
        return None

    try:
        message = await channel.fetch_message(event.message_id)
    except NotFound:
        return None

    return message, event.emoji, user


class Events:
    @staticmethod
    async def on_ready(_):
        await call_event_handlers("ready")

    @staticmethod
    async def on_typing(_, channel: Messageable, user: Union[User, Member], when: datetime):
        await call_event_handlers("typing", channel, user, when, identifier=user.id)

    @staticmethod
    async def on_message(bot: Bot, message: Message):
        if message.author == bot.user:
            await call_event_handlers("self_message", message, identifier=message.id)
            return

        if not await call_event_handlers("message", message, identifier=message.id):
            return

        match = re.match(r"^<@[&!]?(\d+)>$", message.content.strip())
        if match:
            mentions = {bot.user.id}
            if message.guild is not None:
                for role in message.guild.me.roles:  # type: Role
                    if role.managed:
                        mentions.add(role.id)
            if int(match.group(1)) in mentions:
                await call_event_handlers("bot_ping", message, identifier=message.id)
                return

        await bot.process_commands(message)

    @staticmethod
    async def on_message_delete(_, message: Message):
        await call_event_handlers("message_delete", message, identifier=message.id)

    @staticmethod
    async def on_raw_message_delete(_, event: RawMessageDeleteEvent):
        if event.cached_message is not None:
            return

        await call_event_handlers("raw_message_delete", event, identifier=event.message_id)

    @staticmethod
    async def on_message_edit(bot: Bot, before: Message, after: Message):
        await call_event_handlers("message_edit", before, after, identifier=after.id)
        await handle_command_edit(bot, after)

    @staticmethod
    async def on_raw_message_edit(bot: Bot, event: RawMessageUpdateEvent):
        if event.cached_message is not None:
            return

        prepared = []

        async def prepare():
            channel: Optional[Messageable] = bot.get_channel(event.channel_id)
            if channel is None:
                return
            try:
                message: Message = await channel.fetch_message(event.message_id)
            except NotFound:
                return

            prepared.append(message)
            return channel, message

        await call_event_handlers("raw_message_edit", identifier=event.message_id, prepare=prepare)

        if prepared:
            await handle_command_edit(bot, prepared[0])

    @staticmethod
    async def on_raw_reaction_add(bot: Bot, event: RawReactionActionEvent):
        async def prepare():
            return await extract_from_raw_reaction_event(bot, event)

        await call_event_handlers("raw_reaction_add", identifier=event.message_id, prepare=prepare)

    @staticmethod
    async def on_raw_reaction_remove(bot: Bot, event: RawReactionActionEvent):
        async def prepare():
            return await extract_from_raw_reaction_event(bot, event)

        await call_event_handlers("raw_reaction_remove", identifier=event.message_id, prepare=prepare)

    @staticmethod
    async def on_raw_reaction_clear(bot: Bot, event: RawReactionClearEvent):
        async def prepare():
            channel: Optional[Messageable] = bot.get_channel(event.channel_id)
            if channel is None:
                return None
            try:
                return [await channel.fetch_message(event.message_id)]
            except NotFound:
                return None

        await call_event_handlers("raw_reaction_clear", identifier=event.message_id, prepare=prepare)

    @staticmethod
    async def on_raw_reaction_clear_emoji(bot: Bot, event: RawReactionClearEmojiEvent):
        async def prepare():
            channel: Optional[Messageable] = bot.get_channel(event.channel_id)
            if channel is None:
                return None
            try:
                return await channel.fetch_message(event.message_id), event.emoji
            except NotFound:
                return None

        await call_event_handlers("raw_reaction_clear_emoji", identifier=event.message_id, prepare=prepare)

    @staticmethod
    async def on_member_join(_, member: Member):
        await call_event_handlers("member_join", member, identifier=member.id)

    @staticmethod
    async def on_member_remove(_, member: Member):
        await call_event_handlers("member_remove", member, identifier=member.id)

    @staticmethod
    async def on_member_update(_, before: Member, after: Member):
        if before.nick != after.nick:
            await call_event_handlers("member_nick_update", before, after, identifier=before.id)

        roles_before = set(before.roles)
        roles_after = set(after.roles)
        for role in roles_before:
            if role not in roles_after:
                await call_event_handlers("member_role_remove", after, role, identifier=before.id)
        for role in roles_after:
            if role not in roles_before:
                await call_event_handlers("member_role_add", after, role, identifier=before.id)

    @staticmethod
    async def on_user_update(_, before: User, after: User):
        await call_event_handlers("user_update", before, after, identifier=before.id)

    @staticmethod
    async def on_voice_state_update(_, member: Member, before: VoiceState, after: VoiceState):
        await call_event_handlers("voice_state_update", member, before, after, identifier=member.id)

    @staticmethod
    async def on_member_ban(_, guild: Guild, user: Union[User, Member]):
        await call_event_handlers("member_ban", guild, user, identifier=user.id)

    @staticmethod
    async def on_member_unban(_, guild: Guild, user: User):
        await call_event_handlers("member_unban", guild, user, identifier=user.id)

    @staticmethod
    async def on_invite_create(_, invite: Invite):
        await call_event_handlers("invite_create", invite, identifier=invite.code)

    @staticmethod
    async def on_invite_delete(_, invite: Invite):
        await call_event_handlers("invite_delete", invite, identifier=invite.code)

    @staticmethod
    async def on_command_error(_, ctx: Context, error: CommandError):
        await call_event_handlers("command_error", ctx, error, identifier=ctx.message.id)


event_handlers = {}
cog_instances = {}
handler_lock = MultiLock()


def listener(func: Callable):
    name: str = func.__name__
    if not name.startswith("on_"):
        raise Exception("Invalid listener name")
    event_handlers.setdefault(name[3:], []).append(func)
    return func


async def call_event_handlers(event: str, *args, identifier=None, prepare=None) -> bool:
    async with handler_lock[(event, identifier) if identifier is not None else None]:
        if prepare is not None:
            args = await prepare()
            if args is None:
                return False

        for handler in event_handlers.get(event, []):
            try:
                await handler(*args)
            except StopEventHandling:
                return False

        return True


def register_events(bot: Bot):
    for e in dir(Events):
        func = getattr(Events, e)
        if e.startswith("on_") and callable(func):
            handler = partial(func, bot)
            handler.__name__ = e
            bot.event(handler)
