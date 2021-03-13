from typing import Optional, Union, List

from discord import Message, Embed
from discord.ext import commands
from discord.ext.commands import Command, Cog, Group, CommandError, Context

from PyDrocsid.cog import Cog
from PyDrocsid.translations import t
from PyDrocsid.util import can_run_command, send_long_embed
from .colors import Colors

tg = t.g
t = t.help


async def send_help(ctx: Context, command_name: Optional[Union[str, Command]]) -> List[Message]:
    def format_command(cmd: Command) -> str:
        doc = " - " + cmd.short_doc if cmd.short_doc else ""
        return f"`{cmd.name}`{doc}"

    async def add_commands(cog_name: str, cmds: List[Command]):
        desc: List[str] = []
        for cmd in sorted(cmds, key=lambda c: c.name):
            if not cmd.hidden and await can_run_command(cmd, ctx):
                desc.append(format_command(cmd))
        if desc:
            embed.add_field(name=cog_name, value="\n".join(desc), inline=False)

    embed = Embed(title=t.help, color=Colors.help)
    if command_name is None:
        for cog in sorted(ctx.bot.cogs.values(), key=lambda c: c.qualified_name):
            await add_commands(cog.qualified_name, cog.get_commands())
        await add_commands(t.no_category, [command for command in ctx.bot.commands if command.cog is None])

        embed.add_field(name="** **", value=t.help_usage(ctx.prefix), inline=False)

        return await send_long_embed(ctx, embed)

    if isinstance(command_name, str):
        cog: Optional[Cog] = ctx.bot.get_cog(command_name)
        if cog is not None:
            await add_commands(cog.qualified_name, cog.get_commands())
            return await send_long_embed(ctx, embed)

        command: Optional[Union[Command, Group]] = ctx.bot.get_command(command_name)
        if command is None:
            raise CommandError(t.cog_or_command_not_found)
    else:
        command: Command = command_name

    if not await can_run_command(command, ctx):
        raise CommandError(tg.not_allowed)

    description = ctx.prefix
    if command.full_parent_name:
        description += command.full_parent_name + " "
    if command.aliases:
        description += "[" + "|".join([command.name] + command.aliases) + "] "
    else:
        description += command.name + " "
    description += command.signature

    embed.description = f"```css\n{description.strip()}\n```"
    embed.add_field(name=t.description, value=command.help, inline=False)

    if isinstance(command, Group):
        await add_commands(t.subcommands, command.commands)

    return await send_long_embed(ctx, embed)


class HelpCog(Cog, name="Help"):
    @commands.command()
    async def help(self, ctx: Context, *, cog_or_command: Optional[str]):
        """
        Shows this Message
        """

        await send_help(ctx, cog_or_command)
