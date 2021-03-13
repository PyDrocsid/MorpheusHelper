from typing import Optional

from discord import Embed
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import snowflake_time

from PyDrocsid.cog import Cog
from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t
from PyDrocsid.util import measure_latency
from .colors import Colors
from ..contributor import Contributor

tg = t.g
t = t.utils


class UtilsCog(Cog, name="Utils"):
    CONTRIBUTORS = [Contributor.Defelo]
    PERMISSIONS = BasePermission

    @commands.command()
    async def ping(self, ctx: Context):
        """
        display bot latency
        """

        latency: Optional[float] = measure_latency()
        embed = Embed(title=t.pong, colour=Colors.ping)
        if latency is not None:
            embed.description = t.pong_latency(latency * 1000)
        await ctx.send(embed=embed)

    @commands.command(aliases=["sf", "time"])
    async def snowflake(self, ctx: Context, arg: int):
        """
        display snowflake timestamp
        """

        await ctx.send(snowflake_time(arg).strftime("%d.%m.%Y %H:%M:%S"))
