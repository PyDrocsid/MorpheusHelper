import os
import re
import string
from typing import Optional, Iterable

import sentry_sdk
from discord import (
    Message,
    Role,
    Status,
    Game,
    Embed,
    RawReactionActionEvent,
    RawReactionClearEvent,
    RawMessageUpdateEvent,
    RawMessageDeleteEvent,
    Member,
    VoiceState,
    TextChannel,
)
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
from cogs.random_stuff_enc import RandomStuffCog
from cogs.reaction_pin import ReactionPinCog
from cogs.reactionrole import ReactionRoleCog
from cogs.rules import RulesCog
from cogs.voice_channel import VoiceChannelCog
from database import db, run_in_thread
from models.authorized_role import AuthorizedRole
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
    )

db.create_tables()


async def fetch_prefix(_, message: Message) -> Iterable[str]:
    if message.guild is None:
        return ""
    return await get_prefix(), f"<@!{bot.user.id}> ", f"<@{bot.user.id}> "


bot = Bot(command_prefix=fetch_prefix, case_insensitive=True, description=translations.description)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    await bot.change_presence(status=Status.online, activity=Game(name=translations.profile_status))

    await call_event_handlers("ready")


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
async def yesno(ctx: Context):
    """
    adds thumbsup and thumbsdown reactions to the message
    """

    await ctx.message.add_reaction(chr(0x1F44D))
    await ctx.message.add_reaction(chr(0x1F44E))


@bot.command(name="prefix")
@permission_level(1)
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


@bot.group()
@permission_level(2)
@guild_only()
async def auth(ctx: Context):
    """
    manage roles authorized to control this bot
    """

    if ctx.invoked_subcommand is None:
        await ctx.send_help(auth)


@auth.command(name="list", aliases=["l", "?"])
async def auth_list(ctx: Context):
    """
    list authorized roles
    """

    roles = []
    for auth_role in await run_in_thread(db.all, AuthorizedRole):
        if (role := ctx.guild.get_role(auth_role.role)) is not None:
            roles.append(f" - `@{role}` (`{role.id}`)")
        else:
            await run_in_thread(db.delete, auth_role)
    if roles:
        await ctx.send(translations.authorized_roles_header + "\n" + "\n".join(roles))
    else:
        await ctx.send(translations.no_authorized_roles)


@auth.command(name="add", aliases=["a", "+"])
async def auth_add(ctx: Context, *, role: Role):
    """
    authorize role to control this bot
    """

    authorization: Optional[AuthorizedRole] = await run_in_thread(db.get, AuthorizedRole, role.id)
    if authorization is not None:
        raise CommandError(translations.f_already_authorized(role))

    await run_in_thread(AuthorizedRole.create, role.id)
    await ctx.send(translations.f_role_authorized(role))
    await send_to_changelog(ctx.guild, translations.f_log_role_authorized(role))


@auth.command(name="remove", aliases=["del", "r", "d", "-"])
async def auth_del(ctx: Context, *, role: Role):
    """
    unauthorize role to control this bot
    """

    authorization: Optional[AuthorizedRole] = await run_in_thread(db.get, AuthorizedRole, role.id)
    if authorization is None:
        raise CommandError(translations.f_not_authorized(role))

    await run_in_thread(db.delete, authorization)
    await ctx.send(translations.f_role_unauthorized(role))
    await send_to_changelog(ctx.guild, translations.f_log_role_unauthorized(role))


async def build_info_embed(authorized: bool) -> Embed:
    embed = Embed(title="MorpheusHelper", color=0x007700, description=translations.description)
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/avatars/686299664726622258/cb99c816286bdd1d988ec16d8ae85e15.png"
    )
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
    embed.add_field(
        name=translations.contributors_title, value="<@212866839083089921>, <@330148908531580928>", inline=True
    )
    embed.add_field(name=translations.github_title, value="https://github.com/Defelo/MorpheusHelper", inline=False)
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
@permission_level(1)
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
        raise


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
        return await channel.fetch_message(event.message_id), event.emoji, channel.guild.get_member(event.user_id)

    await call_event_handlers("raw_reaction_add", identifier=event.message_id, prepare=prepare)


@bot.event
async def on_raw_reaction_remove(event: RawReactionActionEvent):
    async def prepare():
        channel: TextChannel = bot.get_channel(event.channel_id)
        if not isinstance(channel, TextChannel):
            return
        return await channel.fetch_message(event.message_id), event.emoji, channel.guild.get_member(event.user_id)

    await call_event_handlers("raw_reaction_remove", identifier=event.message_id, prepare=prepare)


@bot.event
async def on_raw_reaction_clear(event: RawReactionClearEvent):
    async def prepare():
        channel: TextChannel = bot.get_channel(event.channel_id)
        if not isinstance(channel, TextChannel):
            return
        return [await channel.fetch_message(event.message_id)]

    await call_event_handlers("raw_reaction_clear", identifier=event.message_id, prepare=prepare)


@bot.event
async def on_message_edit(before: Message, after: Message):
    await call_event_handlers("message_edit", before, after, identifier=after.id)


@bot.event
async def on_raw_message_edit(event: RawMessageUpdateEvent):
    if event.cached_message is not None:
        return

    async def prepare():
        channel: TextChannel = bot.get_channel(event.channel_id)
        if not isinstance(channel, TextChannel):
            return
        return channel, await channel.fetch_message(event.message_id)

    await call_event_handlers("raw_message_edit", identifier=event.message_id, prepare=prepare)


@bot.event
async def on_message_delete(message: Message):
    await call_event_handlers("message_delete", message, identifier=message.id)


@bot.event
async def on_raw_message_delete(event: RawMessageDeleteEvent):
    if event.cached_message is not None:
        return

    await call_event_handlers("raw_message_delete", event, identifier=event.message_id)


@bot.event
async def on_voice_state_update(member: Member, before: VoiceState, after: VoiceState):
    await call_event_handlers("voice_state_update", member, before, after, identifier=member.id)


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
    RandomStuffCog,
)
bot.run(os.environ["TOKEN"])
