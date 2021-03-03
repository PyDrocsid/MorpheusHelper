from discord import Member
from discord.embeds import Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot
from discord.ext.commands.context import Context
from PyDrocsid.async_thread import run_in_thread
from PyDrocsid.translations import translations
from wikipedia.exceptions import WikipediaException, DisambiguationError, PageError
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

        try:
            summary = await run_in_thread(wikipedia.summary, title)
            await ctx.send(embed=make_embed(title=title, content=summary, color=Colours.default,
                                            requested_by=ctx.author))

        # this error occurs when the topic searched for has not been found, but there are suggestions
        except DisambiguationError as not_found_err:
            await ctx.send(embed=make_embed(title=f"{title} was not found!", content=str(not_found_err),
                                            color=Colours.warning, requested_by=ctx.author))

        # this error occurs when the topic searched has not been found and there are no suggestions
        except PageError as not_not_found_error:
            await ctx.send(embed=make_embed(title=title, content=str(not_not_found_error), color=Colours.warning,
                                            requested_by=ctx.author))

        # WikipediaException is the base exception of all exceptions of the wikipedia module
        # if an error occurs that has not been caught above
        # it may mean that wikipedia hasn't responded correctly or not at all
        except WikipediaException:
            await ctx.send(
                embed=make_embed(title=title, content="Wikipedia is not available currently! Try again later.",
                                 color=Colours.warning, requested_by=ctx.author))
