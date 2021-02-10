from discord.embeds import Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord.ext.commands.context import Context
from wikipedia.exceptions import WikipediaException
from colours import Colours

import wikipedia


def make_embed(title: str, content: str, color) -> Embed:
    embed = Embed(title=title, description=content, color=color)
    return embed


# Note: wikiepdia allows bots, but only bots that are responsible (not going too fast).
class WikipediaCog(Cog, name="Wikipedia"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(aliases=["wiki", "summary", "wk", "sum"])
    @commands.cooldown(5, 10, commands.BucketType.user)
    async def wikipedia(self, ctx: Context, *, title: str):
        """
        display wikipedia summary about a topic 
        """
        try:
            await ctx.send(embed=make_embed(title=title, content=wikipedia.summary(title), color=Colours.default))

        except WikipediaException as e:
            await ctx.send(embed=make_embed(title="Not found!", content=str(e), color=Colours.warning))
