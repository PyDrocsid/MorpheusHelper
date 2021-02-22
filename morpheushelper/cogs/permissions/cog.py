import asyncio
from typing import Optional

from discord import Embed
from discord.ext import commands
from discord.ext.commands import guild_only, Context, Converter, BadArgument, CommandError, UserInputError

from PyDrocsid.cog import Cog
from PyDrocsid.config import Config
from PyDrocsid.permission import BasePermissionLevel
from PyDrocsid.translations import translations
from PyDrocsid.util import send_long_embed
from cogs.contributor import Contributor
from .colors import Colors
from .permissions import Permission
from ..logging import send_to_changelog


async def list_permissions(ctx: Context, title: str, min_level: BasePermissionLevel):
    out = {}
    levels = await asyncio.gather(*[permission.resolve() for permission in Config.PERMISSIONS])
    for permission, level in zip(Config.PERMISSIONS, levels):
        if min_level.level >= level.level:
            out.setdefault((level.level, level.description), []).append(
                f"`{permission.name}` - {permission.description}"
            )

    embed = Embed(title=title, colour=Colors.error)
    if not out:
        embed.description = translations.no_permissions
        await ctx.send(embed=embed)
        return

    embed.colour = Colors.Permissions
    for (_, name), lines in sorted(out.items(), reverse=True):
        embed.add_field(name=name, value="\n".join(sorted(lines)), inline=False)

    await send_long_embed(ctx, embed)


class PermissionLevelConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> BasePermissionLevel:
        for level in Config.PERMISSION_LEVELS:  # type: BasePermissionLevel
            if argument.lower() in level.aliases:
                return level

        raise BadArgument(translations.invalid_permission_level)


class PermissionsCog(Cog, name="Permissions"):
    CONTRIBUTORS = [Contributor.Defelo, Contributor.wolflu]
    PERMISSIONS = Permission

    @commands.group(aliases=["perm", "p"])
    @guild_only()
    async def permissions(self, ctx: Context):
        """
        manage bot permissions
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @permissions.command(name="list", aliases=["show", "l", "?"])
    @Permission.view_all_permissions.check
    async def permissions_list(self, ctx: Context, min_level: Optional[PermissionLevelConverter]):
        """
        list all permissions
        """

        if min_level is None:
            min_level = Config.DEFAULT_PERMISSION_LEVEL(...)

        await list_permissions(ctx, translations.permissions_title, min_level)

    @permissions.command(name="my", aliases=["m", "own", "o"])
    @Permission.view_own_permissions.check
    async def permissions_my(self, ctx: Context):
        """
        list all permissions granted to the user
        """

        min_level: BasePermissionLevel = await Config.PERMISSION_LEVELS.get_permission_level(ctx.author)
        await list_permissions(ctx, translations.my_permissions_title, min_level)

    @permissions.command(name="set", aliases=["s", "="])
    @Permission.manage_permissions.check
    async def permissions_set(self, ctx: Context, permission_name: str, level: PermissionLevelConverter):
        """
        configure bot permissions
        """

        level: BasePermissionLevel
        for permission in Config.PERMISSIONS:
            if permission.name.lower() == permission_name.lower():
                break
        else:
            raise CommandError(translations.invalid_permission)

        max_level: BasePermissionLevel = await Config.PERMISSION_LEVELS.get_permission_level(ctx.author)
        if max(level.level, (await permission.resolve()).level) > max_level.level:
            raise CommandError(translations.cannot_manage_permission_level)

        await permission.set(level)

        description = permission.name, level.description
        embed = Embed(
            title=translations.permissions_title,
            colour=Colors.Permissions,
            description=translations.f_permission_set(*description),
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_permission_set(*description))
