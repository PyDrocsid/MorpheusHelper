from typing import Optional

from discord import Role, Guild, Member
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, CommandError, CheckFailure, check, guild_only

from database import run_in_thread
from models.settings import Settings
from permission import Permission
from translations import translations
from util import send_to_changelog, permission_level


@check
async def private_only(ctx: Context):
    if ctx.guild is not None:
        raise CheckFailure(translations.private_only)

    return True


class VerificationCog(Cog, name="Verification"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_verification_role(self) -> Optional[Role]:
        guild: Guild = self.bot.guilds[0]
        return guild.get_role(await run_in_thread(Settings.get, int, "verification_role", -1))

    @commands.command(name="verify")
    @private_only
    async def verify(self, ctx: Context, *, password: str):
        mode: int = await run_in_thread(Settings.get, int, "verification_mode", 0)
        role: Optional[Role] = await self.get_verification_role()
        correct_password: str = await run_in_thread(Settings.get, str, "verification_password")
        if mode == 0 or role is None or correct_password is None:
            raise CommandError(translations.verification_disabled)

        member: Member = self.bot.guilds[0].get_member(ctx.author.id)
        if (mode == 1) == (role in member.roles):
            raise CommandError(translations.already_verified)

        if password != correct_password:
            raise CommandError(translations.password_incorrect)

        if mode == 1:
            await member.add_roles(role)
        elif mode == 2:
            await member.remove_roles(role)
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
                await ctx.send_help(self.verification)
            return

        mode: int = await run_in_thread(Settings.get, int, "verification_mode", 0)
        role: Optional[Role] = await self.get_verification_role()
        password: str = await run_in_thread(Settings.get, str, "verification_password")
        if mode == 0 or role is None or password is None:
            await ctx.send(translations.verification_disabled)
            return

        out = [
            translations.verification_mode[mode - 1],
            translations.f_verification_password(password),
            translations.f_verification_role(role.name, role.id),
        ]
        await ctx.send("\n".join(out))

    @verification.command(name="mode", aliases=["m"])
    async def verification_mode(self, ctx: Context, mode: str):
        """
        configure verification mode:
        off:     disable verification command
        normal:  assign a specific role
        reverse: remove a specific role
        """

        mode: Optional[int] = {"off": 0, "normal": 1, "reverse": 2}.get(mode.lower())
        if mode is None:
            await ctx.send_help(self.verification_mode)
            return

        await run_in_thread(Settings.set, int, "verification_mode", mode)
        await ctx.send(translations.verification_mode_configured[mode])
        await send_to_changelog(ctx.guild, translations.verification_mode_configured[mode])

    @verification.command(name="role", aliases=["r"])
    async def verification_role(self, ctx: Context, *, role: Role):
        """
        configure verification role
        """

        if role > ctx.me.top_role:
            raise CommandError(translations.f_role_not_set_too_high(role, ctx.me.top_role))
        if role.managed:
            raise CommandError(translations.f_role_not_set_managed_role(role))

        await run_in_thread(Settings.set, int, "verification_role", role.id)
        await ctx.send(translations.verification_role_configured)
        await send_to_changelog(ctx.guild, translations.f_log_verification_role_configured(role.name, role.id))

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
