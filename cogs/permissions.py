from typing import Optional

from discord import Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, Converter, BadArgument, CommandError

from permission import Permission
from translations import translations
from util import permission_level, ADMINISTRATOR, get_permission_level, MODERATOR, SUPPORTER, PUBLIC, send_help


async def list_permissions(ctx: Context, title: str, min_level: int):
    out = {}
    for permission in Permission:  # type: Permission
        level = await permission.resolve()
        if min_level >= level:
            out.setdefault(level, []).append(f"`{permission.name}` - {permission.description}")

    embed = Embed(title=title, colour=0xCF0606)
    if not out:
        embed.description = translations.no_permissions
        await ctx.send(embed=embed)
        return

    embed.colour = 0x256BE6
    for level, lines in sorted(out.items(), reverse=True):
        embed.add_field(name=translations.permission_levels[level], value="\n".join(sorted(lines)), inline=False)

    await ctx.send(embed=embed)


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
            await send_help(ctx, PermissionsCog.permissions)

    @permissions.command(name="list", aliases=["show", "l", "?"])
    @permission_level(Permission.view_all_permissions)
    async def list_permissions(self, ctx: Context, min_level: Optional[PermissionLevelConverter]):
        """
        list all permissions
        """

        await list_permissions(ctx, translations.permissions_title, ADMINISTRATOR if min_level is None else min_level)

    @permissions.command(name="my", aliases=["m", "own", "o"])
    @permission_level(Permission.view_own_permissions)
    async def my_permissions(self, ctx: Context):
        """
        list all permissions granted to the user
        """

        await list_permissions(ctx, translations.my_permissions_title, await get_permission_level(ctx.author))

    @permissions.command(name="set", aliases=["s", "="])
    @permission_level(ADMINISTRATOR)
    async def set_permission(self, ctx: Context, permission: str, level: PermissionLevelConverter):
        """
        configure bot permissions
        """

        level: int
        try:
            permission: Permission = Permission[permission.lower()]
        except KeyError:
            raise CommandError(translations.invalid_permission)

        await permission.set(level)
        await ctx.send(translations.f_permission_set(permission.name, translations.permission_levels[level]))
