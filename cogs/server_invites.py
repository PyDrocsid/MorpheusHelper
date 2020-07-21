from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context

from util import send_help


class ServerInvitesCog(Cog, name="Server invites"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(name="serverinvites", aliases=["si"])
    @guild_only()
    async def server_invites(self, ctx: Context):
        """
        manage all created invites for this server
        """

        if ctx.invoked_subcommand is None:
            await send_help(ctx, self.server_invites)
