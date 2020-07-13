import re
from http.client import HTTPException
from typing import Optional, Union

from discord import TextChannel, Message, Forbidden, Permissions, Color
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from permission import Permission
from translations import translations
from util import permission_level, read_normal_message, read_embed, read_complete_message, send_help


class RulesCog(Cog, name="Rule Commands"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(name="send")
    @permission_level(Permission.send)
    @guild_only()
    async def send(self, ctx: Context):
        """
        send messages as the bot
        """

        if ctx.invoked_subcommand is None:
            await send_help(ctx, self.send)

    @send.command(name="text", aliases=["t"])
    async def send_text(self, ctx: Context, channel: TextChannel):
        """
        send a normal message
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(translations.could_not_send_message)

        await ctx.send(translations.send_message)
        content, files = await read_normal_message(self.bot, ctx.channel, ctx.author)
        try:
            await channel.send(content=content, files=files)
        except (HTTPException, Forbidden):
            raise CommandError(translations.msg_could_not_be_sent)
        else:
            await ctx.send(translations.msg_sent)

    @send.command(name="embed", aliases=["e"])
    async def send_embed(self, ctx: Context, channel: TextChannel, color: Optional[Union[Color, str]] = None):
        """
        send an embed
        """

        if isinstance(color, str):
            if not re.match(r"^[0-9a-fA-F]{6}$", color):
                raise CommandError(translations.invalid_color)
            color = int(color, 16)

        permissions: Permissions = channel.permissions_for(channel.guild.me)
        if not permissions.send_messages:
            raise CommandError(translations.could_not_send_message)
        if not permissions.embed_links:
            raise CommandError(translations.could_not_send_embed)

        embed = await read_embed(self.bot, ctx.channel, ctx.author)
        if color is not None:
            embed.colour = color
        try:
            await channel.send(embed=embed)
        except (HTTPException, Forbidden):
            raise CommandError(translations.msg_could_not_be_sent)
        else:
            await ctx.send(translations.msg_sent)

    @send.command(name="copy", aliases=["c"])
    async def send_copy(self, ctx: Context, channel: TextChannel, message: Message):
        """
        copy a message (specify message link)
        """

        content, files, embed = await read_complete_message(message)
        try:
            await channel.send(content=content, embed=embed, files=files)
        except (HTTPException, Forbidden):
            raise CommandError(translations.msg_could_not_be_sent)
        else:
            await ctx.send(translations.msg_sent)

    @commands.group(name="edit")
    @permission_level(Permission.edit)
    @guild_only()
    async def edit(self, ctx: Context):
        """
        edit messages sent by the bot
        """

        if ctx.invoked_subcommand is None:
            await send_help(ctx, self.edit)

    @edit.command(name="text", aliases=["t"])
    async def edit_text(self, ctx: Context, message: Message):
        """
        edit a normal message (specify message link)
        """

        if message.author != self.bot.user:
            raise CommandError(translations.could_not_edit)

        await ctx.send(translations.send_new_message)
        content, files = await read_normal_message(self.bot, ctx.channel, ctx.author)
        if files:
            raise CommandError(translations.cannot_edit_files)
        await message.edit(content=content, embed=None)
        await ctx.send(translations.msg_edited)

    @edit.command(name="embed", aliases=["e"])
    async def edit_embed(self, ctx: Context, message: Message, color: Optional[Union[Color, str]] = None):
        """
        edit an embed (specify message link)
        """

        if message.author != self.bot.user:
            raise CommandError(translations.could_not_edit)

        if isinstance(color, str):
            if not re.match(r"^[0-9a-fA-F]{6}$", color):
                raise CommandError(translations.invalid_color)
            color = int(color, 16)

        embed = await read_embed(self.bot, ctx.channel, ctx.author)
        if color is not None:
            embed.colour = color
        await message.edit(content=None, files=[], embed=embed)
        await ctx.send(translations.msg_edited)

    @edit.command(name="copy", aliases=["c"])
    async def edit_copy(self, ctx: Context, message: Message, source: Message):
        """
        copy a message into another message (specify message links)
        """

        if message.author != self.bot.user:
            raise CommandError(translations.could_not_edit)

        content, files, embed = await read_complete_message(source)
        if files:
            raise CommandError(translations.cannot_edit_files)
        await message.edit(content=content, embed=embed)
        await ctx.send(translations.msg_edited)

    @commands.command(name="delete")
    @permission_level(Permission.delete)
    @guild_only()
    async def delete(self, ctx: Context, message: Message):
        """
        delete a message (specify message link)
        """

        if message.guild is None:
            raise CommandError(translations.cannot_delete_dm)

        channel: TextChannel = message.channel
        permissions: Permissions = channel.permissions_for(message.guild.me)
        if message.author != self.bot.user and not permissions.manage_messages:
            raise CommandError(translations.could_not_delete)

        await message.delete()
        await ctx.send(translations.msg_deleted)
