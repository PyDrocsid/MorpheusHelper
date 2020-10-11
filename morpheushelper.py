import os
import string
import sys
import time
from typing import Optional, Iterable

import sentry_sdk
from PyDrocsid.command_edit import add_to_error_cache
from PyDrocsid.database import db
from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.events import listener, register_cogs, call_event_handlers
from PyDrocsid.help import send_help
from PyDrocsid.translations import translations
from PyDrocsid.util import measure_latency, send_long_embed, send_editable_log
from discord import Message, Embed, User, Forbidden, AllowedMentions, Intents
from discord.ext import tasks
from discord.ext.commands import (
    Bot,
    Context,
    CommandError,
    guild_only,
    CommandNotFound,
    UserInputError,
    check,
    CheckFailure,
)
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from cogs import COGS
from info import MORPHEUS_ICON, CONTRIBUTORS, GITHUB_LINK, VERSION, AVATAR_URL
from permissions import Permission, PermissionLevel, sudo_active
from util import make_error, send_to_changelog, get_prefix, set_prefix
from colours import Colours

banner = r"""

        __  ___                 __                    __  __     __
       /  |/  /___  _________  / /_  ___  __  _______/ / / /__  / /___  ___  _____
      / /|_/ / __ \/ ___/ __ \/ __ \/ _ \/ / / / ___/ /_/ / _ \/ / __ \/ _ \/ ___/
     / /  / / /_/ / /  / /_/ / / / /  __/ /_/ (__  ) __  /  __/ / /_/ /  __/ /
    /_/  /_/\____/_/  / .___/_/ /_/\___/\__,_/____/_/ /_/\___/_/ .___/\___/_/
                     /_/                                      /_/

""".splitlines()
print("\n".join(f"\033[1m\033[36m{line}\033[0m" for line in banner))
print(f"Starting MorpheusHelper v{VERSION} ({GITHUB_LINK})\n")

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


intents = Intents.all()

bot = Bot(command_prefix=fetch_prefix, case_insensitive=True, description=translations.bot_description, intents=intents)
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
            await send_editable_log(
                owner,
                translations.online_status,
                translations.logged_in,
                time.ctime(),
                force_resend=True,
                force_new_embed=bot.initial,
            )
        except Forbidden:
            pass

    print(f"\033[1m\033[36mLogged in as {bot.user}\033[0m")

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
    embed = Embed(title=translations.pong, colour=Colours.ping)
    if latency is not None:
        embed.description = translations.f_pong_latency(latency * 1000)
    await ctx.send(embed=embed)


@check
def is_sudoer(ctx: Context):
    if ctx.author.id != 370876111992913922:
        raise CheckFailure(f"{ctx.author.mention} is not in the sudoers file. This incident will be reported.")

    return True


@bot.command()
@is_sudoer
async def sudo(ctx: Context, *, cmd: str):
    message: Message = ctx.message
    message.content = ctx.prefix + cmd
    sudo_active.set(True)
    await bot.process_commands(message)


@bot.command()
@PermissionLevel.OWNER.check
async def reload(ctx: Context):
    await call_event_handlers("ready")
    await ctx.message.add_reaction(name_to_emoji["white_check_mark"])


@bot.command()
@PermissionLevel.OWNER.check
async def stop(ctx: Context):
    await ctx.message.add_reaction(name_to_emoji["white_check_mark"])
    await bot.close()


@bot.command()
@PermissionLevel.OWNER.check
async def kill(ctx: Context):
    await ctx.message.add_reaction(name_to_emoji["white_check_mark"])
    sys.exit(1)


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
    embed = Embed(title=translations.prefix, description=translations.prefix_updated, colour=Colours.prefix)
    await ctx.send(embed=embed)
    await send_to_changelog(ctx.guild, translations.f_log_prefix_updated(new_prefix))


async def build_info_embed(authorized: bool) -> Embed:
    embed = Embed(title="MorpheusHelper", colour=Colours.info, description=translations.bot_description)
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
        name=translations.bugs_features_title,
        value=translations.bugs_features,
        inline=False,
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

    embed = Embed(
        title="Defelo/MorpheusHelper",
        description="Bot for the Discord Server of The Morpheus Tutorials - Defelo/MorpheusHelper",
        colour=Colours.github,
        url=GITHUB_LINK,
    )
    embed.set_thumbnail(url=AVATAR_URL)
    await ctx.send(embed=embed)


@bot.command(name="version")
async def version(ctx: Context):
    """
    show version
    """

    embed = Embed(title=f"MorpheusHelper v{VERSION}", colour=Colours.version)
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
            await ctx.send(
                embed=make_error(error), allowed_mentions=AllowedMentions(everyone=False, users=False, roles=False)
            )
        ]
    add_to_error_cache(ctx.message, messages)


@listener
async def on_bot_ping(message: Message):
    await message.channel.send(embed=await build_info_embed(False))


cog_blacklist = set(map(str.lower, os.getenv("DISABLED_COGS", "").split(",")))
disabled_cogs = []
enabled_cogs = []
for cog_class in COGS:
    if cog_class.__name__.lower() in cog_blacklist:
        disabled_cogs.append(cog_class.__name__)
        continue

    enabled_cogs.append(cog_class)

register_cogs(bot, *enabled_cogs)

if bot.cogs:
    print(f"\033[1m\033[32m{len(bot.cogs)} Cog{'s' * (len(bot.cogs) > 1)} enabled:\033[0m")
    for cog in bot.cogs.values():
        commands = ", ".join(cmd.name for cmd in cog.get_commands())
        print(f" + {cog.__class__.__name__}" + f" ({commands})" * bool(commands))
if disabled_cogs:
    print(f"\033[1m\033[31m{len(disabled_cogs)} Cog{'s' * (len(disabled_cogs) > 1)} disabled:\033[0m")
    for name in disabled_cogs:
        print(f" - {name}")

bot.run(os.environ["TOKEN"])
