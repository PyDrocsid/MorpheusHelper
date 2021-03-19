from http.client import HTTPException
from typing import Optional

from discord import TextChannel, Message, Forbidden, Permissions, Embed, Member, File
from discord.ext import commands
from discord.ext.commands import guild_only, Context, CommandError, UserInputError

from PyDrocsid.cog import Cog
from PyDrocsid.translations import t
from PyDrocsid.util import Color
from PyDrocsid.util import read_normal_message, read_complete_message
from .colors import Colors
from .permissions import MessagePermission
from cogs.library.contributor import Contributor

tg = t.g
t = t.message


class MessageCog(Cog, name="Message Commands"):
    CONTRIBUTORS = [Contributor.Defelo, Contributor.wolflu]
    PERMISSIONS = MessagePermission

    @staticmethod
    async def get_message_cancel(bot: Bot, channel: TextChannel, member: Member) -> tuple[Optional[str], list[File]]:
        content, files = await read_normal_message(bot, channel, member)
        if content == translations.cancel:
            embed = Embed(
                title=translations.rule, colour=Colours.RuleCommands, description=translations.msg_send_cancel
            )
            await channel.send(embed=embed)
            return None, []

        return content, files

    @commands.group()
    @MessagePermission.send.check
    @guild_only()
    async def send(self, ctx: Context):
        """
        send messages as the bot
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @send.command(name="text", aliases=["t"])
    async def send_text(self, ctx: Context, channel: TextChannel):
        """
        send a normal message
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(t.could_not_send_message)

        embed = Embed(
            title=t.messages,
            colour=Colors.MessageCommands,
            description=t.send_message(t.cancel),
        )
        await ctx.send(embed=embed)
        content, files = await self.get_message_cancel(self.bot, ctx.channel, ctx.author)

        if content is None:
            return

        try:
            await channel.send(content=content, files=files)
        except (HTTPException, Forbidden):
            raise CommandError(t.msg_could_not_be_sent)
        else:
            embed.description = t.msg_sent
            await ctx.send(embed=embed)

    @send.command(name="embed", aliases=["e"])
    async def send_embed(self, ctx: Context, channel: TextChannel, color: Optional[Color] = None):
        """
        send an embed
        """

        permissions: Permissions = channel.permissions_for(channel.guild.me)
        if not permissions.send_messages:
            raise CommandError(t.could_not_send_message)
        if not permissions.embed_links:
            raise CommandError(t.could_not_send_embed)

        embed = Embed(
            title=t.messages,
            colour=Colors.MessageCommands,
            description=t.send_embed_title(t.cancel),
        )
        await ctx.send(embed=embed)
        title, _ = await self.get_message_cancel(self.bot, ctx.channel, ctx.author)
        if title is None:
            return
        if len(title) > 256:
            raise CommandError(t.title_too_long)

        embed.description = t.send_embed_content(t.cancel)
        await ctx.send(embed=embed)
        content, files = await self.get_message_cancel(self.bot, ctx.channel, ctx.author)

        if content is None:
            return

        send_embed = Embed(title=title, description=content)

        if files and any(files[0].filename.lower().endswith(ext) for ext in ["jpg", "jpeg", "png", "gif"]):
            send_embed.set_image(url="attachment://" + files[0].filename)

        if color is not None:
            send_embed.colour = color

        try:
            await channel.send(embed=send_embed, files=files)
        except (HTTPException, Forbidden):
            raise CommandError(t.msg_could_not_be_sent)
        else:
            embed.description = t.msg_sent
            await ctx.send(embed=embed)

    @send.command(name="copy", aliases=["c"])
    async def send_copy(self, ctx: Context, channel: TextChannel, message: Message):
        """
        copy a message (specify message link)
        """

        content, files, embed = await read_complete_message(message)
        try:
            await channel.send(content=content, embed=embed, files=files)
        except (HTTPException, Forbidden):
            raise CommandError(t.msg_could_not_be_sent)
        else:
            embed = Embed(title=t.messages, colour=Colors.MessageCommands, description=t.msg_sent)
            await ctx.send(embed=embed)

    @commands.group()
    @MessagePermission.edit.check
    @guild_only()
    async def edit(self, ctx: Context):
        """
        edit messages sent by the bot
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @edit.command(name="text", aliases=["t"])
    async def edit_text(self, ctx: Context, message: Message):
        """
        edit a normal message (specify message link)
        """

        if message.author != self.bot.user:
            raise CommandError(t.could_not_edit)

        embed = Embed(
            title=t.messages,
            colour=Colors.MessageCommands,
            description=t.send_new_message(t.cancel),
        )
        await ctx.send(embed=embed)
        content, files = await self.get_message_cancel(self.bot, ctx.channel, ctx.author)

        if content is None:
            return

        if files:
            raise CommandError(t.cannot_edit_files)

        await message.edit(content=content, embed=None)
        embed.description = t.msg_edited
        await ctx.send(embed=embed)

    @edit.command(name="embed", aliases=["e"])
    async def edit_embed(self, ctx: Context, message: Message, color: Optional[Color] = None):
        """
        edit an embed (specify message link)
        """

        if message.author != self.bot.user:
            raise CommandError(t.could_not_edit)

        embed = Embed(
            title=t.messages,
            colour=Colors.MessageCommands,
            description=t.send_embed_title(t.cancel),
        )
        await ctx.send(embed=embed)
        title, _ = await self.get_message_cancel(self.bot, ctx.channel, ctx.author)

        if title is None:
            return
        if len(title) > 256:
            raise CommandError(t.title_too_long)

        embed.description = t.send_embed_content(t.cancel)
        await ctx.send(embed=embed)
        content, _ = await self.get_message_cancel(self.bot, ctx.channel, ctx.author)

        if content is None:
            return

        send_embed = Embed(title=title, description=content)

        if color is not None:
            send_embed.colour = color

        await message.edit(content=None, files=[], embed=send_embed)
        embed.description = t.msg_edited
        await ctx.send(embed=embed)

    @edit.command(name="copy", aliases=["c"])
    async def edit_copy(self, ctx: Context, message: Message, source: Message):
        """
        copy a message into another message (specify message links)
        """

        if message.author != self.bot.user:
            raise CommandError(t.could_not_edit)

        content, files, embed = await read_complete_message(source)
        if files:
            raise CommandError(t.cannot_edit_files)
        await message.edit(content=content, embed=embed)
        embed = Embed(title=t.messages, colour=Colors.MessageCommands, description=t.msg_edited)
        await ctx.send(embed=embed)

    @commands.command()
    @MessagePermission.delete.check
    @guild_only()
    async def delete(self, ctx: Context, message: Message):
        """
        delete a message (specify message link)
        """

        if message.guild is None:
            raise CommandError(t.cannot_delete_dm)

        channel: TextChannel = message.channel
        permissions: Permissions = channel.permissions_for(message.guild.me)
        if message.author != self.bot.user and not permissions.manage_messages:
            raise CommandError(t.could_not_delete)

        await message.delete()
        embed = Embed(title=t.messages, colour=Colors.MessageCommands, description=t.msg_deleted)
        await ctx.send(embed=embed)
