import io
from http.client import HTTPException

from discord import TextChannel, Message, File, Forbidden
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from util import permission_level


class RulesCog(Cog, name="Rule Commands"):
    def __init__(self, bot: Bot):
        self.bot = bot

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
        msg: Message = await self.bot.wait_for(
            "message", check=lambda m: m.channel == ctx.channel and m.author == ctx.author
        )
        files = []
        for attachment in msg.attachments:
            file = io.BytesIO()
            await attachment.save(file)
            files.append(File(file, filename=attachment.filename, spoiler=attachment.is_spoiler()))
        try:
            await channel.send(content=msg.content, files=files)
        except (HTTPException, Forbidden):
            raise CommandError("Message could not be sent.")
        else:
            await ctx.send("Message has been sent successfully.")
