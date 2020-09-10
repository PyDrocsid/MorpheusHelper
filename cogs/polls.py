import re
from datetime import datetime
from typing import Optional

import discord
from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.translations import translations
from discord import Embed, Message
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, guild_only, UserInputError, CommandError

MAX_OPTIONS = 20  # Discord reactions limit

default_emojis = [name_to_emoji[f"regional_indicator_{x}"] for x in "abcdefghijklmnopqrstuvwyz"]


class PollsCog(Cog, name="Polls"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(usage="<question>\n[emoji1] <option1>\n[emojiX] [optionX]", aliases=["vote"])
    @guild_only()
    async def poll(self, ctx: Context):
        """
        Starts a poll. Multiline options can be specified using a `\\` at the end of a line
        """
        lines = [line.replace("\x00", "\n") for line in ctx.message.content.replace("\\\n", "\x00").split("\n")]

        if len(lines) < 2:
            raise UserInputError("Missing options")
        if len(lines) > MAX_OPTIONS + 1:
            raise CommandError(translations.f_too_many_options(MAX_OPTIONS))

        question = lines[0][len(ctx.prefix + ctx.invoked_with) + 1:]
        options = [PollOption(ctx, line, i) for i, line in enumerate(lines[1:])]

        embed = Embed(title=question,
                      description=translations.vote_explanation,
                      color=0xff1010,
                      timestamp=datetime.utcnow())
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        for option in options:
            embed.add_field(name="** **", value=str(option), inline=False)

        poll: discord.Message = await ctx.send(embed=embed)

        for option in options:
            await poll.add_reaction(option.emoji)

    @commands.command(aliases=["yn"])
    @guild_only()
    async def yesno(self, ctx: Context, message: Optional[Message] = None):
        """
        adds thumbsup and thumbsdown reactions to the message
        """

        if message is None or message.guild is None:
            message = ctx.message

        if message.channel.permissions_for(ctx.author).add_reactions:
            await message.add_reaction(name_to_emoji["thumbsup"])
            await message.add_reaction(name_to_emoji["thumbsdown"])


class PollOption:
    def __init__(self, ctx: Context, line: str, number: int):
        if len(line) == 0:
            raise UserInputError("Empty option")

        emoji_candidate = line.split(" ")[0]

        custom_emoji_match = re.fullmatch(r"<a?:([a-zA-Z0-9_])+:([0-9]+)>", emoji_candidate)
        if custom_emoji := ctx.bot.get_emoji(int(custom_emoji_match.group(2))) if custom_emoji_match else None:
            self.emoji = custom_emoji
            self.option = line[custom_emoji_match.end():].strip()
        elif (unicode_emoji := emoji_candidate) in name_to_emoji.values():
            self.emoji = unicode_emoji
            self.option = line[len(unicode_emoji):].strip()
        else:
            self.emoji = default_emojis[number]
            self.option = line

    def __str__(self):
        return f"{self.emoji} {self.option}" if self.option else self.emoji
