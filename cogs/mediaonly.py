import re
from typing import Optional

import requests
from discord import Guild, TextChannel, Message, Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError, UserInputError
from requests import RequestException

from database import run_in_thread, db
from models.mediaonly_channel import MediaOnlyChannel
from permission import Permission
from translations import translations
from util import permission_level, check_permissions, send_to_changelog, send_long_embed


class MediaOnlyCog(Cog, name="MediaOnly"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_message(self, message: Message) -> bool:
        if message.guild is None or message.author.bot or await check_permissions(message.author, Permission.mo_bypass):
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
        embed = Embed(title=translations.mediaonly, description=translations.deleted_nomedia,
                      colour=0xCF0606)
        await channel.send(content=message.author.mention, embed=embed, delete_after=30)
        await send_to_changelog(
            message.guild, translations.f_log_deleted_nomedia(message.author.mention, message.channel.mention)
        )

        return False

    @commands.group(aliases=["mo"])
    @permission_level(Permission.mo_manage)
    @guild_only()
    async def mediaonly(self, ctx: Context):
        """
        manage MediaOnly
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

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
                out.append(f":small_orange_diamond: {text_channel.mention}")
            else:
                await run_in_thread(db.delete, channel)
        embed = Embed(title=translations.media_only_channels_header, colour=0xCF0606)
        if out:
            embed.colour = 0xe4e800
            embed.description = "\n".join(out)
            await send_long_embed(ctx, embed)
        else:
            embed.description = translations.no_media_only_channels
            await ctx.send(embed=embed)

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
        embed = Embed(title=translations.media_only_channels_header, description=translations.channel_now_media_only,
                      colour=0xe4e800)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_channel_now_media_only(channel.mention))

    @mediaonly.command(name="remove", aliases=["del", "r", "d", "-"])
    async def remove_channel(self, ctx: Context, channel: TextChannel):
        """
        remove a media only channel
        """

        if (row := await run_in_thread(db.get, MediaOnlyChannel, channel.id)) is None:
            raise CommandError(translations.channel_not_media_only)

        await run_in_thread(db.delete, row)
        embed = Embed(title=translations.media_only_channels_header,
                      description=translations.channel_not_media_only_anymore,
                      colour=0xe4e800)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_channel_not_media_only_anymore(channel.mention))
