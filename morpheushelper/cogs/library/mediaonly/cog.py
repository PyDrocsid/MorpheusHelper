import re
from typing import Optional

import requests
from discord import Guild, TextChannel, Message, Embed
from discord.ext import commands
from discord.ext.commands import guild_only, Context, CommandError, UserInputError
from requests import RequestException

from PyDrocsid.cog import Cog
from PyDrocsid.database import db_thread, db
from PyDrocsid.events import StopEventHandling
from PyDrocsid.translations import t
from PyDrocsid.util import send_long_embed
from .colors import Colors
from .models import MediaOnlyChannel
from .permissions import MediaOnlyPermission
from ..contributor import Contributor
from ..logging import send_to_changelog

tg = t.g
t = t.mediaonly


class MediaOnlyCog(Cog, name="MediaOnly"):
    CONTRIBUTORS = [Contributor.Defelo, Contributor.wolflu]
    PERMISSIONS = MediaOnlyPermission

    async def on_message(self, message: Message):
        if (
            message.guild is None
            or message.author.bot
            or await MediaOnlyPermission.mo_bypass.check_permissions(message.author)
        ):
            return
        if await db_thread(db.get, MediaOnlyChannel, message.channel.id) is None:
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
        embed = Embed(title=t.mediaonly, description=t.deleted_nomedia, colour=Colors.error)
        await channel.send(content=message.author.mention, embed=embed, delete_after=30)
        await send_to_changelog(message.guild, t.log_deleted_nomedia(message.author.mention, message.channel.mention))
        raise StopEventHandling

    @commands.group(aliases=["mo"])
    @MediaOnlyPermission.mo_manage.check
    @guild_only()
    async def mediaonly(self, ctx: Context):
        """
        manage MediaOnly
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @mediaonly.command(name="list", aliases=["l", "?"])
    async def mediaonly_list(self, ctx: Context):
        """
        list media only channels
        """

        guild: Guild = ctx.guild
        out = []
        for channel in await db_thread(db.all, MediaOnlyChannel):
            text_channel: Optional[TextChannel] = guild.get_channel(channel.channel)
            if text_channel is not None:
                out.append(f":small_orange_diamond: {text_channel.mention}")
            else:
                await db_thread(db.delete, channel)
        embed = Embed(title=t.media_only_channels_header, colour=Colors.error)
        if out:
            embed.colour = Colors.MediaOnly
            embed.description = "\n".join(out)
            await send_long_embed(ctx, embed)
        else:
            embed.description = t.no_media_only_channels
            await ctx.send(embed=embed)

    @mediaonly.command(name="add", aliases=["a", "+"])
    async def mediaonly_add(self, ctx: Context, channel: TextChannel):
        """
        add a media only channel
        """

        if await db_thread(db.get, MediaOnlyChannel, channel.id) is not None:
            raise CommandError(t.channel_already_media_only)
        if not channel.permissions_for(channel.guild.me).manage_messages:
            raise CommandError(t.media_only_not_changed_no_permissions)

        await db_thread(MediaOnlyChannel.create, channel.id)
        embed = Embed(
            title=t.media_only_channels_header,
            description=t.channel_now_media_only,
            colour=Colors.MediaOnly,
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, t.log_channel_now_media_only(channel.mention))

    @mediaonly.command(name="remove", aliases=["del", "r", "d", "-"])
    async def mediaonly_remove(self, ctx: Context, channel: TextChannel):
        """
        remove a media only channel
        """

        if (row := await db_thread(db.get, MediaOnlyChannel, channel.id)) is None:
            raise CommandError(t.channel_not_media_only)

        await db_thread(db.delete, row)
        embed = Embed(
            title=t.media_only_channels_header,
            description=t.channel_not_media_only_anymore,
            colour=Colors.MediaOnly,
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, t.log_channel_not_media_only_anymore(channel.mention))
