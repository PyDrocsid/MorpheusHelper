import io
import re
from http.client import HTTPException
from typing import Optional, Union, Tuple, List

from discord import TextChannel, Message, File, Forbidden, Permissions, Embed, Color, Member
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from util import permission_level


class RulesCog(Cog, name="Rule Commands"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def read_normal_message(self, channel: TextChannel, author: Member) -> Tuple[str, List[File]]:
        msg: Message = await self.bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)
        files = []
        for attachment in msg.attachments:
            file = io.BytesIO()
            await attachment.save(file)
            files.append(File(file, filename=attachment.filename, spoiler=attachment.is_spoiler()))
        return msg.content, files

    @commands.group(name="send")
    @permission_level(1)
    @guild_only()
    async def send(self, ctx: Context):
        """
        send messages as the bot
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.send)

    @send.command(name="text")
    async def send_text(self, ctx: Context, channel: TextChannel):
        """
        send a normal message
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(
                "Message could not be sent because I don't have `send_messages` permission in this channel."
            )

        await ctx.send("Now send me the message!")
        content, files = await self.read_normal_message(ctx.channel, ctx.author)
        try:
            await channel.send(content=content, files=files)
        except (HTTPException, Forbidden):
            raise CommandError("Message could not be sent.")
        else:
            await ctx.send("Message has been sent successfully.")

    @send.command(name="embed")
    async def send_embed(self, ctx: Context, channel: TextChannel, color: Optional[Union[Color, str]] = None):
        """
        send an embed
        """

        if isinstance(color, str):
            if not re.match(r"^[0-9a-fA-F]{6}$", color):
                raise CommandError("Invalid color")
            else:
                color = int(color, 16)

        permissions: Permissions = channel.permissions_for(channel.guild.me)
        if not permissions.send_messages:
            raise CommandError(
                "Message could not be sent because I don't have `send_messages` permission in this channel."
            )
        elif not permissions.embed_links:
            raise CommandError(
                "Message could not be sent because I don't have `embed_links` permission in this channel."
            )

        await ctx.send("Send me the title of the embed!")
        title: str = (
            await self.bot.wait_for("message", check=lambda m: m.channel == ctx.channel and m.author == ctx.author)
        ).content
        await ctx.send("Ok, now send me the content of the embed!")
        content: str = (
            await self.bot.wait_for("message", check=lambda m: m.channel == ctx.channel and m.author == ctx.author)
        ).content

        try:
            embed = Embed(title=title, description=content)
            if color is not None:
                embed.colour = color
            await channel.send(embed=embed)
        except (HTTPException, Forbidden):
            raise CommandError("Message could not be sent.")
        else:
            await ctx.send("Message has been sent successfully.")

    @commands.group(name="edit")
    @permission_level(1)
    @guild_only()
    async def edit(self, ctx: Context):
        """
        edit messages sent by the bot
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.edit)

    @edit.command(name="text")
    async def edit_text(self, ctx: Context, message: Message):
        """
        edit a normal message
        """

        if message.author != self.bot.user:
            raise CommandError("This message cannot be edited because the bot is not the author of the message.")

        await ctx.send("Now send me the new message!")
        content, files = await self.read_normal_message(ctx.channel, ctx.author)
        await message.edit(content=content, files=files)
        await ctx.send("Message has been edited successfully.")
