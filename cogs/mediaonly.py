import re
from typing import Optional

import requests
from discord import Guild, TextChannel, Message
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError
from requests import RequestException

from database import run_in_thread, db
from models.mediaonly_channel import MediaOnlyChannel
from util import permission_level, check_access, send_to_changelog


class MediaOnlyCog(Cog, name="MediaOnly"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.author == self.bot.user:
            return
        if message.author.bot:
            return
        if await check_access(message.author):
            return
        if await run_in_thread(db.get, MediaOnlyChannel, message.channel.id) is None:
            return
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
                return

        channel: TextChannel = message.channel
        await message.delete()
        await channel.send(
            f"{message.author.mention} Only pictures are allowed in this channel. "
            "For conversations please use the channels designated for this purpose.",
            delete_after=30,
        )
        await send_to_changelog(
            message.guild,
            f"Deleted a message of {message.author.mention} in media only channel {message.channel.mention} "
            f"because it did not contain an image.",
        )

    @commands.group(aliases=["mo"])
    @permission_level(1)
    @guild_only()
    async def mediaonly(self, ctx: Context):
        """
        manage MediaOnly
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.mediaonly)

    @mediaonly.command(name="list")
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
            await ctx.send("Media only channels:\n" + "\n".join(out))
        else:
            await ctx.send("No media only channels.")

    @mediaonly.command(name="add")
    async def add_channel(self, ctx: Context, channel: TextChannel):
        """
        add a media only channel
        """

        if await run_in_thread(db.get, MediaOnlyChannel, channel.id) is not None:
            raise CommandError("Channel is already a media only channel.")

        await run_in_thread(MediaOnlyChannel.create, channel.id)
        await ctx.send("Channel is now a media only channel.")
        await send_to_changelog(ctx.guild, f"Channel {channel.mention} is now a media only channel.")

    @mediaonly.command(name="remove")
    async def remove_channel(self, ctx: Context, channel: TextChannel):
        """
        remove a media only channel
        """

        if (row := await run_in_thread(db.get, MediaOnlyChannel, channel.id)) is None:
            raise CommandError("Channel is not a media only channel.")

        await run_in_thread(db.delete, row)
        await ctx.send("Channel is not a media only channel anymore.")
        await send_to_changelog(ctx.guild, f"Channel {channel.mention} is not a media only channel anymore.")
