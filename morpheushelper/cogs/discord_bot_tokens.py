from PyDrocsid.translations import translations
from discord import Embed, Member, Message, Forbidden, NotFound, HTTPException
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, guild_only

from colours import Colours
import re


def make_embed(requested_by: Member) -> Embed:
    embed = Embed(title=translations.discordbottoken_title, colour=Colours.DiscordBotToken)
    embed.description = translations.discordbottoken_description
    embed.set_footer(text=translations.f_requested_by(requested_by, requested_by.id), icon_url=requested_by.avatar_url)
    return embed


class DiscordBotTokenCog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(aliases=["dctoken"])
    @guild_only()
    async def token(self, ctx: Context):
        """
        display information about discord bot toktens
        """

        await ctx.send(embed=make_embed(ctx.author))
        try:
            await ctx.message.delete()
        except (Forbidden, NotFound, HTTPException):
            pass

    @guild_only()
    async def on_message(self, msg: Message):
        """
        deletes a message if it contains a discord bot token
        """

        if tokens := re.findall(r'([A-Za-z\d]{24}\.[A-Za-z\d]{6}\.[A-Za-z\d\-\_]{27})', msg.content):
            await msg.channel.send(embed=make_embed(msg.author))
            try:
                await msg.delete()
            except (Forbidden, NotFound, HTTPException):
                pass
            escaped_content = msg.content
            for token in tokens:
                escaped_content = escaped_content.replace(token, "\\*\\*\\*")
            escaped_content = escaped_content.replace("`", "\\`")
            if escaped_content != "***":
                await msg.author.send(f'Your message was: \n{escaped_content}\n*I replaced the Token*')
