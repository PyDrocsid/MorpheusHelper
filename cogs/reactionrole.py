from typing import Optional, Tuple

from discord import Message, Role, PartialEmoji, TextChannel, Member, NotFound
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.reactionrole import ReactionRole
from permission import Permission
from translations import translations
from util import permission_level, send_to_changelog, FixedEmojiConverter


async def get_role(message: Message, emoji: PartialEmoji, add: bool) -> Optional[Tuple[Role, bool]]:
    link: Optional[ReactionRole] = await run_in_thread(ReactionRole.get, message.channel.id, message.id, str(emoji))
    if link is None:
        return None
    if link.auto_remove and not add:
        return None

    role: Optional[Role] = message.guild.get_role(link.role_id)
    if role is None:
        await run_in_thread(db.delete, link)
        return None

    return role, link.auto_remove


class ReactionRoleCog(Cog, name="ReactionRole"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_raw_reaction_add(self, message: Message, emoji: PartialEmoji, member: Member) -> bool:
        if member.bot:
            return False

        result = await get_role(message, emoji, True)
        if result is not None:
            try:
                await member.add_roles(result[0])
            except NotFound:
                pass
            if result[1]:
                await message.remove_reaction(emoji, member)
            return True
        return False

    async def on_raw_reaction_remove(self, message: Message, emoji: PartialEmoji, member: Member) -> bool:
        if member.bot:
            return False

        result = await get_role(message, emoji, False)
        if result is not None:
            try:
                await member.remove_roles(result[0])
            except NotFound:
                pass
            return True
        return False

    @commands.group(name="reactionrole", aliases=["rr"])
    @permission_level(Permission.rr_manage)
    @guild_only()
    async def reactionrole(self, ctx: Context):
        """
        manage reactionrole
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(ReactionRoleCog.reactionrole)

    @reactionrole.command(name="list", aliases=["l", "?"])
    async def list_links(self, ctx: Context, message: Optional[Message] = None):
        """
        list configured reactionrole links
        """

        if message is None:
            channels = {}
            for link in await run_in_thread(db.all, ReactionRole):  # type: ReactionRole
                channel: Optional[TextChannel] = ctx.guild.get_channel(link.channel_id)
                if channel is None:
                    await run_in_thread(db.delete, link)
                    continue
                try:
                    msg: Message = await channel.fetch_message(link.message_id)
                except NotFound:
                    await run_in_thread(db.delete, link)
                    continue
                if ctx.guild.get_role(link.role_id) is None:
                    await run_in_thread(db.delete, link)
                    continue
                channels.setdefault(channel, {}).setdefault(msg.jump_url, set())
                channels[channel][msg.jump_url].add(link.emoji)

            if not channels:
                await ctx.send(translations.no_reactionrole_links)
            else:
                await ctx.send(
                    "\n\n".join(
                        f"{channel.mention}:\n"
                        + "\n".join(url + " " + " ".join(emojis) for url, emojis in messages.items())
                        for channel, messages in channels.items()
                    )
                )
        else:
            out = []
            for link in await run_in_thread(
                db.all, ReactionRole, channel_id=message.channel.id, message_id=message.id
            ):  # type: ReactionRole
                channel: Optional[TextChannel] = ctx.guild.get_channel(link.channel_id)
                if channel is None or await channel.fetch_message(link.message_id) is None:
                    await run_in_thread(db.delete, link)
                    continue
                role: Optional[Role] = ctx.guild.get_role(link.role_id)
                if role is None:
                    await run_in_thread(db.delete, link)
                    continue
                if link.auto_remove:
                    out.append(translations.f_rr_link_auto_remove(link.emoji, role.name))
                else:
                    out.append(translations.f_rr_link(link.emoji, role.name))
            if not out:
                await ctx.send(translations.no_reactionrole_links_for_msg)
            else:
                await ctx.send("\n".join(out))

    @reactionrole.command(name="add", aliases=["a", "+"])
    async def add(
        self, ctx: Context, message: Message, emoji: FixedEmojiConverter, role: Role, auto_remove: bool = False
    ):
        """
        add a new reactionrole link
        """

        emoji: PartialEmoji

        if await run_in_thread(ReactionRole.get, message.channel.id, message.id, str(emoji)) is not None:
            raise CommandError(translations.rr_link_already_exists)

        if role > ctx.me.top_role:
            raise CommandError(translations.f_link_not_created_too_high(role, ctx.me.top_role))
        if role.managed or role.is_default():
            raise CommandError(translations.f_link_not_created_managed_role(role))

        await run_in_thread(ReactionRole.create, message.channel.id, message.id, str(emoji), role.id, auto_remove)
        await message.add_reaction(emoji)
        await ctx.send(translations.rr_link_created)
        await send_to_changelog(ctx.guild, translations.f_log_rr_link_created(emoji, role, message.jump_url))

    @reactionrole.command(name="remove", aliases=["r", "del", "d", "-"])
    async def remove(self, ctx: Context, message: Message, emoji: FixedEmojiConverter):
        """
        remove a reactionrole link
        """

        emoji: PartialEmoji

        if (link := await run_in_thread(ReactionRole.get, message.channel.id, message.id, str(emoji))) is None:
            raise CommandError(translations.rr_link_not_found)

        await run_in_thread(db.delete, link)
        for reaction in message.reactions:
            if str(emoji) == str(reaction.emoji):
                await reaction.clear()
        await ctx.send(translations.rr_link_removed)
        await send_to_changelog(ctx.guild, translations.f_log_rr_link_removed(emoji, message.jump_url))
