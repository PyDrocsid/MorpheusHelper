from datetime import datetime, timedelta
from typing import Optional, Union, List, Tuple

from discord import Role, Guild, Member, Forbidden, HTTPException, User, Embed, NotFound
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.mod import Warn, Report, Mute, Kick, Ban, Join, Leave
from models.settings import Settings
from translations import translations
from util import permission_level, ADMINISTRATOR, send_to_changelog, SUPPORTER, MODERATOR


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

        for ban in await run_in_thread(db.query, Ban, active=True):
            if ban.days != -1 and datetime.now() >= ban.timestamp + timedelta(days=ban.days):
                user: Optional[User] = await self.bot.fetch_user(ban.member)
                if user is not None:
                    await guild.unban(user)
                await send_to_changelog(guild, translations.f_log_unbanned_expired(f"<@{ban.member}>", ban.member_name))
                await run_in_thread(Ban.deactivate, ban.id)

        mute_role: Optional[Role] = guild.get_role(await run_in_thread(Settings.get, int, "mute_role"))
        if mute_role is None:
            return

        for mute in await run_in_thread(db.query, Mute, active=True):
            if mute.days != -1 and datetime.now() >= mute.timestamp + timedelta(days=mute.days):
                member: Optional[Member] = guild.get_member(mute.member)
                if member is not None:
                    await member.remove_roles(mute_role)
                await send_to_changelog(
                    guild, translations.f_log_unmuted_expired(f"<@{mute.member}>", mute.member_name)
                )
                await run_in_thread(Mute.deactivate, mute.id)

    async def on_member_join(self, member: Member):
        await run_in_thread(Join.create, member.id, str(member))
        mute_role: Optional[Role] = member.guild.get_role(await run_in_thread(Settings.get, int, "mute_role"))
        if mute_role is None:
            return True

        if await run_in_thread(db.first, Mute, active=True, member=member.id) is not None:
            await member.add_roles(mute_role)

        return True

    async def on_member_remove(self, member: Member):
        await run_in_thread(Leave.create, member.id, str(member))

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

        await run_in_thread(Report.create, member.id, str(member), ctx.author.id, reason)
        await ctx.send(translations.reported_response)
        await send_to_changelog(
            ctx.guild, translations.f_log_reported(ctx.author.mention, member.mention, member, reason)
        )

    @commands.command(name="warn")
    @permission_level(SUPPORTER)
    @guild_only()
    async def warn(self, ctx: Context, member: Member, *, reason: str):
        """
        warn a member
        """

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        try:
            await member.send(translations.f_warned(ctx.author.mention, ctx.guild.name, reason))
        except (Forbidden, HTTPException):
            await ctx.send(translations.no_dm)
        await run_in_thread(Warn.create, member.id, str(member), ctx.author.id, reason)
        await ctx.send(translations.warned_response)
        await send_to_changelog(
            ctx.guild, translations.f_log_warned(ctx.author.mention, member.mention, member, reason)
        )

    @commands.command(name="mute")
    @permission_level(SUPPORTER)
    @guild_only()
    async def mute(self, ctx: Context, member: Member, days: Optional[int], *, reason: str):
        """
        mute a member
        """

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        if days is not None and not 0 < days < (1 << 31):
            raise CommandError(translations.invalid_mute_time)

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
            await run_in_thread(Mute.create, member.id, str(member), ctx.author.id, days, reason)
            await ctx.send(translations.muted_response)
            await send_to_changelog(
                ctx.guild, translations.f_log_muted(ctx.author.mention, member.mention, member, days, reason)
            )
        else:
            await run_in_thread(Mute.create, member.id, str(member), ctx.author.id, -1, reason)
            await ctx.send(translations.muted_response)
            await send_to_changelog(
                ctx.guild, translations.f_log_muted_inf(ctx.author.mention, member.mention, member, reason)
            )

    @commands.command(name="unmute")
    @permission_level(SUPPORTER)
    @guild_only()
    async def unmute(self, ctx: Context, member: Member, *, reason: str):
        """
        unmute a member
        """

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        mute_role: Optional[Role] = ctx.guild.get_role(await run_in_thread(Settings.get, int, "mute_role"))
        if mute_role is None:
            raise CommandError(translations.mute_role_not_set)

        if mute_role not in member.roles:
            raise CommandError(translations.not_muted)

        await member.remove_roles(mute_role)

        for mute in await run_in_thread(db.query, Mute, active=True, member=member.id):
            await run_in_thread(Mute.deactivate, mute.id, reason)
        await ctx.send(translations.unmuted_response)
        await send_to_changelog(
            ctx.guild, translations.f_log_unmuted(ctx.author.mention, member.mention, member, reason)
        )

    @commands.command(name="kick")
    @permission_level(MODERATOR)
    @guild_only()
    async def kick(self, ctx: Context, member: Member, *, reason: str):
        """
        kick a member
        """

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        if not ctx.guild.me.guild_permissions.kick_members:
            raise CommandError(translations.cannot_kick_permissions)

        if member.top_role >= ctx.guild.me.top_role:
            raise CommandError(translations.cannot_kick)

        try:
            await member.send(translations.f_kicked(ctx.author.mention, ctx.guild.name, reason))
        except (Forbidden, HTTPException):
            await ctx.send(translations.no_dm)
        await member.kick()
        await run_in_thread(Kick.create, member.id, str(member), ctx.author.id, reason)
        await ctx.send(translations.kicked_response)
        await send_to_changelog(
            ctx.guild, translations.f_log_kicked(ctx.author.mention, member.mention, member, reason)
        )

    @commands.command(name="ban")
    @permission_level(MODERATOR)
    @guild_only()
    async def ban(self, ctx: Context, user: Union[Member, User, int], days: Optional[int], *, reason: str):
        """
        ban a user
        """

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        if not ctx.guild.me.guild_permissions.ban_members:
            raise CommandError(translations.cannot_ban_permissions)

        if days is not None and not 0 < days < (1 << 31):
            raise CommandError(translations.invalid_ban_time)

        if isinstance(user, int):
            user = ctx.guild.get_member(user) or await self.bot.fetch_user(user)
            if user is None:
                raise CommandError(translations.user_not_found)

        if isinstance(user, Member) and user.top_role >= ctx.guild.me.top_role:
            raise CommandError(translations.cannot_ban)

        try:
            if days is not None:
                await user.send(translations.f_banned(ctx.author.mention, ctx.guild.name, days, reason))
            else:
                await user.send(translations.f_banned_inf(ctx.author.mention, ctx.guild.name, reason))
        except (Forbidden, HTTPException):
            await ctx.send(translations.no_dm)

        await ctx.guild.ban(user, delete_message_days=1)
        if days is not None:
            await run_in_thread(Ban.create, user.id, str(user), ctx.author.id, days, reason)
            await ctx.send(translations.banned_response)
            await send_to_changelog(
                ctx.guild, translations.f_log_banned(ctx.author.mention, user.mention, user, days, reason)
            )
        else:
            await run_in_thread(Ban.create, user.id, str(user), ctx.author.id, -1, reason)
            await ctx.send(translations.banned_response)
            await send_to_changelog(
                ctx.guild, translations.f_log_banned_inf(ctx.author.mention, user.mention, user, reason)
            )

    @commands.command(name="unban")
    @permission_level(MODERATOR)
    @guild_only()
    async def unban(self, ctx: Context, user: Union[User, int], *, reason: str):
        """
        unban a user
        """

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        if not ctx.guild.me.guild_permissions.ban_members:
            raise CommandError(translations.cannot_unban_permissions)

        if isinstance(user, int):
            user = ctx.guild.get_member(user) or await self.bot.fetch_user(user)
            if user is None:
                raise CommandError(translations.user_not_found)

        if ctx.guild.get_member(user.id) is not None:
            raise CommandError(translations.not_banned)

        try:
            await ctx.guild.unban(user)
        except HTTPException:
            raise CommandError(translations.not_banned)

        for ban in await run_in_thread(db.query, Ban, active=True, member=user.id):
            await run_in_thread(Ban.deactivate, ban.id, reason)
        await ctx.send(translations.unbanned_response)
        await send_to_changelog(ctx.guild, translations.f_log_unbanned(ctx.author.mention, user.mention, user, reason))

    @commands.command(name="stats")
    @permission_level(SUPPORTER)
    @guild_only()
    async def stats(self, ctx: Context, user: Union[User, int]):
        """
        show statistics about a user
        """

        if isinstance(user, int):
            try:
                user = await self.bot.fetch_user(user)
            except NotFound:
                pass

        user_id = user if isinstance(user, int) else user.id
        embed = Embed(title=translations.stats, color=0x35992C)
        if isinstance(user, int):
            embed.set_author(name=str(user))
        else:
            embed.set_author(name=str(user), icon_url=user.avatar_url)

        async def count(cls):
            if cls is Report:
                active = await run_in_thread(db.count, cls, reporter=user_id)
            else:
                active = await run_in_thread(db.count, cls, mod=user_id)
            passive = await run_in_thread(db.count, cls, member=user_id)
            return translations.f_active_passive(active, passive)

        embed.add_field(name=translations.reported_cnt, value=await count(Report))
        embed.add_field(name=translations.warned_cnt, value=await count(Warn))
        embed.add_field(name=translations.muted_cnt, value=await count(Mute))
        embed.add_field(name=translations.kicked_cnt, value=await count(Kick))
        embed.add_field(name=translations.banned_cnt, value=await count(Ban))

        if (ban := await run_in_thread(db.first, Ban, member=user_id, active=True)) is not None:
            if ban.days != -1:
                expiry_date: datetime = ban.timestamp + timedelta(days=ban.days)
                days_left = (expiry_date - datetime.now()).days + 1
                status = translations.f_status_banned_days(ban.days, days_left)
            else:
                status = translations.status_banned
        elif (mute := await run_in_thread(db.first, Mute, member=user_id, active=True)) is not None:
            if mute.days != -1:
                expiry_date: datetime = mute.timestamp + timedelta(days=mute.days)
                days_left = (expiry_date - datetime.now()).days + 1
                status = translations.f_status_muted_days(mute.days, days_left)
            else:
                status = translations.status_muted
        elif (member := ctx.guild.get_member(user_id)) is not None:
            status = translations.f_member_since(member.joined_at.strftime("%d.%m.%Y %H:%M:%S"))
        else:
            status = translations.not_a_member
        embed.add_field(name=translations.status, value=status, inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="userlogs", aliases=["userlog", "ulog"])
    @permission_level(SUPPORTER)
    @guild_only()
    async def userlogs(self, ctx: Context, user: Union[User, int]):
        """
        show moderation log of a user
        """

        if isinstance(user, int):
            try:
                user = await self.bot.fetch_user(user)
            except NotFound:
                pass

        user_id = user if isinstance(user, int) else user.id

        out: List[Tuple[datetime, str]] = []
        for join in await run_in_thread(db.query, Join, member=user_id):
            out.append((join.timestamp, translations.ulog_joined))
        for leave in await run_in_thread(db.query, Leave, member=user_id):
            out.append((leave.timestamp, translations.ulog_left))
        for report in await run_in_thread(db.query, Report, member=user_id):
            out.append((report.timestamp, translations.f_ulog_reported(f"<@{report.reporter}>", report.reason)))
        for warn in await run_in_thread(db.query, Warn, member=user_id):
            out.append((warn.timestamp, translations.f_ulog_warned(f"<@{warn.mod}>", warn.reason)))
        for mute in await run_in_thread(db.query, Mute, member=user_id):
            if mute.days == -1:
                out.append((mute.timestamp, translations.f_ulog_muted_inf(f"<@{mute.mod}>", mute.reason)))
            else:
                out.append((mute.timestamp, translations.f_ulog_muted(f"<@{mute.mod}>", mute.days, mute.reason)))
            if not mute.active:
                if mute.unmute_reason is None:
                    out.append((mute.deactivation_timestamp, translations.ulog_unmuted_expired))
                else:
                    out.append(
                        (mute.deactivation_timestamp, translations.f_ulog_unmuted(f"<@{mute.mod}>", mute.unmute_reason))
                    )
        for kick in await run_in_thread(db.query, Kick, member=user_id):
            out.append((kick.timestamp, translations.f_ulog_kicked(f"<@{kick.mod}>", kick.reason)))
        for ban in await run_in_thread(db.query, Ban, member=user_id):
            if ban.days == -1:
                out.append((ban.timestamp, translations.f_ulog_banned_inf(f"<@{ban.mod}>", ban.reason)))
            else:
                out.append((ban.timestamp, translations.f_ulog_banned(f"<@{ban.mod}>", ban.days, ban.reason)))
            if not ban.active:
                if ban.unban_reason is None:
                    out.append((ban.deactivation_timestamp, translations.ulog_unbanned_expired))
                else:
                    out.append(
                        (ban.deactivation_timestamp, translations.f_ulog_unbanned(f"<@{ban.mod}>", ban.unban_reason))
                    )

        out.sort()
        embeds = [Embed(color=0x34B77E)]
        embeds[0].title = translations.userlogs
        if isinstance(user, int):
            embeds[0].set_author(name=str(user))
        else:
            embeds[0].set_author(name=str(user), icon_url=user.avatar_url)
        i = 0
        total = 0
        for row in out:
            name = row[0].strftime("%d.%m.%Y %H:%M:%S")
            value = row[1]
            if i == 25 or total + len(name) + len(value) >= 5800:
                embed = Embed(color=0x34B77E)
                embeds.append(embed)
                total = 0
            total += len(name) + len(value)
            embeds[-1].add_field(name=name, value=value, inline=False)
            i += 1
        if out:
            embeds[-1].set_footer(text=translations.utc_note)
            for embed in embeds:
                await ctx.send(embed=embed)
        else:
            await ctx.send(translations.ulog_empty)
