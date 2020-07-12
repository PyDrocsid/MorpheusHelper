from discord import Embed
from discord.ext.commands import Context, Cog, command, Bot, Group


class HelpCog(Cog):

    def __init__(self, bot: Bot):
        self.bot = bot

    @command(pass_context=True)
    async def help(self, ctx: Context, *args):
        """
        Shows this message
        """
        global embed
        await ctx.send_help(args)
        if len(args) == 0:
            embed = Embed(title="Command Help", color=0x008080)
            for cog in self.bot.cogs:
                cog = self.bot.get_cog(cog)
                title = cog.qualified_name
                description = ""
                for command in cog.get_commands():
                    description += command.name + " | " + command.short_doc + "\n"
                embed.add_field(name=title, value=description, inline=False)

            title = "No Category"
            description = ""

            for command in self.bot.commands:
                if command.cog is None:
                    description += command.name + " | " + command.short_doc + "\n"

            embed.add_field(name=title, value=description, inline=False)

            embed.add_field(name="** **",
                            value="Type {}help <command> for more info on a command.".format(
                                self.bot.command_prefix) + "\n" + "Type {}help <cog> for more info on a cog.".format(
                                self.bot.command_prefix),
                            inline=False)

            await ctx.send(embed=embed)

        elif len(args) == 1:
            try:
                try:
                    # Command Help for grouped commands
                    group: Group = self.bot.get_command(args[0])
                    command = self.bot.get_command(args[0])
                    executing = self.bot.command_prefix + "[" + command.name + (
                        "|" if len(command.aliases) != 0 else "") + "|".join(
                        command.aliases) + "]"

                    if len(command.aliases) == 0:
                        executing = self.bot.command_prefix + command.name

                    embed = Embed(title="Command Help for " + args[0], description=executing, color=0x008080)

                    subcommand_description = ""
                    for c in group.commands:
                        subcommand_description += c.name + (" | " + c.short_doc if len(c.short_doc) != 0 else "") + "\n"

                    embed.add_field(name="Subcommands", value=subcommand_description, inline=False)
                    embed.add_field(name="Description", value=command.short_doc, inline=False)
                    await ctx.send(embed=embed)
                except:
                    # Command Help for none group commands
                    command = self.bot.get_command(args[0])
                    executing = self.bot.command_prefix + "[" + command.name + (
                        "|" if len(command.aliases) != 0 else "") + "|".join(
                        command.aliases) + "]"

                    if len(command.aliases) == 0:
                        executing = self.bot.command_prefix + command.name

                    embed = Embed(title="Command Help for " + args[0], description=executing, color=0x008080)
                    embed.add_field(name="Description", value=command.short_doc)
                    await ctx.send(embed=embed)
            except:
                # Cog help
                found = False
                for x in self.bot.cogs:
                    for y in args:
                        if x == y:
                            embed = Embed(title="Cog Commands for " + args[0], color=0x008080)
                            for command in self.bot.get_cog(y).get_commands():
                                embed.add_field(name=command.name, value=command.short_doc, inline=False)
                            found = True

                if not found:
                    embed = Embed(title="This Cog or Command does not exists!", color=0xff0000)

                await ctx.send(embed=embed)
