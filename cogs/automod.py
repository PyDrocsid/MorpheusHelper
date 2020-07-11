import asyncio
from typing import Optional

from discord import Role, Member, Guild, Forbidden, HTTPException
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread
from models.mod import Kick
from models.settings import Settings
from permission import Permission
from translations import translations
from util import permission_level, send_to_changelog


class AutoModCog(Cog, name="AutoMod"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_autokick_role(self) -> Optional[Role]:
        guild: Guild = self.bot.guilds[0]
        return guild.get_role(await run_in_thread(Settings.get, int, "autokick_role", -1))

    async def on_member_join(self, member: Member) -> bool:
        if member.bot:
            return True

        mode: int = await run_in_thread(Settings.get, int, "autokick_mode", 0)
        role: Optional[Role] = await self.get_autokick_role()
        if mode == 0 or role is None:
            return True

        delay: int = await run_in_thread(Settings.get, int, "autokick_delay", 30)
        await asyncio.sleep(delay)
        if mode == 1 and role in member.roles:
            return True
        if mode == 2 and role not in member.roles:
            return True

        try:
            await member.send(translations.f_autokicked(member.guild.name))
        except (Forbidden, HTTPException):
            pass
        await member.kick(reason=translations.log_autokicked)
        await run_in_thread(Kick.create, member.id, str(member), None, None)
        return True

    @commands.group(name="autokick", aliases=["ak"])
    @permission_level(Permission.manage_autokick)
    @guild_only()
    async def autokick(self, ctx: Context):
        """
        manage autokick
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                await ctx.send_help(self.autokick)
            return

        mode: int = await run_in_thread(Settings.get, int, "autokick_mode", 0)
        role: Optional[Role] = await self.get_autokick_role()
        if mode == 0 or role is None:
            await ctx.send(translations.autokick_disabled)
            return

        delay: int = await run_in_thread(Settings.get, int, "autokick_delay", 30)
        out = [
            translations.autokick_mode[mode - 1],
            translations.f_autokick_delay(delay),
            translations.f_autokick_role(role.name, role.id),
        ]
        await ctx.send("\n".join(out))

    @autokick.command(name="mode", aliases=["m"])
    async def autokick_mode(self, ctx: Context, mode: str):
        """
        configure autokick mode:
        off:     disable autokick
        normal:  kick members without a specific role
        reverse: kick members with a specific role
        """

        mode: Optional[int] = {"off": 0, "normal": 1, "reverse": 2}.get(mode.lower())
        if mode is None:
            await ctx.send_help(self.autokick_mode)
            return

        await run_in_thread(Settings.set, int, "autokick_mode", mode)
        await ctx.send(translations.autokick_mode_configured[mode])
        await send_to_changelog(ctx.guild, translations.autokick_mode_configured[mode])

    @autokick.command(name="delay", aliases=["d"])
    async def autokick_delay(self, ctx: Context, seconds: int):
        """
        configure autokick delay (in seconds)
        """

        if not 0 < seconds < 300:
            raise CommandError(translations.invalid_duration)

        await run_in_thread(Settings.set, int, "autokick_delay", seconds)
        await ctx.send(translations.autokick_delay_configured)
        await send_to_changelog(ctx.guild, translations.f_log_autokick_delay_configured(seconds))

    @autokick.command(name="role", aliases=["r"])
    async def autokick_role(self, ctx: Context, role: Role):
        """
        configure autokick role
        """

        if role > ctx.me.top_role:
            raise CommandError(translations.f_role_not_set_too_high(role, ctx.me.top_role))
        if role.managed:
            raise CommandError(translations.f_role_not_set_managed_role(role))

        await run_in_thread(Settings.set, int, "autokick_role", role.id)
        await ctx.send(translations.autokick_role_configured)
        await send_to_changelog(ctx.guild, translations.f_log_autokick_role_configured(role.name, role.id))
