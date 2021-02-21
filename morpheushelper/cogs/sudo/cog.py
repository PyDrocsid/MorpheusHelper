import sys

from PyDrocsid.permission import BasePermission
from discord import TextChannel, Message
from discord.ext import commands
from discord.ext.commands import check, Context, CheckFailure

from PyDrocsid.cog import Cog
from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.events import call_event_handlers
from cogs.contributor import Contributor
from permissions import sudo_active, PermissionLevel


@check
def is_sudoer(ctx: Context) -> bool:
    if ctx.author.id != 370876111992913922:
        raise CheckFailure(f"{ctx.author.mention} is not in the sudoers file. This incident will be reported.")

    return True


class SudoCog(Cog, name="Sudo"):
    CONTRIBUTORS = [Contributor.Defelo]
    PERMISSIONS = BasePermission

    def __init__(self):
        self.sudo_cache: dict[TextChannel, Message] = {}

    async def on_command_error(self, ctx: Context, _):
        if ctx.author.id == 370876111992913922:
            self.sudo_cache[ctx.channel] = ctx.message

    @commands.command(hidden=True)
    @is_sudoer
    async def sudo(self, ctx: Context, *, cmd: str):
        message: Message = ctx.message
        message.content = ctx.prefix + cmd

        if cmd == "!!" and ctx.channel in self.sudo_cache:
            message.content = self.sudo_cache.pop(ctx.channel).content

        sudo_active.set(True)
        await self.bot.process_commands(message)

    @commands.command()
    @PermissionLevel.OWNER.check
    async def reload(self, ctx: Context):
        await call_event_handlers("ready")
        await ctx.message.add_reaction(name_to_emoji["white_check_mark"])

    @commands.command()
    @PermissionLevel.OWNER.check
    async def stop(self, ctx: Context):
        await ctx.message.add_reaction(name_to_emoji["white_check_mark"])
        await self.bot.close()

    @commands.command()
    @PermissionLevel.OWNER.check
    async def kill(self, ctx: Context):
        await ctx.message.add_reaction(name_to_emoji["white_check_mark"])
        sys.exit(1)
