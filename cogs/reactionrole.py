from typing import Optional, Tuple

from PyDrocsid.database import db_thread, db
from PyDrocsid.emoji_converter import EmojiConverter
from PyDrocsid.events import StopEventHandling
from PyDrocsid.translations import translations
from discord import Message, Role, PartialEmoji, TextChannel, Member, NotFound, Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError, UserInputError

from models.reactionrole import ReactionRole
from permissions import Permission
from util import send_to_changelog, get_colour


async def get_role(message: Message, emoji: PartialEmoji, add: bool) -> Optional[Tuple[Role, bool]]:
    link: Optional[ReactionRole] = await db_thread(ReactionRole.get, message.channel.id, message.id, str(emoji))
    if link is None:
        return None
    if link.auto_remove and not add:
        return None

    role: Optional[Role] = message.guild.get_role(link.role_id)
    if role is None:
        await db_thread(db.delete, link)
        return None

    return role, link.auto_remove


class ReactionRoleCog(Cog, name="ReactionRole"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_raw_reaction_add(self, message: Message, emoji: PartialEmoji, member: Member):
        if member.bot or message.guild is None:
            return

        result = await get_role(message, emoji, True)
        if result is not None:
            try:
                await member.add_roles(result[0])
            except NotFound:
                pass
            if result[1]:
                await message.remove_reaction(emoji, member)
            raise StopEventHandling

    async def on_raw_reaction_remove(self, message: Message, emoji: PartialEmoji, member: Member):
        if member.bot or message.guild is None:
            return

        result = await get_role(message, emoji, False)
        if result is not None:
            try:
                await member.remove_roles(result[0])
            except NotFound:
                pass
            raise StopEventHandling

    @commands.group(aliases=["rr"])
    @Permission.rr_manage.check
    @guild_only()
    async def reactionrole(self, ctx: Context):
        """
        manage reactionrole
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @reactionrole.command(name="list", aliases=["l", "?"])
    async def reactionrole_list(self, ctx: Context, msg: Optional[Message] = None):
        """
        list configured reactionrole links
        """

        embed = Embed(title=translations.reactionrole, colour=get_colour(self))
        if msg is None:
            channels = {}
            for link in await db_thread(db.all, ReactionRole):  # type: ReactionRole
                channel: Optional[TextChannel] = ctx.guild.get_channel(link.channel_id)
                if channel is None:
                    await db_thread(db.delete, link)
                    continue
                try:
                    msg: Message = await channel.fetch_message(link.message_id)
                except NotFound:
                    await db_thread(db.delete, link)
                    continue
                if ctx.guild.get_role(link.role_id) is None:
                    await db_thread(db.delete, link)
                    continue
                channels.setdefault(channel, {}).setdefault(msg.jump_url, set())
                channels[channel][msg.jump_url].add(link.emoji)

            if not channels:
                embed.colour = get_colour("red")
                embed.description = translations.no_reactionrole_links
            else:
                embed.description = "\n\n".join(f"{channel.mention}: " + "\n".join(
                    f"[{' '.join(emojis)}]({url})" for url, emojis in messages.items()) for channel, messages in
                                                channels.items())
        else:
            out = []
            for link in await db_thread(
                    db.all, ReactionRole, channel_id=msg.channel.id, message_id=msg.id
            ):  # type: ReactionRole
                channel: Optional[TextChannel] = ctx.guild.get_channel(link.channel_id)
                if channel is None or await channel.fetch_message(link.message_id) is None:
                    await db_thread(db.delete, link)
                    continue
                role: Optional[Role] = ctx.guild.get_role(link.role_id)
                if role is None:
                    await db_thread(db.delete, link)
                    continue
                if link.auto_remove:
                    out.append(translations.f_rr_link_auto_remove(link.emoji, role.name))
                else:
                    out.append(translations.f_rr_link(link.emoji, role.mention))
            if not out:
                embed.colour = get_colour("red")
                embed.description = translations.no_reactionrole_links_for_msg
            else:
                embed.description = "\n".join(out)
        await ctx.send(embed=embed)

    @reactionrole.command(name="add", aliases=["a", "+"])
    async def reactionrole_add(self, ctx: Context, msg: Message, emoji: EmojiConverter, role: Role, auto_remove: bool):
        """
        add a new reactionrole link
        """

        emoji: PartialEmoji

        if await db_thread(ReactionRole.get, msg.channel.id, msg.id, str(emoji)) is not None:
            raise CommandError(translations.rr_link_already_exists)
        if not msg.channel.permissions_for(msg.guild.me).add_reactions:
            raise CommandError(translations.rr_link_not_created_no_permissions)

        if role >= ctx.me.top_role:
            raise CommandError(translations.f_link_not_created_too_high(role, ctx.me.top_role))
        if role.managed or role.is_default():
            raise CommandError(translations.f_link_not_created_managed_role(role))

        await db_thread(ReactionRole.create, msg.channel.id, msg.id, str(emoji), role.id, auto_remove)
        await msg.add_reaction(emoji)
        embed = Embed(title=translations.reactionrole, colour=get_colour(self),
                      description=translations.rr_link_created)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_rr_link_created(emoji, role.id, msg.jump_url))

    @reactionrole.command(name="remove", aliases=["r", "del", "d", "-"])
    async def reactionrole_remove(self, ctx: Context, msg: Message, emoji: EmojiConverter):
        """
        remove a reactionrole link
        """

        emoji: PartialEmoji

        if (link := await db_thread(ReactionRole.get, msg.channel.id, msg.id, str(emoji))) is None:
            raise CommandError(translations.rr_link_not_found)

        await db_thread(db.delete, link)
        for reaction in msg.reactions:
            if str(emoji) == str(reaction.emoji):
                await reaction.clear()
        embed = Embed(title=translations.reactionrole, colour=get_colour(self),
                      description=translations.rr_link_removed)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_rr_link_removed(emoji, msg.jump_url))
