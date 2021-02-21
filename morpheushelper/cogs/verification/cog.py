from datetime import datetime
from typing import Optional, List

from discord import Role, Member, Guild, Embed
from discord.ext import commands
from discord.ext.commands import Context, CommandError, CheckFailure, check, guild_only, UserInputError

from PyDrocsid.cog import Cog
from PyDrocsid.database import db_thread, db
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from colours import Colours
from util import send_to_changelog
from .models import VerificationRole
from .permissions import Permission
from ..contributor import Contributor


@check
async def private_only(ctx: Context):
    if ctx.guild is not None:
        raise CheckFailure(translations.private_only)

    return True


class VerificationCog(Cog, name="Verification"):
    CONTRIBUTORS = [Contributor.Defelo, Contributor.wolflu]
    PERMISSIONS = Permission

    @commands.command()
    @private_only
    async def verify(self, ctx: Context, *, password: str):
        correct_password: str = await Settings.get(str, "verification_password")
        if correct_password is None:
            raise CommandError(translations.verification_disabled)

        if password != correct_password:
            raise CommandError(translations.password_incorrect)

        guild: Guild = self.bot.guilds[0]
        member: Member = guild.get_member(ctx.author.id)

        delay: int = await Settings.get(int, "verification_delay", -1)
        if delay != -1 and (datetime.utcnow() - member.joined_at).total_seconds() < delay:
            raise CommandError(translations.password_incorrect)

        add: List[Role] = []
        remove: List[Role] = []
        fail = False
        for vrole in await db_thread(db.all, VerificationRole):  # type: VerificationRole
            role: Optional[Role] = guild.get_role(vrole.role_id)
            if role is None:
                continue

            if vrole.reverse:
                if role in member.roles:
                    remove.append(role)
                else:
                    fail = True
            elif not vrole.reverse and role not in member.roles:
                add.append(role)
        if not add and not remove:
            raise CommandError(translations.already_verified)
        if fail:
            raise CommandError(translations.verification_reverse_role_not_assigned)

        await member.add_roles(*add)
        await member.remove_roles(*remove)
        embed = Embed(title=translations.verification, description=translations.verified, colour=Colours.Verification)
        await ctx.send(embed=embed)

    @commands.group(aliases=["vf"])
    @Permission.manage_verification.check
    @guild_only()
    async def verification(self, ctx: Context):
        """
        configure verify command
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        password: str = await Settings.get(str, "verification_password")

        normal: List[Role] = []
        reverse: List[Role] = []
        for vrole in await db_thread(db.all, VerificationRole):  # type: VerificationRole
            role: Optional[Role] = ctx.guild.get_role(vrole.role_id)
            if role is None:
                await db_thread(db.delete, vrole)
            else:
                [normal, reverse][vrole.reverse].append(role)

        embed = Embed(title=translations.verification, colour=Colours.error)
        if password is None or not normal + reverse:
            embed.add_field(name=translations.status, value=translations.verification_disabled, inline=False)
            await ctx.send(embed=embed)
            return

        embed.colour = Colours.Verification
        embed.add_field(name=translations.status, value=translations.verification_enabled, inline=False)
        embed.add_field(name=translations.password, value=f"`{password}`", inline=False)

        delay: int = await Settings.get(int, "verification_delay", -1)
        val = translations.f_x_seconds(delay) if delay != -1 else translations.disabled
        embed.add_field(name=translations.delay, value=val, inline=False)

        if normal:
            embed.add_field(
                name=translations.roles_normal,
                value="\n".join(f":small_orange_diamond: {role.mention}" for role in normal),
            )
        if reverse:
            embed.add_field(
                name=translations.roles_reverse,
                value="\n".join(f":small_blue_diamond: {role.mention}" for role in reverse),
            )

        await ctx.send(embed=embed)

    @verification.command(name="add", aliases=["a", "+"])
    async def verification_add(self, ctx: Context, role: Role, reverse: bool = False):
        """
        add verification role
        if `reverse` is set to `true`, the role is not added but removed during verification.
        the `verify` command will fail if the user does not have the role.
        """

        if role >= ctx.me.top_role:
            raise CommandError(translations.f_role_not_set_too_high(role, ctx.me.top_role))
        if role.managed:
            raise CommandError(translations.f_role_not_set_managed_role(role))

        if await db_thread(db.get, VerificationRole, role.id) is not None:
            raise CommandError(translations.verification_role_already_set)

        await db_thread(VerificationRole.create, role.id, reverse)
        embed = Embed(
            title=translations.verification,
            description=translations.verification_role_added,
            colour=Colours.Verification,
        )
        await ctx.send(embed=embed)
        if reverse:
            await send_to_changelog(ctx.guild, translations.f_log_verification_role_added_reverse(role.name, role.id))
        else:
            await send_to_changelog(ctx.guild, translations.f_log_verification_role_added(role.name, role.id))

    @verification.command(name="remove", aliases=["r", "-"])
    async def verification_remove(self, ctx: Context, *, role: Role):
        """
        remove verification role
        """

        if (row := await db_thread(db.get, VerificationRole, role.id)) is None:
            raise CommandError(translations.verification_role_not_set)

        await db_thread(db.delete, row)
        embed = Embed(
            title=translations.verification,
            description=translations.verification_role_removed,
            colour=Colours.Verification,
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_verification_role_removed(role.name, role.id))

    @verification.command(name="password", aliases=["p"])
    async def verification_password(self, ctx: Context, *, password: str):
        """
        configure verification password
        """

        if len(password) > 256:
            raise CommandError(translations.password_too_long)

        await Settings.set(str, "verification_password", password)
        embed = Embed(
            title=translations.verification,
            description=translations.verification_password_configured,
            colour=Colours.Verification,
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_verification_password_configured(password))

    @verification.command(name="delay", aliases=["d"])
    async def verification_delay(self, ctx: Context, seconds: int):
        """
        configure verification delay
        set to -1 to disable
        """

        if seconds != -1 and not 0 <= seconds < (1 << 31):
            raise CommandError(translations.invalid_duration)

        await Settings.set(int, "verification_delay", seconds)
        embed = Embed(title=translations.verification, colour=Colours.Verification)
        if seconds == -1:
            embed.description = translations.verification_delay_disabled
            await send_to_changelog(ctx.guild, translations.verification_delay_disabled)
        else:
            embed.description = translations.verification_delay_configured
            await send_to_changelog(ctx.guild, translations.f_log_verification_delay_configured(seconds))
        await ctx.send(embed=embed)
