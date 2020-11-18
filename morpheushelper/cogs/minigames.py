import random

from PyDrocsid.translations import translations
from PyDrocsid.util import send_long_embed
from discord import Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, UserInputError, CommandError

from colours import Colours


class MiniGamesCog(Cog, name="Mini Games Cog"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group()
    @guild_only()
    async def games(self, ctx: Context):
        """
        start funny mini games
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        embed = Embed(
            title=translations.mini_games_title,
            description=translations.mini_games_description
            + ":small_orange_diamond: "
            + "\n :small_orange_diamond: ".join(g for g in translations.mini_games),
            colour=Colours.MiniGamesCog,
        )
        await ctx.send(embed=embed)

    @games.group(name="minesweeper", aliases=["ms"])
    async def minesweeper(self, ctx: Context, width: int = 10, height: int = 10, bombs: int = 20):
        """
        start a minesweeper game
        """

        if width > 14 or height > 14:
            raise CommandError(translations.f_to_big_ms_field(14, 14))
        if bombs > (maximum := (width - 1) * (height - 1)):
            raise CommandError(translations.f_to_many_bombs(width, height, maximum))

        b = set()
        while len(b) < bombs:
            b.add((random.randint(0, width - 1), random.randint(0, height - 1)))

        f = [[0 for _ in range(width)] for _ in range(height)]

        def inc(ax, ay):
            if 0 <= ax < width and 0 <= ay < height and f[ay][ax] != -1:
                f[ay][ax] += 1

        for x, y in b:
            f[y][x] = -1
            inc(x - 1, y - 1)
            inc(x, y - 1)
            inc(x + 1, y - 1)
            inc(x - 1, y)
            inc(x + 1, y)
            inc(x - 1, y + 1)
            inc(x, y + 1)
            inc(x + 1, y + 1)

        game_field = ""
        for line in f:
            game_field += (
                "".join(
                    "||:"
                    + ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "boom"][int(x)]
                    + ":||"
                    for x in line
                )
                + "\n"
            )

        embed = Embed(
            title=translations.f_ms_title(width, height, bombs), description=game_field, colour=Colours.MiniGamesCog
        )

        await send_long_embed(ctx, embed)
