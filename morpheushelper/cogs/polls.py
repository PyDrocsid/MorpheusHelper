import re
import string
from datetime import datetime
from typing import Optional

from PyDrocsid.emojis import name_to_emoji, emoji_to_name
from PyDrocsid.translations import translations
from discord import Embed, Message
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, guild_only, CommandError

from colours import Colours

MAX_OPTIONS = 20  # Discord reactions limit

default_emojis = [name_to_emoji[f"regional_indicator_{x}"] for x in string.ascii_lowercase]


class PollsCog(Cog, name="Polls"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(usage=translations.poll_usage, aliases=["vote"])
    @guild_only()
    async def poll(self, ctx: Context, *, args: str):
        """
        Starts a poll. Multiline options can be specified using a `\\` at the end of a line
        """

        question, *options = [line.replace("\x00", "\n") for line in args.replace("\\\n", "\x00").split("\n")]

        if not options:
            raise CommandError(translations.missing_options)
        if len(options) > MAX_OPTIONS:
            raise CommandError(translations.f_too_many_options(MAX_OPTIONS))

        options = [PollOption(ctx, line, i) for i, line in enumerate(options)]

        embed = Embed(
            title=question, description=translations.vote_explanation, color=Colours.Polls, timestamp=datetime.utcnow()
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)

        for option in options:
            embed.add_field(name="** **", value=str(option), inline=False)

        poll: Message = await ctx.send(embed=embed)

        for option in options:
            await poll.add_reaction(option.emoji)

    @commands.command(aliases=["yn"])
    @guild_only()
    async def yesno(self, ctx: Context, message: Optional[Message] = None, text: Optional[str] = None):
        """
        adds thumbsup and thumbsdown reactions to the message
        """

        if message is None or message.guild is None or text:
            message = ctx.message

        if message.channel.permissions_for(ctx.author).add_reactions:
            await message.add_reaction(name_to_emoji["thumbsup"])
            await message.add_reaction(name_to_emoji["thumbsdown"])


class PollOption:
    def __init__(self, ctx: Context, line: str, number: int):
        if not line:
            raise CommandError(translations.empty_option)

        emoji_candidate, *text = line.split(" ")
        text = " ".join(text)

        custom_emoji_match = re.fullmatch(r"<a?:[a-zA-Z0-9_]+:(\d+)>", emoji_candidate)
        if custom_emoji := ctx.bot.get_emoji(int(custom_emoji_match.group(1))) if custom_emoji_match else None:
            self.emoji = custom_emoji
            self.option = text.strip()
        elif (unicode_emoji := emoji_candidate) in emoji_to_name:
            self.emoji = unicode_emoji
            self.option = text.strip()
        else:
            self.emoji = default_emojis[number]
            self.option = line

    def __str__(self):
        return f"{self.emoji} {self.option}" if self.option else self.emoji
