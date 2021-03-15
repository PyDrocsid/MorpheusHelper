import re
from typing import Optional, Union

from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from PyDrocsid.util import read_normal_message
from discord import Member, TextChannel, Guild, Message, Embed, PartialEmoji, Forbidden, File
from discord.ext.commands import ColorConverter, BadArgument, Bot

from colours import Colours
from permissions import PermissionLevel, Permission


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


async def get_prefix() -> str:
    return await Settings.get(str, "prefix", ".")


async def set_prefix(new_prefix: str):
    await Settings.set(str, "prefix", new_prefix)


async def check_wastebasket(
    message: Message, member: Member, emoji: PartialEmoji, footer: str, permission: Permission
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


async def get_message_cancel(bot: Bot, channel: TextChannel, member: Member) -> tuple[Optional[str], list[File]]:
    content, files = await read_normal_message(bot, channel, member)
    if content == translations.cancel:
        embed = Embed(title=translations.rule, colour=Colours.RuleCommands,
                        description=translations.msg_send_cancel)
        await channel.send(embed=embed)
        return None, []

    return content, files
