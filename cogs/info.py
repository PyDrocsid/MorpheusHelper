from discord import Embed, Guild, Status
from discord import Role
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context
from discord.utils import get

from database import run_in_thread, db
from models.btp_role import BTPRole


class InfoCog(Cog, name="Server Information"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="server")
    @guild_only()
    async def server(self, ctx: Context):
        """
        displays information about this discord server
        """

        guild: Guild = ctx.guild
        embed = Embed(title=guild.name, description="Information about this Discord Server", color=0x005180)
        embed.set_thumbnail(url=guild.icon_url)
        created = guild.created_at.date()
        embed.add_field(name="Creation Date", value=f"{created.day}.{created.month}.{created.year}")
        online_count = sum(m.status != Status.offline for m in guild.members)
        embed.add_field(name=f"{guild.member_count} Members", value=f"{online_count} online")
        embed.add_field(name="Owner", value=guild.owner.mention)

        role: Role
        if (role := get(guild.roles, name="Admin")) is not None and role.members:
            embed.add_field(
                name=f"{len(role.members)} Admins",
                value="\n".join(":small_orange_diamond: " + m.mention for m in role.members),
            )
        if (role := get(guild.roles, name="Moderator")) is not None and role.members:
            embed.add_field(
                name=f"{len(role.members)} Moderators",
                value="\n".join(":small_orange_diamond: " + m.mention for m in role.members),
            )
        if (role := get(guild.roles, name="Supporter")) is not None and role.members:
            embed.add_field(
                name=f"{len(role.members)} Supporters",
                value="\n".join(":small_orange_diamond: " + m.mention for m in role.members),
            )

        bots = [m.mention for m in guild.members if m.bot]
        embed.add_field(name=f"{len(bots)} Bots", value="\n".join(":small_orange_diamond: " + b for b in bots))
        embed.add_field(name="Topics", value=f"{len(await run_in_thread(db.all, BTPRole))} topics registered")

        await ctx.send(embed=embed)
