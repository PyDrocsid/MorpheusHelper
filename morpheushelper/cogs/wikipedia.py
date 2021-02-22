from discord import Member
from discord.embeds import Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord.ext.commands.context import Context
from PyDrocsid.async_thread import run_in_thread
from PyDrocsid.translations import translations
from wikipedia.exceptions import WikipediaException
from colours import Colours
import wikipedia


def make_embed(title: str, content: str, color, requested_by: Member) -> Embed:
    embed = Embed(title=title, description=content, color=color)
    embed.set_footer(text=translations.f_requested_by(requested_by, requested_by.id), icon_url=requested_by.avatar_url)
    return embed


# Note: wikipedia allows bots, but only bots that are responsible (not going too fast).
class WikipediaCog(Cog, name="Wikipedia"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(aliases=["wiki", "summary", "wk", "sum"])
    @commands.cooldown(5, 10, commands.BucketType.user)
    async def wikipedia(self, ctx: Context, *, title: str):
        """
        display wikipedia summary about a topic
        """
        # workaround because the run_in_thread function doesn't support arguments
        def inner():
            try:
                return wikipedia.summary(title)
            except WikipediaException as e:
                return {"Error": str(e)}

            except:
                return "Wikipedia cog is not working currently!"

        summary = await run_in_thread(inner)

        # if the type of the return value is dict, this mean that the wikipedia module didn't find
        # the topic the user searched for
        if type(summary) is dict:
            await ctx.send(embed=make_embed(title=f"{title} was not found!", content=summary["Error"],
                                            color=Colours.warning,
                                            requested_by=ctx.author))
        else:
            await ctx.send(embed=make_embed(title=title, content=summary, color=Colours.default,
                                            requested_by=ctx.author))
