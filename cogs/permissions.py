from typing import Optional

from discord.ext import commands
from discord.ext.commands import (
    Cog,
    Bot,
    guild_only,
    Context,
    Converter,
    BadArgument,
    CommandError,
)

from permission import Permission
from translations import translations
from util import (
    permission_level,
    ADMINISTRATOR,
    get_permission_level,
    MODERATOR,
    SUPPORTER,
    PUBLIC,
)


async def list_permissions(ctx: Context, min_level: int):
    min_level: int
    out = {}
    for permission in Permission:  # type: Permission
        level = await permission.resolve()
        if min_level >= level:
            out.setdefault(level, []).append(
                f"  {permission.name} ({permission.description})"
            )
    if out:
        await ctx.send(
            "```\n"
            + "\n\n".join(
                "\n".join([translations.permission_levels[level] + ":"] + lines)
                for level, lines in sorted(out.items(), reverse=True)
            )
            + "\n```"
        )
    else:
        await ctx.send(translations.no_permissions)


class PermissionLevelConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        if argument.lower() in ("administrator", "admin", "a"):
            return ADMINISTRATOR
        if argument.lower() in ("moderator", "mod", "m"):
            return MODERATOR
        if argument.lower() in ("supporter", "supp", "s"):
            return SUPPORTER
        if argument.lower() in ("public", "p"):
            return PUBLIC
        raise BadArgument(translations.invalid_permission_level)


class PermissionsCog(Cog, name="Permissions"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(name="permissions", aliases=["perm", "p"])
    @guild_only()
    async def permissions(self, ctx: Context):
        """
        manage bot permissions
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(PermissionsCog.permissions)

    @permissions.command(name="list", aliases=["show", "l", "?"])
    @permission_level(Permission.view_all_permissions)
    async def list_permissions(
        self,
        ctx: Context,
        min_level: Optional[PermissionLevelConverter] = ADMINISTRATOR,
    ):
        """
        list all permissions
        """

        min_level: int
        await list_permissions(ctx, min_level)

    @permissions.command(name="my", aliases=["m", "own", "o"])
    @permission_level(Permission.view_own_permissions)
    async def my_permissions(self, ctx: Context):
        """
        list all permissions granted to the user
        """

        await list_permissions(ctx, await get_permission_level(ctx.author))

    @permissions.command(name="set", aliases=["s", "="])
    @permission_level(ADMINISTRATOR)
    async def set_permission(
        self, ctx: Context, permission: str, level: PermissionLevelConverter
    ):
        """
        configure bot permissions
        """

        level: int
        try:
            permission: Permission = Permission[permission.lower()]
        except KeyError:
            raise CommandError(translations.invalid_permission)

        await permission.set(level)
        await ctx.send(
            translations.f_permission_set(
                permission.name, translations.permission_levels[level]
            )
        )
