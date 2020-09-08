import os
import string
import time
from typing import Optional, Iterable

import sentry_sdk
from PyDrocsid.command_edit import add_to_error_cache
from PyDrocsid.database import db
from PyDrocsid.events import listener, register_cogs
from PyDrocsid.help import send_help
from PyDrocsid.translations import translations
from PyDrocsid.util import measure_latency, send_long_embed, send_editable_log
from discord import (
    Message,
    Embed,
    User,
    Forbidden,
    AllowedMentions,
)
from discord.ext import tasks
from discord.ext.commands import (
    Bot,
    Context,
    CommandError,
    guild_only,
    CommandNotFound,
    UserInputError,
)
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from cogs.automod import AutoModCog
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
from cogs.reaction_pin import ReactionPinCog
from cogs.reactionrole import ReactionRoleCog
from cogs.reddit import RedditCog
from cogs.rules import RulesCog
from cogs.verification import VerificationCog
from cogs.voice_channel import VoiceChannelCog
from info import MORPHEUS_ICON, CONTRIBUTORS, GITHUB_LINK, VERSION, AVATAR_URL
from permissions import Permission
from util import make_error, send_to_changelog, get_prefix, set_prefix, get_colour

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


bot = Bot(command_prefix=fetch_prefix, case_insensitive=True, description=translations.bot_description)
bot.remove_command("help")
bot.initial = True


def get_owner() -> Optional[User]:
    owner_id = os.getenv("OWNER_ID")
    if owner_id and owner_id.isnumeric():
        return bot.get_user(int(owner_id))
    return None


@listener
async def on_ready():
    if (owner := get_owner()) is not None:
        try:
            await send_editable_log(owner, translations.online_status, translations.logged_in, time.ctime(),
                                    force_resend=True, force_new_embed=bot.initial)
        except Forbidden:
            pass

    print(f"Logged in as {bot.user}")

    if owner is not None:
        try:
            status_loop.start()
        except RuntimeError:
            status_loop.restart()

    bot.initial = False


@tasks.loop(seconds=20)
async def status_loop():
    if (owner := get_owner()) is None:
        return
    try:
        await send_editable_log(owner, translations.online_status, translations.heartbeat, time.ctime())
    except Forbidden:
        pass


@bot.command()
async def ping(ctx: Context):
    """
    display bot latency
    """

    latency: Optional[float] = measure_latency()
    embed = Embed(title=translations.pong, colour=get_colour("ping"))
    if latency is not None:
        embed.description = translations.f_pong_latency(latency * 1000)
    await ctx.send(embed=embed)


@bot.command(aliases=["yn"])
@guild_only()
async def yesno(ctx: Context, message: Optional[Message] = None):
    """
    adds thumbsup and thumbsdown reactions to the message
    """

    if message is None or message.guild is None:
        message = ctx.message

    if message.channel.permissions_for(ctx.author).add_reactions:
        await message.add_reaction(chr(0x1F44D))
        await message.add_reaction(chr(0x1F44E))


@bot.command(name="prefix")
@Permission.change_prefix.check
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
    embed = Embed(title=translations.prefix, description=translations.prefix_updated, colour=get_colour())
    await ctx.send(embed=embed)
    await send_to_changelog(ctx.guild, translations.f_log_prefix_updated(new_prefix))


async def build_info_embed(authorized: bool) -> Embed:
    embed = Embed(title="MorpheusHelper", colour=get_colour("info"), description=translations.bot_description)
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
    embed.add_field(name=translations.contributors_title, value=" ".join(f"<@{c}>" for c in CONTRIBUTORS), inline=True)
    embed.add_field(name=translations.version_title, value=VERSION, inline=True)
    embed.add_field(name=translations.github_title, value=GITHUB_LINK, inline=False)
    embed.add_field(name=translations.prefix_title, value=f"`{prefix}` or {bot.user.mention}", inline=True)
    embed.add_field(name=translations.help_command_title, value=f"`{prefix}help`", inline=True)
    embed.add_field(
        name=translations.bugs_features_title, value=translations.bugs_features, inline=False,
    )
    return embed


@bot.command(name="help")
async def help_cmd(ctx: Context, *, cog_or_command: Optional[str]):
    """
    Shows this Message
    """

    await send_help(ctx, cog_or_command)


@bot.command(name="github", aliases=["gh"])
async def github(ctx: Context):
    """
    return the github link
    """

    embed = Embed(title="Defelo/MorpheusHelper",
                  description="Bot for the Discord Server of The Morpheus Tutorials - Defelo/MorpheusHelper",
                  colour=get_colour("github"),
                  url=GITHUB_LINK)
    embed.set_thumbnail(url=AVATAR_URL)
    await ctx.send(embed=embed)


@bot.command(name="version")
async def version(ctx: Context):
    """
    show version
    """

    embed = Embed(title=f"MorpheusHelper v{VERSION}", colour=get_colour())
    await ctx.send(embed=embed)


@bot.command(name="info", aliases=["infos", "about"])
async def info(ctx: Context):
    """
    show information about the bot
    """

    await send_long_embed(ctx, await build_info_embed(False))


@bot.command(name="admininfo", aliases=["admininfos"])
@Permission.admininfo.check
async def admininfo(ctx: Context):
    """
    show information about the bot (admin view)
    """

    await send_long_embed(ctx, await build_info_embed(True))


@bot.event
async def on_error(*_, **__):
    if sentry_dsn:
        sentry_sdk.capture_exception()
    else:
        raise  # skipcq: PYL-E0704


@bot.event
async def on_command_error(ctx: Context, error: CommandError):
    if isinstance(error, CommandNotFound) and ctx.guild is not None and ctx.prefix == await get_prefix():
        messages = []
    elif isinstance(error, UserInputError):
        messages = await send_help(ctx, ctx.command)
    else:
        messages = [
            await ctx.send(embed=make_error(error),
                           allowed_mentions=AllowedMentions(everyone=False, users=False, roles=False))
        ]
    add_to_error_cache(ctx.message, messages)


@listener
async def on_bot_ping(message: Message):
    await message.channel.send(embed=await build_info_embed(False))


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
    ModCog,
    PermissionsCog,
    RedditCog,
    AutoModCog,
    VerificationCog,
)
bot.run(os.environ["TOKEN"])
