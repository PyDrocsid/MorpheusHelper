import asyncio
from asyncio import Task
from typing import Optional, Dict

from discord import Role, Member, Guild, Forbidden, HTTPException, Embed
from discord.ext import commands
from discord.ext.commands import guild_only, Context, CommandError, UserInputError

from PyDrocsid.cog import Cog
from PyDrocsid.database import db_thread
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from .colors import Colors
from .permissions import AutoModPermission
from ..contributor import Contributor
from ..logging import send_to_changelog
from ..mod.models import Kick

pending_kicks: set[int] = set()


async def kick(member: Member) -> bool:
    if not member.guild.me.guild_permissions.kick_members:
        return False

    if member.top_role >= member.guild.me.top_role or member.id == member.guild.owner_id:
        return False

    try:
        embed = Embed(
            title=translations.autokick,
            description=translations.f_autokicked(member.guild.name),
            colour=Colors.AutoMod,
        )
        await member.send(embed=embed)
    except (Forbidden, HTTPException):
        pass

    pending_kicks.add(member.id)
    await member.kick(reason=translations.log_autokicked)
    await db_thread(Kick.create, member.id, str(member), None, None)
    return True


async def kick_delay(member: Member, delay: int, role: Role, reverse: bool):
    await asyncio.sleep(delay)
    if reverse != (role in member.roles):
        return

    if (member := member.guild.get_member(member.id)) is not None:
        await kick(member)


class AutoModCog(Cog, name="AutoMod"):
    CONTRIBUTORS = [Contributor.Defelo, Contributor.wolflu]
    PERMISSIONS = AutoModPermission

    def __init__(self):
        self.kick_tasks: Dict[Member, Task] = {}

    async def get_autokick_role(self) -> Optional[Role]:
        guild: Guild = self.bot.guilds[0]
        return guild.get_role(await Settings.get(int, "autokick_role", -1))

    async def get_instantkick_role(self) -> Optional[Role]:
        guild: Guild = self.bot.guilds[0]
        return guild.get_role(await Settings.get(int, "instantkick_role", -1))

    def cancel_task(self, member: Member):
        if member in self.kick_tasks:
            self.kick_tasks.pop(member).cancel()

    async def on_member_join(self, member: Member):
        if member.bot:
            return

        mode: int = await Settings.get(int, "autokick_mode", 0)
        role: Optional[Role] = await self.get_autokick_role()
        if mode == 0 or role is None:
            return

        delay: int = await Settings.get(int, "autokick_delay", 30)
        self.kick_tasks[member] = asyncio.create_task(kick_delay(member, delay, role, mode == 2))
        self.kick_tasks[member].add_done_callback(lambda _: self.cancel_task(member))

    async def on_member_remove(self, member: Member):
        if member.id in pending_kicks:
            pending_kicks.remove(member.id)
            return

        self.cancel_task(member)

    async def on_member_role_add(self, member: Member, role: Role):
        if member.bot:
            return

        if role == await self.get_instantkick_role():
            if not await kick(member):
                await member.remove_roles(role)
            return

        mode: int = await Settings.get(int, "autokick_mode", 0)
        if mode == 1 and role == await self.get_autokick_role():
            self.cancel_task(member)

    async def on_member_role_remove(self, member: Member, role: Role):
        if member.bot:
            return

        mode: int = await Settings.get(int, "autokick_mode", 0)
        if mode == 2 and role == await self.get_autokick_role():
            self.cancel_task(member)

    @commands.group(aliases=["ak"])
    @AutoModPermission.manage_autokick.check
    @guild_only()
    async def autokick(self, ctx: Context):
        """
        manage autokick
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        embed = Embed(title=translations.autokick, colour=Colors.error)
        mode: int = await Settings.get(int, "autokick_mode", 0)
        role: Optional[Role] = await self.get_autokick_role()
        if mode == 0 or role is None:
            embed.add_field(name=translations.status, value=translations.autokick_disabled, inline=False)
            await ctx.send(embed=embed)
            return

        embed.add_field(name=translations.status, value=translations.autokick_mode[mode - 1], inline=False)
        embed.colour = Colors.AutoMod
        delay: int = await Settings.get(int, "autokick_delay", 30)
        embed.add_field(name=translations.delay, value=translations.f_x_seconds(delay), inline=False)
        embed.add_field(name=translations.role, value=role.mention, inline=False)

        await ctx.send(embed=embed)

    @autokick.command(name="mode", aliases=["m"])
    async def autokick_mode(self, ctx: Context, mode: str):
        """
        configure autokick mode

        `off` - disable autokick
        `normal` - kick members without a specific role
        `reverse` - kick members with a specific role
        """

        mode: Optional[int] = {"off": 0, "normal": 1, "reverse": 2}.get(mode.lower())
        if mode is None:
            raise UserInputError

        await Settings.set(int, "autokick_mode", mode)
        embed = Embed(
            title=translations.autokick, description=translations.autokick_mode_configured[mode], colour=Colors.AutoMod
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.autokick_mode_configured[mode])

    @autokick.command(name="delay", aliases=["d"])
    async def autokick_delay(self, ctx: Context, seconds: int):
        """
        configure autokick delay (in seconds)
        """

        if not 0 < seconds < 300:
            raise CommandError(translations.invalid_duration)

        await Settings.set(int, "autokick_delay", seconds)
        embed = Embed(
            title=translations.autokick, description=translations.autokick_delay_configured, colour=Colors.AutoMod
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_autokick_delay_configured(seconds))

    @autokick.command(name="role", aliases=["r"])
    async def autokick_role(self, ctx: Context, *, role: Role):
        """
        configure autokick role
        """

        await Settings.set(int, "autokick_role", role.id)
        embed = Embed(
            title=translations.autokick, description=translations.autokick_role_configured, colour=Colors.AutoMod
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_autokick_role_configured(role.mention, role.id))

    @commands.group(aliases=["ik"])
    @AutoModPermission.manage_instantkick.check
    @guild_only()
    async def instantkick(self, ctx: Context):
        """
        manage instantkick
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        embed = Embed(title=translations.instantkick, colour=Colors.error)
        role: Optional[Role] = await self.get_instantkick_role()
        if role is None:
            embed.add_field(name=translations.status, value=translations.instantkick_disabled)
            await ctx.send(embed=embed)
            return

        embed.add_field(name=translations.status, value=translations.instantkick_enabled, inline=False)
        embed.colour = Colors.AutoMod
        embed.add_field(name=translations.role, value=role.mention, inline=False)

        await ctx.send(embed=embed)

    @instantkick.command(name="disable", aliases=["d", "off"])
    async def instantkick_disable(self, ctx: Context):
        """
        disable instantkick
        """

        await Settings.set(int, "instantkick_role", -1)
        embed = Embed(
            title=translations.instantkick, description=translations.instantkick_set_disabled, colour=Colors.AutoMod
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.instantkick_set_disabled)

    @instantkick.command(name="role", aliases=["r"])
    async def instantkick_role(self, ctx: Context, *, role: Role):
        """
        configure instantkick role
        """

        if role >= ctx.me.top_role:
            raise CommandError(translations.instantkick_cannot_kick)

        await Settings.set(int, "instantkick_role", role.id)
        embed = Embed(
            title=translations.instantkick, description=translations.instantkick_role_configured, colour=Colors.AutoMod
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_instantkick_role_configured(role.mention, role.id))
