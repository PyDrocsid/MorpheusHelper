import os
import re
import string
import time
from typing import Optional, Iterable

import sentry_sdk
from discord import (
    Message,
    Role,
    Embed,
    RawReactionActionEvent,
    RawReactionClearEvent,
    RawMessageUpdateEvent,
    RawMessageDeleteEvent,
    Member,
    VoiceState,
    TextChannel,
    User,
    NotFound,
    Forbidden,
)
from discord.ext import tasks
from discord.ext.commands import Bot, Context, CommandError, guild_only, CommandNotFound
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from cogs.betheprofessional import BeTheProfessionalCog
from cogs.cleverbot import CleverBotCog
from cogs.info import InfoCog
from cogs.invites import InvitesCog
from cogs.logging import LoggingCog
from cogs.mediaonly import MediaOnlyCog
from cogs.metaquestion import MetaQuestionCog
from cogs.mod import ModCog
from cogs.news import NewsCog
from cogs.permissions import PermissionsCog
from cogs.random_stuff_enc import RandomStuffCog
from cogs.reaction_pin import ReactionPinCog
from cogs.reactionrole import ReactionRoleCog
from cogs.rules import RulesCog
from cogs.voice_channel import VoiceChannelCog
from programmerhumor import ProgrammerHumor
from database import db
from info import MORPHEUS_ICON, CONTRIBUTORS, GITHUB_LINK, VERSION
from permission import Permission
from translations import translations
from util import (
    permission_level,
    make_error,
    measure_latency,
    send_to_changelog,
    call_event_handlers,
    register_cogs,
    get_prefix,
    set_prefix,
)

sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        attach_stacktrace=True,
        shutdown_timeout=5,
        integrations=[AioHttpIntegration(), SqlalchemyIntegration()],
        release=f"morpheushelper@{VERSION}",
    )

db.create_tables()


async def fetch_prefix(_, message: Message) -> Iterable[str]:
    if message.guild is None:
        return ""
    return await get_prefix(), f"<@!{bot.user.id}> ", f"<@{bot.user.id}> "


bot = Bot(command_prefix=fetch_prefix, case_insensitive=True, description=translations.description)


def get_owner() -> Optional[User]:
    owner_id = os.getenv("OWNER_ID")
    if owner_id and owner_id.isnumeric():
        return bot.get_user(int(owner_id))
    return None


@bot.event
async def on_ready():
    if (owner := get_owner()) is not None:
        try:
            await owner.send("logged in")
        except Forbidden:
            pass

    print(f"Logged in as {bot.user}")

    if owner is not None:
        try:
            status_loop.start()
        except RuntimeError:
            status_loop.restart()

    try:
        programmerhumor_loop.start()
    except RuntimeError:
        programmerhumor_loop.restart()

    await call_event_handlers("ready")


@tasks.loop(seconds=20)
async def status_loop():
    if (owner := get_owner()) is None:
        return
    messages = await owner.history(limit=1).flatten()
    content = "heartbeat: " + time.ctime()
    if messages and messages[0].content.startswith("heartbeat: "):
        await messages[0].edit(content=content)
    else:
        try:
            await owner.send(content)
        except Forbidden:
            pass


@tasks.loop(hours=5)
async def programmerhumor_loop():
    await ProgrammerHumor.run(bot.get_channel(341284235581194241))  # videos-und-memes


@bot.command()
async def ping(ctx: Context):
    """
    display bot latency
    """

    latency: Optional[float] = measure_latency()
    if latency is not None:
        await ctx.send(translations.f_pong_latency(latency * 1000))
    else:
        await ctx.send(translations.pong)


@bot.command(aliases=["yn"])
@guild_only()
async def yesno(ctx: Context, message: Optional[Message] = None):
    """
    adds thumbsup and thumbsdown reactions to the message
    """

    if message is None:
        message = ctx.message
    await message.add_reaction(chr(0x1F44D))
    await message.add_reaction(chr(0x1F44E))


@bot.command(name="prefix")
@permission_level(Permission.change_prefix)
@guild_only()
async def change_prefix(ctx: Context, new_prefix: str):
    """
    change the bot prefix
    """

    if not 0 < len(new_prefix) <= 16:
        raise CommandError(translations.invalid_prefix_length)

    valid_chars = set(string.ascii_letters + string.digits + string.punctuation)
    if any(c not in valid_chars for c in new_prefix):
        raise CommandError(translations.prefix_invalid_chars)

    await set_prefix(new_prefix)
    await ctx.send(translations.prefix_updated)
    await send_to_changelog(ctx.guild, translations.f_log_prefix_updated(new_prefix))


async def build_info_embed(authorized: bool) -> Embed:
    embed = Embed(title="MorpheusHelper", color=0x007700, description=translations.description)
    embed.set_thumbnail(url=MORPHEUS_ICON)
    prefix = await get_prefix()
    features = translations.features
    if authorized:
        features += translations.admin_features
    embed.add_field(
        name=translations.features_title,
        value="\n".join(f":small_orange_diamond: {feature}" for feature in features),
        inline=False,
    )
    embed.add_field(name=translations.author_title, value="<@370876111992913922>", inline=True)
    embed.add_field(name=translations.contributors_title, value=", ".join(f"<@{c}>" for c in CONTRIBUTORS), inline=True)
    embed.add_field(name=translations.version_title, value=VERSION, inline=True)
    embed.add_field(name=translations.github_title, value=GITHUB_LINK, inline=False)
    embed.add_field(name=translations.prefix_title, value=f"`{prefix}` or {bot.user.mention}", inline=True)
    embed.add_field(name=translations.help_command_title, value=f"`{prefix}help`", inline=True)
    embed.add_field(
        name=translations.bugs_features_title, value=translations.bugs_features, inline=False,
    )
    return embed


