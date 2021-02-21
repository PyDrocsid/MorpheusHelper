import string

from discord import Embed

from PyDrocsid.settings import Settings

from PyDrocsid.translations import translations
from discord.ext import commands
from discord.ext.commands import guild_only, Context, CommandError

from PyDrocsid.cog import Cog
from .permissions import Permission
from ..contributor import Contributor
from colours import Colours
from util import send_to_changelog


async def get_prefix() -> str:
    return await Settings.get(str, "prefix", ".")


async def set_prefix(new_prefix: str):
    await Settings.set(str, "prefix", new_prefix)


class SettingsCog(Cog, name="Settings"):
    CONTRIBUTORS = [Contributor.Defelo]
    PERMISSIONS = Permission

    @commands.command(name="prefix")
    @Permission.change_prefix.check
    @guild_only()
    async def change_prefix(self, ctx: Context, new_prefix: str):
        """
        change the bot prefix
        """

        if not 0 < len(new_prefix) <= 16:
            raise CommandError(translations.invalid_prefix_length)

        valid_chars = set(string.ascii_letters + string.digits + string.punctuation)
        if any(c not in valid_chars for c in new_prefix):
            raise CommandError(translations.prefix_invalid_chars)

        await set_prefix(new_prefix)
        embed = Embed(title=translations.prefix, description=translations.prefix_updated, colour=Colours.prefix)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_prefix_updated(new_prefix))
