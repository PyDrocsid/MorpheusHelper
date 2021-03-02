import re
from datetime import datetime, timedelta
from typing import Optional, Union, List, Tuple

from PyDrocsid.database import db_thread, db
from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from PyDrocsid.util import send_long_embed
from discord import Role, Guild, Member, Forbidden, HTTPException, User, Embed, NotFound, Message
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError, Converter, BadArgument, UserInputError
from discord.utils import snowflake_time

from colours import Colours
from models.allowed_invite import InviteLog
from models.mod import Join, Mute, Ban, Leave, UsernameUpdate, Report, Warn, Kick
from permissions import Permission, PermissionLevel
from util import send_to_changelog, get_prefix, is_teamler


class DurationConverter(Converter):
    async def convert(self, ctx, argument: str) -> Optional[int]:
        if argument.lower() in ("inf", "perm", "permanent", "-1", "∞"):
            return None
        if (match := re.match(r"^(\d+)d?$", argument)) is None:
            raise BadArgument(translations.invalid_duration)
        if (days := int(match.group(1))) <= 0:
            raise BadArgument(translations.invalid_duration)
        if days >= (1 << 31):
            raise BadArgument(translations.invalid_duration_inf)
        return days


async def configure_role(ctx: Context, role_name: str, role: Role, check_assignable: bool = False):
    if check_assignable:
        if role >= ctx.me.top_role:
            raise CommandError(translations.f_role_not_set_too_high(role, ctx.me.top_role))
        if role.managed:
            raise CommandError(translations.f_role_not_set_managed_role(role))
    await Settings.set(int, role_name + "_role", role.id)
    embed = Embed(title=translations.roles, description=translations.role_set, color=Colours.ModTools)
    await ctx.send(embed=embed)
    await send_to_changelog(
        ctx.guild, translations.f_log_role_set(translations.role_name[role_name], role.mention, role.id)
    )


async def get_mute_role(guild: Guild) -> Role:
    mute_role: Optional[Role] = guild.get_role(await Settings.get(int, "mute_role"))
    if mute_role is None:
        raise CommandError(translations.mute_role_not_set)
    return mute_role


async def update_join_date(guild: Guild, user_id: int):
    member: Optional[Member] = guild.get_member(user_id)
    if member is not None:
        await db_thread(Join.update, member.id, str(member), member.joined_at)


async def send_to_changelog_mod(
    guild: Guild,
    message: Optional[Message],
    colour: int,
    title: str,
    member: Union[Member, User, Tuple[int, str]],
    reason: str,
    *,
    duration: Optional[str] = None,
):
    embed = Embed(title=title, colour=colour, timestamp=datetime.utcnow())

    if isinstance(member, tuple):
        member_id, member_name = member
        embed.set_author(name=member_name)
    else:
        member_id: int = member.id
        member_name: str = str(member)
        embed.set_author(name=member_name, icon_url=member.avatar_url)

    embed.add_field(name=translations.log_field_member, value=f"<@{member_id}>", inline=True)
    embed.add_field(name=translations.log_field_member_id, value=str(member_id), inline=True)

    if message:
        embed.set_footer(text=str(message.author), icon_url=message.author.avatar_url)
        embed.add_field(
            name=translations.log_field_channel,
            value=translations.f_jump_url(message.channel.mention, message.jump_url),
            inline=True,
        )

    if duration:
        embed.add_field(name=translations.log_field_duration, value=duration, inline=True)

    embed.add_field(name=translations.log_field_reason, value=reason, inline=False)

    await send_to_changelog(guild, embed)