@bot.command(name="info", aliases=["infos", "about"])
async def info(ctx: Context):
    """
    show information about the bot
    """

    await ctx.send(embed=await build_info_embed(False))


@bot.command(name="admininfo", aliases=["admininfos"])
@permission_level(Permission.admininfo)
async def admininfo(ctx: Context):
    """
    show information about the bot (admin view)
    """

    await ctx.send(embed=await build_info_embed(True))


@bot.event
async def on_error(*_, **__):
    if sentry_dsn:
        sentry_sdk.capture_exception()
    else:
        raise  # skipcq: PYL-E0704


@bot.event
async def on_command_error(ctx: Context, error: CommandError):
    if isinstance(error, CommandNotFound) and ctx.guild is not None and ctx.prefix == await get_prefix():
        return
    await ctx.send(make_error(error))


@bot.event
async def on_raw_reaction_add(event: RawReactionActionEvent):
    async def prepare():
        channel: TextChannel = bot.get_channel(event.channel_id)
        if not isinstance(channel, TextChannel):
            return
        try:
            message = await channel.fetch_message(event.message_id)
        except NotFound:
            return
        return message, event.emoji, channel.guild.get_member(event.user_id)

    await call_event_handlers("raw_reaction_add", identifier=event.message_id, prepare=prepare)


@bot.event
async def on_raw_reaction_remove(event: RawReactionActionEvent):
    async def prepare():
        channel: TextChannel = bot.get_channel(event.channel_id)
        if not isinstance(channel, TextChannel):
            return
        try:
            message = await channel.fetch_message(event.message_id)
        except NotFound:
            return
        return message, event.emoji, channel.guild.get_member(event.user_id)

    await call_event_handlers("raw_reaction_remove", identifier=event.message_id, prepare=prepare)


@bot.event
async def on_raw_reaction_clear(event: RawReactionClearEvent):
    async def prepare():
        channel: TextChannel = bot.get_channel(event.channel_id)
        if not isinstance(channel, TextChannel):
            return
        try:
            return [await channel.fetch_message(event.message_id)]
        except NotFound:
            return

    await call_event_handlers("raw_reaction_clear", identifier=event.message_id, prepare=prepare)


@bot.event
async def on_message_edit(before: Message, after: Message):
    if before.guild is None:
        return
    await call_event_handlers("message_edit", before, after, identifier=after.id)


@bot.event
async def on_raw_message_edit(event: RawMessageUpdateEvent):
    if event.cached_message is not None:
        return

    async def prepare():
        channel: TextChannel = bot.get_channel(event.channel_id)
        if not isinstance(channel, TextChannel):
            return
        try:
            return channel, await channel.fetch_message(event.message_id)
        except NotFound:
            return

    await call_event_handlers("raw_message_edit", identifier=event.message_id, prepare=prepare)


@bot.event
async def on_message_delete(message: Message):
    if message.guild is None:
        return
    await call_event_handlers("message_delete", message, identifier=message.id)


@bot.event
async def on_raw_message_delete(event: RawMessageDeleteEvent):
    if event.cached_message is not None or event.guild_id is None:
        return

    await call_event_handlers("raw_message_delete", event, identifier=event.message_id)


@bot.event
async def on_voice_state_update(member: Member, before: VoiceState, after: VoiceState):
    await call_event_handlers("voice_state_update", member, before, after, identifier=member.id)


@bot.event
async def on_member_join(member: Member):
    await call_event_handlers("member_join", member, identifier=member.id)


@bot.event
async def on_member_remove(member: Member):
    await call_event_handlers("member_remove", member, identifier=member.id)


@bot.event
async def on_member_update(before: Member, after: Member):
    await call_event_handlers("member_update", before, after, identifier=before.id)


@bot.event
async def on_user_update(before: User, after: User):
    await call_event_handlers("user_update", before, after, identifier=before.id)


@bot.event
async def on_message(message: Message):
    if message.author == bot.user:
        await call_event_handlers("self_message", message, identifier=message.id)
        return

    if not await call_event_handlers("message", message, identifier=message.id):
        return

    match = re.match(r"^<@[&!]?(\d+)>$", message.content.strip())
    if match:
        mentions = [bot.user.id]
        if message.guild is not None:
            for role in message.guild.me.roles:  # type: Role
                if role.managed:
                    mentions.append(role.id)
        if int(match.group(1)) in mentions:
            await message.channel.send(embed=await build_info_embed(False))
            return

    await bot.process_commands(message)


register_cogs(
    bot,
    VoiceChannelCog,
    ReactionPinCog,
    BeTheProfessionalCog,
    LoggingCog,
    MediaOnlyCog,
    RulesCog,
    InvitesCog,
    MetaQuestionCog,
    InfoCog,
    ReactionRoleCog,
    CleverBotCog,
    NewsCog,
    RandomStuffCog,
    ModCog,
    PermissionsCog,
)
bot.run(os.environ["TOKEN"])
