from discord import Embed, Member, Message, PartialEmoji, Forbidden, NotFound, HTTPException
from discord.ext import commands
from discord.ext.commands import Context, guild_only

from PyDrocsid.cog import Cog
from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.events import StopEventHandling
from PyDrocsid.translations import translations
from PyDrocsid.util import check_wastebasket
from .colors import Colors
from .permissions import Permission
from ..contributor import Contributor


def make_embed(requested_by: Member) -> Embed:
    embed = Embed(title=translations.metaquestion_title, url="http://metafrage.de/", colour=Colors.MetaQuestions)
    embed.description = translations.metaquestion_description
    embed.set_footer(text=translations.f_requested_by(requested_by, requested_by.id), icon_url=requested_by.avatar_url)
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
    CONTRIBUTORS = [Contributor.Defelo]
    PERMISSIONS = Permission

    async def on_raw_reaction_add(self, message: Message, emoji: PartialEmoji, member: Member):
        if message.guild is None or member == self.bot.user:
            return

        if emoji.name == "metaquestion":
            if message.author.bot or not message.channel.permissions_for(member).send_messages:
                try:
                    await message.remove_reaction(emoji, member)
                except Forbidden:
                    pass
                raise StopEventHandling

            for reaction in message.reactions:
                if reaction.emoji == emoji:
                    if reaction.me:
                        raise StopEventHandling
                    break
            await message.add_reaction(emoji)
            msg: Message = await message.channel.send(message.author.mention, embed=make_embed(member))
            await msg.add_reaction(name_to_emoji["wastebasket"])
            raise StopEventHandling

        if await check_wastebasket(message, member, emoji, translations.requested_by, Permission.mq_reduce):
            await message.clear_reactions()
            embed: Embed = message.embeds[0]
            embed.title = embed.url
            embed.description = ""
            embed.clear_fields()
            await message.edit(embed=embed)
            raise StopEventHandling

    @commands.command(aliases=["mf", "mq", "meta", "metafrage"])
    @guild_only()
    async def metaquestion(self, ctx: Context):
        """
        display information about meta questions
        """

        message: Message = await ctx.send(embed=make_embed(ctx.author))
        await message.add_reaction(name_to_emoji["wastebasket"])
        try:
            await ctx.message.delete()
        except (Forbidden, NotFound, HTTPException):
            pass
