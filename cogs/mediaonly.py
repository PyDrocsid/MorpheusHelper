import re
from typing import Optional

import requests
from discord import Guild, TextChannel, Message
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError
from requests import RequestException

from database import run_in_thread, db
from models.mediaonly_channel import MediaOnlyChannel
from translations import translations
from util import permission_level, check_permissions, send_to_changelog, MODERATOR


class MediaOnlyCog(Cog, name="MediaOnly"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_message(self, message: Message) -> bool:
        if message.guild is None or message.author.bot or await check_permissions(message.author, MODERATOR):
            return True
        if await run_in_thread(db.get, MediaOnlyChannel, message.channel.id) is None:
            return True

        urls = [(att.url,) for att in message.attachments]
        urls += re.findall(r"(https?://([a-zA-Z0-9\-_~]+\.)+[a-zA-Z0-9\-_~]+(/\S*)?)", message.content)
        for url, *_ in urls:
            try:
                mime = requests.head(url).headers["Content-type"]
            except (KeyError, AttributeError, RequestException, UnicodeError, ConnectionError):
                break
            if not mime.startswith("image/"):
                break
        else:
            if urls:
                return True

        channel: TextChannel = message.channel
        await message.delete()
        await channel.send(translations.f_deleted_nomedia(message.author.mention), delete_after=30)
        await send_to_changelog(
            message.guild, translations.f_log_deleted_nomedia(message.author.mention, message.channel.mention)
        )

        return False

    @commands.group(aliases=["mo"])
    @permission_level(MODERATOR)
    @guild_only()
    async def mediaonly(self, ctx: Context):
        """
        manage MediaOnly
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.mediaonly)

    @mediaonly.command(name="list", aliases=["l", "?"])
    async def list_channels(self, ctx: Context):
        """
        list media only channels
        """

        guild: Guild = ctx.guild
        out = []
        for channel in await run_in_thread(db.all, MediaOnlyChannel):
            text_channel: Optional[TextChannel] = guild.get_channel(channel.channel)
            if text_channel is not None:
                out.append(f"- {text_channel.mention}")
            else:
                await run_in_thread(db.delete, channel)
        if out:
            await ctx.send(translations.media_only_channels_header + "\n" + "\n".join(out))
        else:
            await ctx.send(translations.no_media_only_channels)

    @mediaonly.command(name="add", aliases=["a", "+"])
    async def add_channel(self, ctx: Context, channel: TextChannel):
        """
        add a media only channel
        """

        if await run_in_thread(db.get, MediaOnlyChannel, channel.id) is not None:
            raise CommandError(translations.channel_already_media_only)
        if not channel.permissions_for(channel.guild.me).manage_messages:
            raise CommandError(translations.media_only_not_changed_no_permissions)

        await run_in_thread(MediaOnlyChannel.create, channel.id)
        await ctx.send(translations.channel_now_media_only)
        await send_to_changelog(ctx.guild, translations.f_log_channel_now_media_only(channel.mention))

    @mediaonly.command(name="remove", aliases=["del", "r", "d", "-"])
    async def remove_channel(self, ctx: Context, channel: TextChannel):
        """
        remove a media only channel
        """

        if (row := await run_in_thread(db.get, MediaOnlyChannel, channel.id)) is None:
            raise CommandError(translations.channel_not_media_only)

        await run_in_thread(db.delete, row)
        await ctx.send(translations.channel_not_media_only_anymore)
        await send_to_changelog(ctx.guild, translations.f_log_channel_not_media_only_anymore(channel.mention))
