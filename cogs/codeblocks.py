from PyDrocsid.translations import translations
from discord import Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot

from colours import Colours


class CodeblocksCog(Cog, name="Codeblocks command"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="codeblocks", aliases=["codeblock", "code", "c"])
    async def codeblocks(self, ctx):
        await ctx.send(
            embed=Embed(
                title=translations.codeblocks_title,
                description=translations.codeblocks_description,
                colour=Colours.CodeBlocks,
            )
        )