class ModCog(Cog, name="Mod Tools"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_ready(self):
        guild: Guild = self.bot.guilds[0]
        mute_role: Optional[Role] = guild.get_role(await Settings.get(int, "mute_role"))
        if mute_role is not None:
            for mute in await db_thread(db.all, Mute, active=True):
                member: Optional[Member] = guild.get_member(mute.member)
                if member is not None:
                    await member.add_roles(mute_role)

        try:
            self.mod_loop.start()
        except RuntimeError:
            self.mod_loop.restart()

    @tasks.loop(minutes=30)
    async def mod_loop(self):
        guild: Guild = self.bot.guilds[0]

        for ban in await db_thread(db.all, Ban, active=True):
            if ban.days != -1 and datetime.utcnow() >= ban.timestamp + timedelta(days=ban.days):
                await db_thread(Ban.deactivate, ban.id)

                try:
                    await guild.unban(user := await self.bot.fetch_user(ban.member))
                except NotFound:
                    user = ban.member, ban.member_name

                await send_to_changelog_mod(
                    guild,
                    None,
                    Colours.changelog["unban"],
                    translations.log_unbanned,
                    user,
                    translations.log_unbanned_expired,
                )

        mute_role: Optional[Role] = guild.get_role(await Settings.get(int, "mute_role"))
        if mute_role is None:
            return

        for mute in await db_thread(db.all, Mute, active=True):
            if mute.days != -1 and datetime.utcnow() >= mute.timestamp + timedelta(days=mute.days):
                if member := guild.get_member(mute.member):
                    await member.remove_roles(mute_role)
                else:
                    member = mute.member, mute.member_name

                await send_to_changelog_mod(
                    guild,
                    None,
                    Colours.changelog["unmute"],
                    translations.log_unmuted,
                    member,
                    translations.log_unmuted_expired,
                )
                await db_thread(Mute.deactivate, mute.id)

    async def on_member_join(self, member: Member):
        await db_thread(Join.create, member.id, str(member))
        mute_role: Optional[Role] = member.guild.get_role(await Settings.get(int, "mute_role"))
        if mute_role is None:
            return

        if await db_thread(db.first, Mute, active=True, member=member.id) is not None:
            await member.add_roles(mute_role)

    async def on_member_remove(self, member: Member):
        await db_thread(Leave.create, member.id, str(member))

    async def on_member_nick_update(self, before: Member, after: Member):
        await db_thread(UsernameUpdate.create, before.id, before.nick, after.nick, True)

    async def on_user_update(self, before: User, after: User):
        if str(before) == str(after):
            return

        await db_thread(UsernameUpdate.create, before.id, str(before), str(after), False)

    @commands.group()
    @PermissionLevel.ADMINISTRATOR.check
    @guild_only()
    async def roles(self, ctx: Context):
        """
        configure roles
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        embed = Embed(title=translations.roles, color=Colours.ModTools)
        for role_name in ["admin", "mod", "supp", "team", "mute"]:
            role = ctx.guild.get_role(await Settings.get(int, role_name + "_role"))
            val = role.mention if role is not None else translations.role_not_set
            embed.add_field(name=translations.role_name[role_name], value=val, inline=False)
        await ctx.send(embed=embed)

    @roles.command(name="administrator", aliases=["admin"])
    async def roles_administrator(self, ctx: Context, role: Role):
        """
        set administrator role
        """

        await configure_role(ctx, "admin", role)

    @roles.command(name="moderator", aliases=["mod"])
    async def roles_moderator(self, ctx: Context, role: Role):
        """
        set moderator role
        """

        await configure_role(ctx, "mod", role)

    @roles.command(name="supporter", aliases=["supp"])
    async def roles_supporter(self, ctx: Context, role: Role):
        """
        set supporter role
        """

        await configure_role(ctx, "supp", role)

    @roles.command(name="team")
    async def roles_team(self, ctx: Context, role: Role):
        """
        set team role
        """

        await configure_role(ctx, "team", role)

    @roles.command(name="mute")
    async def roles_mute(self, ctx: Context, role: Role):
        """
        set mute role
        """

        await configure_role(ctx, "mute", role, check_assignable=True)

    @commands.command()
    @guild_only()
    async def report(self, ctx: Context, member: Union[Member, int], *, reason: str):
        """
        report a member
        """
        member: Member = await self.get_user(ctx.guild, member)
        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        await db_thread(Report.create, member.id, str(member), ctx.author.id, reason)
        embed = Embed(title=translations.report, description=translations.reported_response, colour=Colours.ModTools)
        await ctx.send(embed=embed)
        await send_to_changelog_mod(
            ctx.guild, ctx.message, Colours.changelog["report"], translations.log_reported, member, reason
        )

    @commands.command()
    @Permission.warn.check
    @guild_only()
    async def warn(self, ctx: Context, member: Member, *, reason: str):
        """
        warn a member
        """

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        if member == self.bot.user:
            raise CommandError(translations.cannot_warn)

        user_embed = Embed(
            title=translations.warn,
            description=translations.f_warned(ctx.author.mention, ctx.guild.name, reason),
            colour=Colours.ModTools,
        )
        server_embed = Embed(title=translations.warn, description=translations.warned_response, colour=Colours.ModTools)
        try:
            await member.send(embed=user_embed)
        except (Forbidden, HTTPException):
            server_embed.description = translations.no_dm + "\n\n" + server_embed.description
            server_embed.colour = Colours.error
        await db_thread(Warn.create, member.id, str(member), ctx.author.id, reason)
        await ctx.send(embed=server_embed)
        await send_to_changelog_mod(
            ctx.guild, ctx.message, Colours.changelog["warn"], translations.log_warned, member, reason
        )

    async def get_user(self, guild: Guild, user: Union[Member, User, int]) -> Union[Member, User]:
        if isinstance(user, Member):
            return user
        if isinstance(user, User):
            return guild.get_member(user.id) or user

        if member := guild.get_member(user):
            return member
        try:
            return await self.bot.fetch_user(user)
        except (NotFound, HTTPException):
            raise CommandError(translations.user_not_found)

    @commands.command()
    @Permission.mute.check
    @guild_only()
    async def mute(self, ctx: Context, user: Union[Member, User, int], days: DurationConverter, *, reason: str):
        """
        mute a member
        set days to `inf` for a permanent mute
        """

        days: Optional[int]

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        mute_role: Role = await get_mute_role(ctx.guild)
        user: Union[Member, User] = await self.get_user(ctx.guild, user)

        if user == self.bot.user or await is_teamler(user):
            raise CommandError(translations.cannot_mute)

        if isinstance(user, Member):
            await user.add_roles(mute_role)
            await user.move_to(None)

        active_mutes: List[Mute] = await db_thread(db.all, Mute, active=True, member=user.id)
        if any(
            mute.days == -1
            or days is not None
            and datetime.utcnow() + timedelta(days=days) <= mute.timestamp + timedelta(days=mute.days)
            for mute in active_mutes
        ):
            raise CommandError(translations.already_muted)
        for mute in active_mutes:
            await db_thread(Mute.upgrade, mute.id, ctx.author.id)

        user_embed = Embed(title=translations.mute, colour=Colours.ModTools)
        server_embed = Embed(title=translations.mute, description=translations.muted_response, colour=Colours.ModTools)

        if days is not None:
            await db_thread(Mute.create, user.id, str(user), ctx.author.id, days, reason, bool(active_mutes))
            user_embed.description = translations.f_muted(ctx.author.mention, ctx.guild.name, days, reason)
            await send_to_changelog_mod(
                ctx.guild,
                ctx.message,
                Colours.changelog["mute"],
                translations.log_muted,
                user,
                reason,
                duration=translations.f_log_field_days(days),
            )
        else:
            await db_thread(Mute.create, user.id, str(user), ctx.author.id, -1, reason, bool(active_mutes))
            user_embed.description = translations.f_muted_inf(ctx.author.mention, ctx.guild.name, reason)
            await send_to_changelog_mod(
                ctx.guild,
                ctx.message,
                Colours.changelog["mute"],
                translations.log_muted,
                user,
                reason,
                duration=translations.log_field_days_infinity,
            )

        try:
            await user.send(embed=user_embed)
        except (Forbidden, HTTPException):
            server_embed.description = translations.no_dm + "\n\n" + server_embed.description
            server_embed.colour = Colours.error

        await ctx.send(embed=server_embed)

    @commands.command()
    @Permission.mute.check
    @guild_only()
    async def unmute(self, ctx: Context, user: Union[Member, User, int], *, reason: str):
        """
        unmute a member
        """

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        mute_role: Role = await get_mute_role(ctx.guild)
        user: Union[Member, User] = await self.get_user(ctx.guild, user)

        was_muted = False
        if isinstance(user, Member) and mute_role in user.roles:
            was_muted = True
            await user.remove_roles(mute_role)

        for mute in await db_thread(db.all, Mute, active=True, member=user.id):
            await db_thread(Mute.deactivate, mute.id, ctx.author.id, reason)
            was_muted = True
        if not was_muted:
            raise CommandError(translations.not_muted)

        embed = Embed(title=translations.unmute, description=translations.unmuted_response, colour=Colours.ModTools)
        await ctx.send(embed=embed)
        await send_to_changelog_mod(
            ctx.guild, ctx.message, Colours.changelog["unmute"], translations.log_unmuted, user, reason
        )

    @commands.command()
    @Permission.kick.check
    @guild_only()
    async def kick(self, ctx: Context, member: Member, *, reason: str):
        """
        kick a member
        """

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        if member == self.bot.user or await is_teamler(member):
            raise CommandError(translations.cannot_kick)

        if not ctx.guild.me.guild_permissions.kick_members:
            raise CommandError(translations.cannot_kick_permissions)

        if member.top_role >= ctx.guild.me.top_role or member.id == ctx.guild.owner_id:
            raise CommandError(translations.cannot_kick)

        await db_thread(Kick.create, member.id, str(member), ctx.author.id, reason)
        await send_to_changelog_mod(
            ctx.guild, ctx.message, Colours.changelog["kick"], translations.log_kicked, member, reason
        )

        user_embed = Embed(
            title=translations.kick,
            description=translations.f_kicked(ctx.author.mention, ctx.guild.name, reason),
            colour=Colours.ModTools,
        )
        server_embed = Embed(title=translations.kick, description=translations.kicked_response, colour=Colours.ModTools)

        try:
            await member.send(embed=user_embed)
        except (Forbidden, HTTPException):
            server_embed.description = translations.no_dm + "\n\n" + server_embed.description
            server_embed.colour = Colours.error

        await member.kick(reason=reason)

        await ctx.send(embed=server_embed)

    @commands.command()
    @Permission.ban.check
    @guild_only()
    async def ban(
        self,
        ctx: Context,
        user: Union[Member, User, int],
        ban_days: DurationConverter,
        delete_days: int,
        *,
        reason: str,
    ):
        """
        ban a user
        set ban_days to `inf` for a permanent ban
        """

        ban_days: Optional[int]

        if not ctx.guild.me.guild_permissions.ban_members:
            raise CommandError(translations.cannot_ban_permissions)

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)
        if not 0 <= delete_days <= 7:
            raise CommandError(translations.invalid_duration)

        user: Union[Member, User] = await self.get_user(ctx.guild, user)

        if user == self.bot.user or await is_teamler(user):
            raise CommandError(translations.cannot_ban)
        if isinstance(user, Member) and (user.top_role >= ctx.guild.me.top_role or user.id == ctx.guild.owner_id):
            raise CommandError(translations.cannot_ban)

        active_bans: List[Ban] = await db_thread(db.all, Ban, active=True, member=user.id)
        if any(
            ban.days == -1
            or ban_days is not None
            and datetime.utcnow() + timedelta(days=ban_days) <= ban.timestamp + timedelta(days=ban.days)
            for ban in active_bans
        ):
            raise CommandError(translations.already_banned)
        for ban in active_bans:
            await db_thread(Ban.upgrade, ban.id, ctx.author.id)
        for mute in await db_thread(db.all, Mute, active=True, member=user.id):
            await db_thread(Mute.upgrade, mute.id, ctx.author.id)

        user_embed = Embed(title=translations.ban, colour=Colours.ModTools)
        server_embed = Embed(title=translations.ban, description=translations.banned_response, colour=Colours.ModTools)

        if ban_days is not None:
            await db_thread(Ban.create, user.id, str(user), ctx.author.id, ban_days, reason, bool(active_bans))
            user_embed.description = translations.f_banned(ctx.author.mention, ctx.guild.name, ban_days, reason)
            await send_to_changelog_mod(
                ctx.guild,
                ctx.message,
                Colours.changelog["ban"],
                translations.log_banned,
                user,
                reason,
                duration=translations.f_log_field_days(ban_days),
            )
        else:
            await db_thread(Ban.create, user.id, str(user), ctx.author.id, -1, reason, bool(active_bans))
            user_embed.description = translations.f_banned_inf(ctx.author.mention, ctx.guild.name, reason)
            await send_to_changelog_mod(
                ctx.guild,
                ctx.message,
                Colours.changelog["ban"],
                translations.log_banned,
                user,
                reason,
                duration=translations.log_field_days_infinity,
            )

        try:
            await user.send(embed=user_embed)
        except (Forbidden, HTTPException):
            server_embed.description = translations.no_dm + "\n\n" + server_embed.description
            server_embed.colour = Colours.error

        await ctx.guild.ban(user, delete_message_days=delete_days, reason=reason)

        await ctx.send(embed=server_embed)

    @commands.command()
    @Permission.ban.check
    @guild_only()
    async def unban(self, ctx: Context, user: Union[User, int], *, reason: str):
        """
        unban a user
        """

        if len(reason) > 900:
            raise CommandError(translations.reason_too_long)

        if not ctx.guild.me.guild_permissions.ban_members:
            raise CommandError(translations.cannot_unban_permissions)

        user: Union[Member, User] = await self.get_user(ctx.guild, user)

        was_banned = True
        try:
            await ctx.guild.unban(user, reason=reason)
        except HTTPException:
            was_banned = False

        for ban in await db_thread(db.all, Ban, active=True, member=user.id):
            was_banned = True
            await db_thread(Ban.deactivate, ban.id, ctx.author.id, reason)
        if not was_banned:
            raise CommandError(translations.not_banned)

        embed = Embed(title=translations.unban, description=translations.unbanned_response, colour=Colours.ModTools)
        await ctx.send(embed=embed)
        await send_to_changelog_mod(
            ctx.guild, ctx.message, Colours.changelog["unban"], translations.log_unbanned, user, reason
        )

    async def get_stats_user(
        self, ctx: Context, user: Optional[Union[User, int]]
    ) -> Tuple[Union[User, int], int, bool]:
        arg_passed = len(ctx.message.content.strip(await get_prefix()).split()) >= 2
        if user is None:
            if arg_passed:
                raise UserInputError
            user = ctx.author

        if isinstance(user, int):
            if not 0 <= user < (1 << 63):
                raise UserInputError
            try:
                user = await self.bot.fetch_user(user)
            except NotFound:
                pass

        user_id = user if isinstance(user, int) else user.id

        if user_id != ctx.author.id and not await Permission.view_stats.check_permissions(ctx.author):
            raise CommandError(translations.stats_not_allowed)

        return user, user_id, arg_passed

    @commands.command()
    async def stats(self, ctx: Context, user: Optional[Union[User, int]] = None):
        """
        show statistics about a user
        """

        user, user_id, arg_passed = await self.get_stats_user(ctx, user)
        await update_join_date(self.bot.guilds[0], user_id)

        embed = Embed(title=translations.stats, color=Colours.stats)
        if isinstance(user, int):
            embed.set_author(name=str(user))
        else:
            embed.set_author(name=f"{user} ({user_id})", icon_url=user.avatar_url)

        async def count(cls):
            if cls is Report:
                active = await db_thread(db.count, cls, reporter=user_id)
            else:
                active = await db_thread(db.count, cls, mod=user_id)
            passive = await db_thread(db.count, cls, member=user_id)
            return translations.f_active_passive(active, passive)

        embed.add_field(name=translations.reported_cnt, value=await count(Report))
        embed.add_field(name=translations.warned_cnt, value=await count(Warn))
        embed.add_field(name=translations.muted_cnt, value=await count(Mute))
        embed.add_field(name=translations.kicked_cnt, value=await count(Kick))
        embed.add_field(name=translations.banned_cnt, value=await count(Ban))

        if (ban := await db_thread(db.first, Ban, member=user_id, active=True)) is not None:
            if ban.days != -1:
                expiry_date: datetime = ban.timestamp + timedelta(days=ban.days)
                days_left = (expiry_date - datetime.utcnow()).days + 1
                status = translations.f_status_banned_days(ban.days, days_left)
            else:
                status = translations.status_banned
        elif (mute := await db_thread(db.first, Mute, member=user_id, active=True)) is not None:
            if mute.days != -1:
                expiry_date: datetime = mute.timestamp + timedelta(days=mute.days)
                days_left = (expiry_date - datetime.utcnow()).days + 1
                status = translations.f_status_muted_days(mute.days, days_left)
            else:
                status = translations.status_muted
        elif (member := self.bot.guilds[0].get_member(user_id)) is not None:
            status = translations.f_member_since(member.joined_at.strftime("%d.%m.%Y %H:%M:%S"))
        else:
            status = translations.not_a_member
        embed.add_field(name=translations.status, value=status, inline=False)

        if arg_passed:
            await ctx.send(embed=embed)
        else:
            try:
                await ctx.author.send(embed=embed)
            except (Forbidden, HTTPException):
                raise CommandError(translations.could_not_send_dm)
            await ctx.message.add_reaction(name_to_emoji["white_check_mark"])

    @commands.command(aliases=["userlog", "ulog", "uinfo", "userinfo"])
    async def userlogs(self, ctx: Context, user: Optional[Union[User, int]] = None):
        """
        show moderation log of a user
        """

        user, user_id, arg_passed = await self.get_stats_user(ctx, user)
        await update_join_date(self.bot.guilds[0], user_id)

        out: List[Tuple[datetime, str]] = [(snowflake_time(user_id), translations.ulog_created)]
        for join in await db_thread(db.all, Join, member=user_id):
            out.append((join.timestamp, translations.ulog_joined))
        for leave in await db_thread(db.all, Leave, member=user_id):
            out.append((leave.timestamp, translations.ulog_left))
        for username_update in await db_thread(db.all, UsernameUpdate, member=user_id):
            if not username_update.nick:
                msg = translations.f_ulog_username_updated(username_update.member_name, username_update.new_name)
            elif username_update.member_name is None:
                msg = translations.f_ulog_nick_set(username_update.new_name)
            elif username_update.new_name is None:
                msg = translations.f_ulog_nick_cleared(username_update.member_name)
            else:
                msg = translations.f_ulog_nick_updated(username_update.member_name, username_update.new_name)
            out.append((username_update.timestamp, msg))
        for report in await db_thread(db.all, Report, member=user_id):
            out.append((report.timestamp, translations.f_ulog_reported(f"<@{report.reporter}>", report.reason)))
        for warn in await db_thread(db.all, Warn, member=user_id):
            out.append((warn.timestamp, translations.f_ulog_warned(f"<@{warn.mod}>", warn.reason)))
        for mute in await db_thread(db.all, Mute, member=user_id):
            text = [translations.ulog_muted, translations.ulog_muted_inf][mute.days == -1][mute.is_upgrade].format
            if mute.days == -1:
                out.append((mute.timestamp, text(f"<@{mute.mod}>", mute.reason)))
            else:
                out.append((mute.timestamp, text(f"<@{mute.mod}>", mute.days, mute.reason)))
            if not mute.active and not mute.upgraded:
                if mute.unmute_mod is None:
                    out.append((mute.deactivation_timestamp, translations.ulog_unmuted_expired))
                else:
                    out.append(
                        (
                            mute.deactivation_timestamp,
                            translations.f_ulog_unmuted(f"<@{mute.unmute_mod}>", mute.unmute_reason),
                        )
                    )
        for kick in await db_thread(db.all, Kick, member=user_id):
            if kick.mod is not None:
                out.append((kick.timestamp, translations.f_ulog_kicked(f"<@{kick.mod}>", kick.reason)))
            else:
                out.append((kick.timestamp, translations.ulog_autokicked))
        for ban in await db_thread(db.all, Ban, member=user_id):
            text = [translations.ulog_banned, translations.ulog_banned_inf][ban.days == -1][ban.is_upgrade].format
            if ban.days == -1:
                out.append((ban.timestamp, text(f"<@{ban.mod}>", ban.reason)))
            else:
                out.append((ban.timestamp, text(f"<@{ban.mod}>", ban.days, ban.reason)))
            if not ban.active and not ban.upgraded:
                if ban.unban_mod is None:
                    out.append((ban.deactivation_timestamp, translations.ulog_unbanned_expired))
                else:
                    out.append(
                        (
                            ban.deactivation_timestamp,
                            translations.f_ulog_unbanned(f"<@{ban.unban_mod}>", ban.unban_reason),
                        )
                    )
        for log in await db_thread(db.all, InviteLog, applicant=user_id):  # type: InviteLog
            if log.approved:
                out.append((log.timestamp, translations.f_ulog_invite_approved(f"<@{log.mod}>", log.guild_name)))
            else:
                out.append((log.timestamp, translations.f_ulog_invite_removed(f"<@{log.mod}>", log.guild_name)))

        out.sort()
        embed = Embed(title=translations.userlogs, color=Colours.userlog)
        if isinstance(user, int):
            embed.set_author(name=str(user))
        else:
            embed.set_author(name=f"{user} ({user_id})", icon_url=user.avatar_url)
        for row in out:
            name = row[0].strftime("%d.%m.%Y %H:%M:%S")
            value = row[1]
            embed.add_field(name=name, value=value, inline=False)

        embed.set_footer(text=translations.utc_note)

        if arg_passed:
            await send_long_embed(ctx, embed)
        else:
            try:
                await send_long_embed(ctx.author, embed)
            except (Forbidden, HTTPException):
                raise CommandError(translations.could_not_send_dm)
            await ctx.message.add_reaction(name_to_emoji["white_check_mark"])

    @commands.command()
    @Permission.init_join_log.check
    @guild_only()
    async def init_join_log(self, ctx: Context):
        """
        create a join log entry for each server member
        """

        guild: Guild = ctx.guild

        def init():
            for member in guild.members:  # type: Member
                Join.update(member.id, str(member), member.joined_at)

        embed = Embed(
            title=translations.init_join_log,
            description=translations.f_filling_join_log(len(guild.members)),
            color=Colours.ModTools,
        )
        msg: Message = await ctx.send(embed=embed)
        await db_thread(init)
        embed.description += "\n\n" + translations.join_log_filled
        await msg.edit(embed=embed)
