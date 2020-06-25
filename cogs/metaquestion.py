import re

from discord import Embed, Member, Message, PartialEmoji, Forbidden
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, guild_only

from database import run_in_thread, db
from models.mediaonly_channel import MediaOnlyChannel
from permission import Permission
from translations import translations
from util import check_permissions

WASTEBASKET = b"\xf0\x9f\x97\x91\xef\xb8\x8f".decode()


def make_embed(requested_by: Member) -> Embed:
    embed = Embed(title=translations.metaquestion_title, url="http://metafrage.de/")
    embed.description = translations.metaquestion_description
    embed.set_footer(
        text=translations.f_requested_by(requested_by, requested_by.id),
        icon_url=requested_by.avatar_url,
    )
    embed.add_field(
        name=translations.mq_advantages_title,
        value="\n".join("- " + e for e in translations.mq_advantages),
        inline=False,
    )
    embed.add_field(
        name=translations.mq_disadvantages_title,
        value="\n".join("- " + e for e in translations.mq_disadvantages),
        inline=False,
    )
    return embed


class MetaQuestionCog(Cog, name="Metafragen"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_raw_reaction_add(
        self, message: Message, emoji: PartialEmoji, member: Member
    ) -> bool:
        if member == self.bot.user:
            return True

        if emoji.name == "metaquestion":
            media_only = (
                not await check_permissions(member, Permission.mo_bypass)
                and await run_in_thread(db.get, MediaOnlyChannel, message.channel.id)
                is not None
            )
            if (
                message.author.bot
                or not message.channel.permissions_for(member).send_messages
                or media_only
            ):
                try:
                    await message.remove_reaction(emoji, member)
                except Forbidden:
                    pass
                return False

            for reaction in message.reactions:
                if reaction.emoji == emoji:
                    if reaction.me:
                        return False
                    break
            await message.add_reaction(emoji)
            msg: Message = await message.channel.send(
                message.author.mention, embed=make_embed(member)
            )
            await msg.add_reaction(WASTEBASKET)
            return False
        elif emoji.name == WASTEBASKET:
            for embed in message.embeds:
                pattern = (
                    re.escape(translations.requested_by)
                    .replace("\\{\\}", "{}")
                    .format(r".*?#\d{4}", r"(\d+)")
                )
                if (
                    match := re.match("^" + pattern + "$", embed.footer.text)
                ) is not None:
                    author_id = int(match.group(1))
                    if not (
                        author_id == member.id
                        or await check_permissions(member, Permission.mq_reduce)
                    ):
                        try:
                            await message.remove_reaction(emoji, member)
                        except Forbidden:
                            pass
                        return False
                    break
            else:
                return True

            await message.clear_reactions()
            await message.edit(
                content=message.content + " http://metafrage.de/", embed=None
            )
            return False

        return True

    @commands.command(name="metafrage", aliases=["mf", "mq", "meta", "metaquestion"])
    @guild_only()
    async def metaquestion(self, ctx: Context):
        """
        display information about meta questions
        """

        message: Message = await ctx.send(embed=make_embed(ctx.author))
        await message.add_reaction(WASTEBASKET)
