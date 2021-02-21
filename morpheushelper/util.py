import re
from typing import Optional, Union

from PyDrocsid.permission import BasePermission

from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from discord import Member, TextChannel, Guild, Message, Embed, PartialEmoji, Forbidden
from discord.ext.commands import ColorConverter, BadArgument

from colours import Colours
from permissions import PermissionLevel


class Color(ColorConverter):
    async def convert(self, ctx, argument: str) -> Optional[int]:
        try:
            return await super().convert(ctx, argument)
        except BadArgument:
            pass

        if not re.match(r"^[0-9a-fA-F]{6}$", argument):
            raise BadArgument(translations.invalid_color)
        return int(argument, 16)


def make_error(message) -> Embed:
    return Embed(title=translations.error, colour=Colours.error, description=str(message))


async def is_teamler(member: Member) -> bool:
    return await PermissionLevel.SUPPORTER.check_permissions(member)


async def send_to_changelog(guild: Guild, message: Union[str, Embed]):
    channel: Optional[TextChannel] = guild.get_channel(await Settings.get(int, "logging_changelog", -1))
    if channel is not None:
        if isinstance(message, str):
            embed = Embed(colour=Colours.changelog, description=message)
        else:
            embed = message
        await channel.send(embed=embed)


async def check_wastebasket(
    message: Message, member: Member, emoji: PartialEmoji, footer: str, permission: BasePermission
) -> Optional[int]:
    if emoji.name != name_to_emoji["wastebasket"]:
        return None

    for embed in message.embeds:
        if embed.footer.text == Embed.Empty:
            continue

        pattern = re.escape(footer).replace("\\{\\}", "{}").format(r".*?#\d{4}", r"(\d+)")
        if (match := re.match("^" + pattern + "$", embed.footer.text)) is None:
            continue

        author_id = int(match.group(1))
        if not (author_id == member.id or await permission.check_permissions(member)):
            try:
                await message.remove_reaction(emoji, member)
            except Forbidden:
                pass
            return None

        return author_id

    return None
