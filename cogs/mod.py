from typing import Optional

from discord import Role, Guild
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context

from database import run_in_thread
from models.settings import Settings
from translations import translations
from util import permission_level, ADMINISTRATOR


class ModCog(Cog, name="Mod Tools"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(name="mod")
    @permission_level(ADMINISTRATOR)
    @guild_only()
    async def mod(self, ctx: Context):
        """
        mod tools
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(ModCog.mod)

    @mod.command(name="administrator", aliases=["admin", "a"])
    async def administrator(self, ctx: Context, role: Optional[Role]):
        """
        set administrator role
        """

        guild: Guild = ctx.guild
        if role is None:
            role = guild.get_role(await run_in_thread(Settings.get, int, "admin_role"))
            if role is None:
                await ctx.send(translations.no_role_set)
            else:
                await ctx.send(f"`@{role}` ({role.id})")
        else:
            await run_in_thread(Settings.set, int, "admin_role", role.id)
            await ctx.send(translations.role_set)
            await ctx.send(translations.f_log_role_set_admin(role.name, role.id))

    @mod.command(name="moderator", aliases=["mod", "m"])
    async def moderator(self, ctx: Context, role: Optional[Role]):
        """
        set moderator role
        """

        guild: Guild = ctx.guild
        if role is None:
            role = guild.get_role(await run_in_thread(Settings.get, int, "mod_role"))
            if role is None:
                await ctx.send(translations.no_role_set)
            else:
                await ctx.send(f"`@{role}` ({role.id})")
        else:
            await run_in_thread(Settings.set, int, "mod_role", role.id)
            await ctx.send(translations.role_set)
            await ctx.send(translations.f_log_role_set_mod(role.name, role.id))

    @mod.command(name="supporter", aliases=["supp", "s"])
    async def supporter(self, ctx: Context, role: Optional[Role]):
        """
        set supporter role
        """

        guild: Guild = ctx.guild
        if role is None:
            role = guild.get_role(await run_in_thread(Settings.get, int, "supp_role"))
            if role is None:
                await ctx.send(translations.no_role_set)
            else:
                await ctx.send(f"`@{role}` ({role.id})")
        else:
            await run_in_thread(Settings.set, int, "supp_role", role.id)
            await ctx.send(translations.role_set)
            await ctx.send(translations.f_log_role_set_supp(role.name, role.id))

    @mod.command(name="team", aliases=["t"])
    async def team(self, ctx: Context, role: Optional[Role]):
        """
        set team role
        """

        guild: Guild = ctx.guild
        if role is None:
            role = guild.get_role(await run_in_thread(Settings.get, int, "team_role"))
            if role is None:
                await ctx.send(translations.no_role_set)
            else:
                await ctx.send(f"`@{role}` ({role.id})")
        else:
            await run_in_thread(Settings.set, int, "team_role", role.id)
            await ctx.send(translations.role_set)
            await ctx.send(translations.f_log_role_set_team(role.name, role.id))
