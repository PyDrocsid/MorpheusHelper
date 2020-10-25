import re
import string
from datetime import datetime
from typing import Optional, Tuple

from PyDrocsid.emojis import name_to_emoji, emoji_to_name
from PyDrocsid.events import StopEventHandling
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from discord import Embed, Message, PartialEmoji, Member, Forbidden
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, guild_only, CommandError

from permissions import PermissionLevel
from util import is_teamler

MAX_OPTIONS = 20  # Discord reactions limit

default_emojis = [name_to_emoji[f"regional_indicator_{x}"] for x in string.ascii_lowercase]


async def get_teampoll_embed(message: Message) -> Tuple[Optional[Embed], Optional[int]]:
    for embed in message.embeds:
        for i, field in enumerate(embed.fields):
            if translations.status == field.name:
                return embed, i
    return None, None


async def update_reacted_teamlers(message: Message) -> str:
    if (team_role := message.guild.get_role(await Settings.get(int, "team_role"))) is not None:
        teamlers = {*team_role.members}
        for reaction in message.reactions:
            if reaction.me:
                teamlers -= {*await reaction.users().flatten()}
        if teamlers:
            end = [translations.one_teamler_missing, translations.multiple_teamlers_missing][len(teamlers) > 1]
            return " ,".join(map(lambda x: x.mention, teamlers)) + end
        return translations.teampoll_all_voted + " :white_check_mark:"
    return translations.team_role_not_set


class PollsCog(Cog, name="Polls"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_raw_reaction_add(self, message: Message, emoji: PartialEmoji, member: Member):
        if member.bot or message.guild is None:
            return
        embed, index = await get_teampoll_embed(message)
        if embed is not None:
            if not await is_teamler(member):
                try:
                    await message.remove_reaction(emoji, member)
                except Forbidden:
                    pass
                raise StopEventHandling
            for reaction in message.reactions:
                if reaction.emoji == emoji.name and reaction.me:
                    value = await update_reacted_teamlers(message)
                    embed.set_field_at(index, name=translations.status, value=value, inline=False)
                    await message.edit(embed=embed)
                    return

    async def on_raw_reaction_remove(self, message: Message, _, member: Member):
        if member.bot or message.guild is None:
            return
        embed, index = await get_teampoll_embed(message)
        if embed is not None:
            user_reacted = False
            for reaction in message.reactions:
                if reaction.me and member in await reaction.users().flatten():
                    user_reacted = True
                    break
            if not user_reacted and await is_teamler(member):
                value = await update_reacted_teamlers(message)
                embed.set_field_at(index, name=translations.status, value=value, inline=False)
                await message.edit(embed=embed)
                return

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
            title=question, description=translations.vote_explanation, color=0xFF1010, timestamp=datetime.utcnow()
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)

        for option in options:
            embed.add_field(name="** **", value=str(option), inline=False)

        poll: Message = await ctx.send(embed=embed)

        for option in options:
            await poll.add_reaction(option.emoji)

    @commands.command(usage=translations.poll_usage, aliases=["teamvote", "tp"])
    @PermissionLevel.SUPPORTER.check
    @guild_only()
    async def teampoll(self, ctx: Context, *, args: str):
        """
        Starts a poll and shows, which teamler has not voted yet.
         Multiline options can be specified using a `\\` at the end of a line
        """

        question, *options = [line.replace("\x00", "\n") for line in args.replace("\\\n", "\x00").split("\n")]

        if not options:
            raise CommandError(translations.missing_options)
        if len(options) > MAX_OPTIONS:
            raise CommandError(translations.f_too_many_options(MAX_OPTIONS))

        options = [PollOption(ctx, line, i) for i, line in enumerate(options)]

        embed = Embed(
            title=question, description=translations.vote_explanation, color=0xFF1010, timestamp=datetime.utcnow()
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar_url)

        for option in options:
            embed.add_field(name="** **", value=str(option), inline=False)
        if (team_role := ctx.guild.get_role(await Settings.get(int, "team_role"))) is not None:
            if (teamlers := " ,".join(map(lambda x: x.mention, team_role.members))) != "":
                embed.add_field(name=translations.status, value=teamlers, inline=False)
            else:
                raise CommandError(translations.team_role_no_members)
        else:
            raise CommandError(translations.team_role_not_set)

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
