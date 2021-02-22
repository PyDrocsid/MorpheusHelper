import re
from typing import Optional

from discord import Member, Message, Embed, PartialEmoji, Forbidden

from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.permission import BasePermission
from permissions import PermissionLevel


async def is_teamler(member: Member) -> bool:
    return await PermissionLevel.SUPPORTER.check_permissions(member)


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
