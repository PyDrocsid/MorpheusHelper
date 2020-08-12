import asyncio
from asyncio import Task
from typing import Optional, Dict

from discord import Role, Member, Guild, Forbidden, HTTPException, Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError, UserInputError

from database import run_in_thread
from models.mod import Kick
from models.settings import Settings
from permission import Permission
from translations import translations
from util import permission_level, send_to_changelog


async def kick(member: Member) -> bool:
    if not member.guild.me.guild_permissions.kick_members:
        return False

    if member.top_role >= member.guild.me.top_role or member.id == member.guild.owner_id:
        return False

    try:
        embed = Embed(title=translations.autokick, description=translations.f_autokicked(member.guild.name),
                      colour=0x256BE6)
        await member.send(embed=embed)
    except (Forbidden, HTTPException):
        pass
    await member.kick(reason=translations.log_autokicked)
    await run_in_thread(Kick.create, member.id, str(member), None, None)
    return True


async def kick_delay(member: Member, delay: int, role: Role, reverse: bool):
    await asyncio.sleep(delay)
    if reverse != (role in member.roles):
        return

    if (member := member.guild.get_member(member.id)) is not None:
        await kick(member)


class AutoModCog(Cog, name="AutoMod"):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.kick_tasks: Dict[Member, Task] = {}

    async def get_autokick_role(self) -> Optional[Role]:
        guild: Guild = self.bot.guilds[0]
        return guild.get_role(await run_in_thread(Settings.get, int, "autokick_role", -1))

    async def get_instantkick_role(self) -> Optional[Role]:
        guild: Guild = self.bot.guilds[0]
        return guild.get_role(await run_in_thread(Settings.get, int, "instantkick_role", -1))

    def cancel_task(self, member: Member):
        if member in self.kick_tasks:
            self.kick_tasks.pop(member).cancel()

    async def on_member_join(self, member: Member) -> bool:
        if member.bot:
            return True

        mode: int = await run_in_thread(Settings.get, int, "autokick_mode", 0)
        role: Optional[Role] = await self.get_autokick_role()
        if mode == 0 or role is None:
            return True

        delay: int = await run_in_thread(Settings.get, int, "autokick_delay", 30)
        self.kick_tasks[member] = asyncio.create_task(kick_delay(member, delay, role, mode == 2))
        self.kick_tasks[member].add_done_callback(lambda _: self.cancel_task(member))
        return True

    async def on_member_remove(self, member: Member):
        self.cancel_task(member)
        return True

    async def on_member_role_add(self, member: Member, role: Role) -> bool:
        if member.bot:
            return True

        if role == await self.get_instantkick_role():
            if await kick(member):
                return False

        mode: int = await run_in_thread(Settings.get, int, "autokick_mode", 0)
        if mode == 1 and role == await self.get_autokick_role():
            self.cancel_task(member)

        return True

    async def on_member_role_remove(self, member: Member, role: Role) -> bool:
        if member.bot:
            return True

        mode: int = await run_in_thread(Settings.get, int, "autokick_mode", 0)
        if mode == 2 and role == await self.get_autokick_role():
            self.cancel_task(member)

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
                raise UserInputError
            return

        embed = Embed(title=translations.autokick, colour=0xCF0606)
        mode: int = await run_in_thread(Settings.get, int, "autokick_mode", 0)
        role: Optional[Role] = await self.get_autokick_role()
        if mode == 0 or role is None:
            embed.add_field(name=translations.status, value=translations.autokick_disabled, inline=False)
            await ctx.send(embed=embed)
            return

        embed.add_field(name=translations.status, value=translations.autokick_mode[mode - 1], inline=False)
        embed.colour = [0x256BE6, 0x03AD28][mode - 1]
        delay: int = await run_in_thread(Settings.get, int, "autokick_delay", 30)
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

        await run_in_thread(Settings.set, int, "autokick_mode", mode)
        embed = Embed(title=translations.autokick, description=translations.autokick_mode_configured[mode],
                      colour=0x256BE6)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.autokick_mode_configured[mode])

    @autokick.command(name="delay", aliases=["d"])
    async def autokick_delay(self, ctx: Context, seconds: int):
        """
        configure autokick delay (in seconds)
        """

        if not 0 < seconds < 300:
            raise CommandError(translations.invalid_duration)

        await run_in_thread(Settings.set, int, "autokick_delay", seconds)
        embed = Embed(title=translations.autokick, description=translations.autokick_delay_configured, colour=0x256BE6)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_autokick_delay_configured(seconds))

    @autokick.command(name="role", aliases=["r"])
    async def autokick_role(self, ctx: Context, *, role: Role):
        """
        configure autokick role
        """

        await run_in_thread(Settings.set, int, "autokick_role", role.id)
        embed = Embed(title=translations.autokick, description=translations.autokick_role_configured, colour=0x256BE6)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_autokick_role_configured(role.name, role.id))

    @commands.group(name="instantkick", aliases=["ik"])
    @permission_level(Permission.manage_instantkick)
    @guild_only()
    async def instantkick(self, ctx: Context):
        """
        manage instantkick
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        embed = Embed(title=translations.instantkick, colour=0xCF0606)
        role: Optional[Role] = await self.get_instantkick_role()
        if role is None:
            embed.add_field(name=translations.status, value=translations.instantkick_disabled)
            await ctx.send(embed=embed)
            return

        embed.add_field(name=translations.status, value=translations.instantkick_enabled, inline=False)
        embed.colour = 0x256BE6
        embed.add_field(name=translations.role, value=role.mention, inline=False)

        await ctx.send(embed=embed)

    @instantkick.command(name="disable", aliases=["d", "off"])
    async def instantkick_mode(self, ctx: Context):
        """
        disable instantkick
        """

        await run_in_thread(Settings.set, int, "instantkick_role", -1)
        embed = Embed(title=translations.instantkick, description=translations.instantkick_set_disabled,
                      colour=0x256BE6)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.instantkick_set_disabled)

    @instantkick.command(name="role", aliases=["r"])
    async def instantkick_role(self, ctx: Context, *, role: Role):
        """
        configure instantkick role
        """

        if role >= ctx.me.top_role:
            raise CommandError(translations.instantkick_cannot_kick)

        await run_in_thread(Settings.set, int, "instantkick_role", role.id)
        embed = Embed(title=translations.instantkick, description=translations.instantkick_role_configured,
                      colour=0x256BE6)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_instantkick_role_configured(role.name, role.id))
