import io
import re
from typing import Optional, Tuple, List

from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from discord import Member, TextChannel, Guild, Message, File, Embed, Attachment, PartialEmoji, Forbidden
from discord.ext.commands import Bot, CommandError

from permissions import PermissionLevel, Permission


def make_error(message) -> str:
    return f":x: Error: {message}"


async def is_teamler(member: Member) -> bool:
    return await PermissionLevel.SUPPORTER.check_permissions(member)


async def send_to_changelog(guild: Guild, message: str):
    channel: Optional[TextChannel] = guild.get_channel(await Settings.get(int, "logging_changelog", -1))
    if channel is not None:
        await channel.send(message)


async def get_prefix() -> str:
    return await Settings.get(str, "prefix", ".")


async def set_prefix(new_prefix: str):
    await Settings.set(str, "prefix", new_prefix)


async def attachment_to_file(attachment: Attachment) -> File:
    file = io.BytesIO()
    await attachment.save(file)
    return File(file, filename=attachment.filename, spoiler=attachment.is_spoiler())


async def read_normal_message(bot: Bot, channel: TextChannel, author: Member) -> Tuple[str, List[File]]:
    msg: Message = await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)
    return msg.content, [await attachment_to_file(attachment) for attachment in msg.attachments]


async def read_embed(bot: Bot, channel: TextChannel, author: Member) -> Embed:
    await channel.send(translations.send_embed_title)
    title: str = (await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)).content
    if len(title) > 256:
        raise CommandError(translations.title_too_long)
    await channel.send(translations.send_embed_content)
    content: str = (await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)).content
    return Embed(title=title, description=content)


async def read_complete_message(message: Message) -> Tuple[str, List[File], Optional[Embed]]:
    for embed in message.embeds:
        if embed.type == "rich":
            break
    else:
        embed = None

    return message.content, [await attachment_to_file(attachment) for attachment in message.attachments], embed


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
