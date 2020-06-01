from datetime import datetime, timedelta
from typing import Optional

from discord import Role, Guild, Member, Forbidden, HTTPException
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.mod import Warn, Report, Mute, Kick
from models.settings import Settings
from translations import translations
from util import permission_level, ADMINISTRATOR, send_to_changelog, SUPPORTER, check_permissions


async def configure_role(ctx: Context, role_name: str, role: Optional[Role], check_assignable: bool = False):
    guild: Guild = ctx.guild
    if role is None:
        role = guild.get_role(await run_in_thread(Settings.get, int, role_name + "_role"))
        if role is None:
            await ctx.send(translations.no_role_set)
        else:
            await ctx.send(f"`@{role}` ({role.id})")
    else:
        if check_assignable:
            if role > ctx.me.top_role:
                raise CommandError(translations.f_role_not_set_too_high(role, ctx.me.top_role))
            if role.managed:
                raise CommandError(translations.f_role_not_set_managed_role(role))
        await run_in_thread(Settings.set, int, role_name + "_role", role.id)
        await ctx.send(translations.role_set)
        await send_to_changelog(ctx.guild, getattr(translations, "f_log_role_set_" + role_name)(role.name, role.id))


class ModCog(Cog, name="Mod Tools"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_ready(self):
        guild: Guild = self.bot.guilds[0]
        mute_role: Optional[Role] = guild.get_role(await run_in_thread(Settings.get, int, "mute_role"))
        if mute_role is not None:
            for mute in await run_in_thread(db.query, Mute, active=True):
                member: Optional[Member] = guild.get_member(mute.member)
                if member is not None:
                    await member.add_roles(mute_role)

        try:
            self.mod_loop.start()
        except RuntimeError:
            self.mod_loop.restart()
        return True

    @tasks.loop(seconds=10)
    async def mod_loop(self):
        guild: Guild = self.bot.guilds[0]
        mute_role: Optional[Role] = guild.get_role(await run_in_thread(Settings.get, int, "mute_role"))
        if mute_role is None:
            return

        for mute in await run_in_thread(db.query, Mute, active=True):
            if mute.days != -1 and datetime.now() >= mute.timestamp + timedelta(days=mute.days):
                member: Optional[Member] = guild.get_member(mute.member)
                if member is not None:
                    await member.remove_roles(mute_role)
                await send_to_changelog(guild, translations.f_log_unmuted_expired(member.mention))
                await run_in_thread(Mute.deactivate, mute.id)

    async def on_member_join(self, member: Member):
        mute_role: Optional[Role] = member.guild.get_role(await run_in_thread(Settings.get, int, "mute_role"))
        if mute_role is None:
            return True

        if await run_in_thread(db.first, Mute, active=True, member=member.id) is not None:
            await member.add_roles(mute_role)

        return True

    @commands.group(name="roles")
    @permission_level(ADMINISTRATOR)
    @guild_only()
    async def roles(self, ctx: Context):
        """
        configure roles
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(ModCog.roles)

    @roles.command(name="administrator", aliases=["admin"])
    async def set_admin(self, ctx: Context, role: Optional[Role]):
        """
        set administrator role
        """

        await configure_role(ctx, "admin", role)

    @roles.command(name="moderator", aliases=["mod"])
    async def set_mod(self, ctx: Context, role: Optional[Role]):
        """
        set moderator role
        """

        await configure_role(ctx, "mod", role)

    @roles.command(name="supporter", aliases=["supp"])
    async def set_supp(self, ctx: Context, role: Optional[Role]):
        """
        set supporter role
        """

        await configure_role(ctx, "supp", role)

    @roles.command(name="team")
    async def set_team(self, ctx: Context, role: Optional[Role]):
        """
        set team role
        """

        await configure_role(ctx, "team", role)

    @roles.command(name="mute")
    async def set_mute(self, ctx: Context, role: Optional[Role]):
        """
        set mute role
        """

        await configure_role(ctx, "mute", role, check_assignable=True)

    @commands.command(name="report")
    @guild_only()
    async def report(self, ctx: Context, member: Member, *, reason: str):
        """
        report a member
        """

        await run_in_thread(Report.create, member.id, ctx.author.id, reason)
        await ctx.send(translations.reported_response)
        await send_to_changelog(ctx.guild, translations.f_log_reported(ctx.author.mention, member.mention, reason))

    @commands.command(name="warn")
    @permission_level(SUPPORTER)
    @guild_only()
    async def warn(self, ctx: Context, member: Member, *, reason: str):
        """
        warn a member
        """

        try:
            await member.send(translations.f_warned(ctx.author.mention, ctx.guild.name, reason))
        except (Forbidden, HTTPException):
            await ctx.send(translations.no_dm)
        await run_in_thread(Warn.create, member.id, ctx.author.id, reason)
        await ctx.send(translations.warned_response)
        await send_to_changelog(ctx.guild, translations.f_log_warned(ctx.author.mention, member.mention, reason))

    @commands.command(name="mute")
    @permission_level(SUPPORTER)
    @guild_only()
    async def mute(self, ctx: Context, member: Member, days: Optional[int], *, reason: str):
        """
        mute a member
        """

        if days is not None and not 0 < days < (1 << 31):
            raise CommandError(translations.invalid_mute_time)

        if member.bot or await check_permissions(member, SUPPORTER):
            raise CommandError(translations.cannot_mute)

        mute_role: Optional[Role] = ctx.guild.get_role(await run_in_thread(Settings.get, int, "mute_role"))
        if mute_role is None:
            raise CommandError(translations.mute_role_not_set)

        if mute_role in member.roles:
            raise CommandError(translations.already_muted)

        await member.add_roles(mute_role)
        try:
            if days is not None:
                await member.send(translations.f_muted(ctx.author.mention, ctx.guild.name, days, reason))
            else:
                await member.send(translations.f_muted_inf(ctx.author.mention, ctx.guild.name, reason))
        except (Forbidden, HTTPException):
            await ctx.send(translations.no_dm)
        if days is not None:
            await run_in_thread(Mute.create, member.id, ctx.author.id, days, reason)
            await ctx.send(translations.muted_response)
            await send_to_changelog(
                ctx.guild, translations.f_log_muted(ctx.author.mention, member.mention, days, reason)
            )
        else:
            await run_in_thread(Mute.create, member.id, ctx.author.id, -1, reason)
            await ctx.send(translations.muted_response)
            await send_to_changelog(ctx.guild, translations.f_log_muted_inf(ctx.author.mention, member.mention, reason))

    @commands.command(name="unmute")
    @permission_level(SUPPORTER)
    @guild_only()
    async def unmute(self, ctx: Context, member: Member, *, reason: str):
        """
        unmute a member
        """

        mute_role: Optional[Role] = ctx.guild.get_role(await run_in_thread(Settings.get, int, "mute_role"))
        if mute_role is None:
            raise CommandError(translations.mute_role_not_set)

        if mute_role not in member.roles:
            raise CommandError(translations.not_muted)

        await member.remove_roles(mute_role)

        for mute in await run_in_thread(db.query, Mute, active=True, member=member.id):
            await run_in_thread(Mute.deactivate, mute.id)
        await ctx.send(translations.unmuted_response)
        await send_to_changelog(ctx.guild, translations.f_log_unmuted(ctx.author.mention, member.mention, reason))

    @commands.command(name="kick")
    @permission_level(SUPPORTER)
    @guild_only()
    async def kick(self, ctx: Context, member: Member, *, reason: str):
        """
        kick a member
        """

        if not ctx.guild.me.guild_permissions.kick_members:
            raise CommandError(translations.cannot_kick)

        try:
            await member.send(translations.f_kicked(ctx.author.mention, ctx.guild.name, reason))
        except (Forbidden, HTTPException):
            await ctx.send(translations.no_dm)
        await member.kick()
        await run_in_thread(Kick.create, member.id, ctx.author.id, reason)
        await ctx.send(translations.kicked_response)
        await send_to_changelog(ctx.guild, translations.f_log_kicked(ctx.author.mention, member.mention, reason))
