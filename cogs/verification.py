from typing import Optional, List

from discord import Role, Member, Guild, Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, CommandError, CheckFailure, check, guild_only

from database import run_in_thread, db
from models.settings import Settings
from models.verification_role import VerificationRole
from permission import Permission
from translations import translations
from util import send_to_changelog, permission_level, send_help


@check
async def private_only(ctx: Context):
    if ctx.guild is not None:
        raise CheckFailure(translations.private_only)

    return True


class VerificationCog(Cog, name="Verification"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="verify")
    @private_only
    async def verify(self, ctx: Context, *, password: str):
        correct_password: str = await run_in_thread(Settings.get, str, "verification_password")
        if correct_password is None:
            raise CommandError(translations.verification_disabled)

        if password != correct_password:
            raise CommandError(translations.password_incorrect)

        guild: Guild = self.bot.guilds[0]
        member: Member = guild.get_member(ctx.author.id)
        add: List[Role] = []
        remove: List[Role] = []
        for vrole in await run_in_thread(db.all, VerificationRole):  # type: VerificationRole
            role: Optional[Role] = guild.get_role(vrole.role_id)
            if role is None:
                continue

            if vrole.reverse and role in member.roles:
                remove.append(role)
            elif not vrole.reverse and role not in member.roles:
                add.append(role)
        if not add and not remove:
            raise CommandError(translations.already_verified)

        await member.add_roles(*add)
        await member.remove_roles(*remove)
        await ctx.send(translations.verified)

    @commands.group(name="verification", aliases=["vf"])
    @permission_level(Permission.manage_verification)
    @guild_only()
    async def verification(self, ctx: Context):
        """
        configure verify command
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                await send_help(ctx, self.verification)
            return

        password: str = await run_in_thread(Settings.get, str, "verification_password")

        normal: List[Role] = []
        reverse: List[Role] = []
        for vrole in await run_in_thread(db.all, VerificationRole):  # type: VerificationRole
            role: Optional[Role] = ctx.guild.get_role(vrole.role_id)
            if role is None:
                await run_in_thread(db.delete, vrole)
            else:
                [normal, reverse][vrole.reverse].append(role)

        embed = Embed(title=translations.verification, colour=0xCF0606)
        if password is None or not normal + reverse:
            embed.add_field(name=translations.status, value=translations.verification_disabled, inline=False)
            await ctx.send(embed=embed)
            return

        embed.colour = 0x256BE6
        embed.add_field(name=translations.status, value=translations.verification_enabled, inline=False)
        embed.add_field(name=translations.password, value=f"`{password}`", inline=False)

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
    async def verification_role_add(self, ctx: Context, role: Role, reverse: bool = False):
        """
        add verification role
        """

        if role > ctx.me.top_role:
            raise CommandError(translations.f_role_not_set_too_high(role, ctx.me.top_role))
        if role.managed:
            raise CommandError(translations.f_role_not_set_managed_role(role))

        if await run_in_thread(db.get, VerificationRole, role.id) is not None:
            raise CommandError(translations.verification_role_already_set)

        await run_in_thread(VerificationRole.create, role.id, reverse)
        await ctx.send(translations.verification_role_added)
        if reverse:
            await send_to_changelog(ctx.guild, translations.f_log_verification_role_added_reverse(role.name, role.id))
        else:
            await send_to_changelog(ctx.guild, translations.f_log_verification_role_added(role.name, role.id))

    @verification.command(name="remove", aliases=["r", "del", "d", "-"])
    async def verification_role_remove(self, ctx: Context, *, role: Role):
        """
        remove verification role
        """

        if (row := await run_in_thread(db.get, VerificationRole, role.id)) is None:
            raise CommandError(translations.verification_role_not_set)

        await run_in_thread(db.delete, row)
        await ctx.send(translations.verification_role_removed)
        await send_to_changelog(ctx.guild, translations.f_log_verification_role_removed(role.name, role.id))

    @verification.command(name="password", aliases=["p"])
    async def verification_password(self, ctx: Context, *, password: str):
        """
        configure verification password
        """

        if len(password) > 256:
            raise CommandError(translations.password_too_long)

        await run_in_thread(Settings.set, str, "verification_password", password)
        await ctx.send(translations.verification_password_configured)
        await send_to_changelog(ctx.guild, translations.f_log_verification_password_configured(password))
