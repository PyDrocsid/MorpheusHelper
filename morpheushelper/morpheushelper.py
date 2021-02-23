import os
from pathlib import Path
from typing import Iterable

import sentry_sdk
from discord import Message, Intents
from discord.ext.commands import Bot, Context, CommandError, CommandNotFound, UserInputError

from PyDrocsid.cog import load_cogs
from PyDrocsid.command_edit import add_to_error_cache
from PyDrocsid.config import Config, load_config_file, load_version
from PyDrocsid.database import db
from PyDrocsid.events import listener
from PyDrocsid.help import send_help
from PyDrocsid.translations import translations
from PyDrocsid.util import make_error
from PyDrocsid.util import setup_sentry
from cogs import (
    AdventOfCodeCog,
    AutoModCog,
    BeTheProfessionalCog,
    BotInfoCog,
    CodeblocksCog,
    DiscordpyDocumentationCog,
    InvitesCog,
    LoggingCog,
    MediaOnlyCog,
    MessageCog,
    MetaQuestionCog,
    ModCog,
    PermissionsCog,
    PollsCog,
    ReactionPinCog,
    ReactionRoleCog,
    RedditCog,
    RunCodeCog,
    ServerInfoCog,
    SettingsCog,
    SudoCog,
    UtilsCog,
    VerificationCog,
    VoiceChannelCog,
    HeartbeatCog,
)
from cogs.settings.cog import get_prefix

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

if sentry_dsn := os.environ.get("SENTRY_DSN"):
    setup_sentry(sentry_dsn, Config.VERSION)

db.create_tables()


async def fetch_prefix(_, message: Message) -> Iterable[str]:
    prefix = [await get_prefix(), f"<@!{bot.user.id}> ", f"<@{bot.user.id}> "]

    if message.guild is None:
        prefix.append("")

    return prefix


bot = Bot(
    command_prefix=fetch_prefix,
    case_insensitive=True,
    description=translations.bot_description,
    intents=(Intents.all()),
)
bot.remove_command("help")


@listener
async def on_ready():
    print(f"\033[1m\033[36mLogged in as {bot.user}\033[0m")


@bot.event
async def on_error(*_, **__):
    if sentry_dsn:
        sentry_sdk.capture_exception()
    else:
        raise  # skipcq: PYL-E0704


@listener
async def on_command_error(ctx: Context, error: CommandError):
    if isinstance(error, CommandNotFound) and ctx.guild is not None and ctx.prefix == await get_prefix():
        messages = []
    elif isinstance(error, UserInputError):
        messages = await send_help(ctx, ctx.command)
    else:
        messages = [await ctx.send(embed=make_error(error))]

    add_to_error_cache(ctx.message, messages)


# fmt: off
load_cogs(
    bot,

    # # Administration
    PermissionsCog(),
    SettingsCog(),
    SudoCog(),

    # Moderation
    ModCog(),
    LoggingCog(),
    MessageCog(),
    MediaOnlyCog(),
    InvitesCog(),
    AutoModCog(),
    VerificationCog(),

    # Information
    BotInfoCog(info_icon="https://github.com/TheMorpheus407.png"),
    CodeblocksCog(),
    HeartbeatCog(),
    MetaQuestionCog(),
    ServerInfoCog(),

    # Integrations
    AdventOfCodeCog(),
    DiscordpyDocumentationCog(),
    RedditCog(),
    RunCodeCog(),

    BeTheProfessionalCog(),
    PollsCog(),
    ReactionPinCog(),
    ReactionRoleCog(),
    UtilsCog(),
    VoiceChannelCog(),
)
# fmt: on

bot.run(os.environ["TOKEN"])
