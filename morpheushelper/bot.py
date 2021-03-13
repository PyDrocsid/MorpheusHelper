from typing import Iterable

import sentry_sdk
from discord import Intents, Message
from discord.ext.commands import Bot, Context, CommandError, CommandNotFound, UserInputError

from PyDrocsid.cog import load_cogs
from PyDrocsid.command_edit import add_to_error_cache
from PyDrocsid.environment import TOKEN
from PyDrocsid.events import listener
from PyDrocsid.permission import PermissionDeniedError
from PyDrocsid.translations import t
from PyDrocsid.util import make_error
from cogs.custom import CustomBotInfoCog, CustomRolesCog
from cogs.library import *
from cogs.library.help.cog import send_help
from cogs.library.settings.cog import get_prefix


async def fetch_prefix(_, msg: Message) -> Iterable[str]:
    prefix = [await get_prefix(), f"<@!{bot.user.id}> ", f"<@{bot.user.id}> "]

    if msg.guild is None:
        prefix.append("")

    return prefix


bot = Bot(command_prefix=fetch_prefix, case_insensitive=True, intents=(Intents.all()))
bot.remove_command("help")


@listener
async def on_ready():
    print(f"\033[1m\033[36mLogged in as {bot.user}\033[0m")


@bot.event
async def on_error(*_, **__):
    sentry_sdk.capture_exception()
    raise  # skipcq: PYL-E0704


@listener
async def on_command_error(ctx: Context, error: CommandError):
    if isinstance(error, PermissionDeniedError):
        messages = [await ctx.send(embed=make_error(t.g.not_allowed))]
    elif isinstance(error, CommandNotFound) and ctx.guild is not None and ctx.prefix == await get_prefix():
        messages = []
    elif isinstance(error, UserInputError):
        messages = await send_help(ctx, ctx.command)
    else:
        messages = [await ctx.send(embed=make_error(error))]

    add_to_error_cache(ctx.message, messages)


# fmt: off
load_cogs(
    bot,

    # Administration
    PermissionsCog(),
    SettingsCog(),
    SudoCog(),

    # Moderation
    CustomRolesCog(),
    ModCog(),
    LoggingCog(),
    MessageCog(),
    MediaOnlyCog(),
    InvitesCog(),
    AutoModCog(),
    VerificationCog(),

    # Information
    CustomBotInfoCog(),
    CodeblocksCog(),
    HeartbeatCog(),
    HelpCog(),
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


def run():
    bot.run(TOKEN)
