from typing import Optional

from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from discord import Member, TextChannel, Guild, Embed

from colours import Colours
from permissions import PermissionLevel


def make_error(message) -> Embed:
    return Embed(title=translations.error, colour=Colours.error, description=translations.f_error_string(message))


async def is_teamler(member: Member) -> bool:
    return await PermissionLevel.SUPPORTER.check_permissions(member)


async def send_to_changelog(guild: Guild, message: str):
    channel: Optional[TextChannel] = guild.get_channel(await Settings.get(int, "logging_changelog", -1))
    if channel is not None:
        embed = Embed(title=Embed.Empty, colour=Colours.changelog, description=message)
        await channel.send(embed=embed)


async def get_prefix() -> str:
    return await Settings.get(str, "prefix", ".")


async def set_prefix(new_prefix: str):
    await Settings.set(str, "prefix", new_prefix)
