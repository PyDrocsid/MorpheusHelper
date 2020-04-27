from typing import Optional

from discord import Message, Role, PartialEmoji, TextChannel, Member
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.reactionrole import ReactionRole
from util import permission_level, send_to_changelog, FixedEmojiConverter


async def get_role(message: Message, emoji: PartialEmoji) -> Optional[Role]:
    link: Optional[ReactionRole] = await run_in_thread(ReactionRole.get, message.channel.id, message.id, str(emoji))
    if link is not None:
        role: Optional[Role] = message.guild.get_role(link.role_id)
        if role is None:
            await run_in_thread(db.delete, link)
            return None

        return role


class ReactionRoleCog(Cog, name="ReactionRole"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_raw_reaction_add(self, message: Message, emoji: PartialEmoji, member: Member) -> bool:
        role: Optional[Role] = await get_role(message, emoji)
        if role is not None:
            await member.add_roles(role)
            return True
        return False

    async def on_raw_reaction_remove(self, message: Message, emoji: PartialEmoji, member: Member) -> bool:
        role: Optional[Role] = await get_role(message, emoji)
        if role is not None:
            await member.remove_roles(role)
            return True
        return False

    @commands.group(name="reactionrole", aliases=["rr"])
    @permission_level(1)
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
                msg: Optional[Message] = await channel.fetch_message(link.message_id)
                if msg is None or ctx.guild.get_role(link.role_id) is None:
                    await run_in_thread(db.delete, link)
                    continue
                channels.setdefault(channel, {}).setdefault(msg.jump_url, set())
                channels[channel][msg.jump_url].add(link.emoji)

            if not channels:
                await ctx.send("No ReactionRole links have been created yet.")
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
                out.append(f"{link.emoji} -> `@{role}`")
            if not out:
                await ctx.send("No ReactionRole links have been created yet for this message.")
            else:
                await ctx.send("\n".join(out))

    @reactionrole.command(name="add", aliases=["a", "+"])
    async def add(self, ctx: Context, message: Message, emoji: FixedEmojiConverter, role: Role):
        """
        add a new reactionrole link
        """

        emoji: PartialEmoji

        if await run_in_thread(ReactionRole.get, message.channel.id, message.id, str(emoji)) is not None:
            raise CommandError("A link already exists for this reaction on this message.")

        await run_in_thread(ReactionRole.create, message.channel.id, message.id, str(emoji), role.id)
        await message.add_reaction(emoji)
        await ctx.send("Link has been created successfully.")
        await send_to_changelog(
            ctx.guild, f"ReactionRole link for {emoji} -> `@{role}` has been created on {message.jump_url}"
        )

    @reactionrole.command(name="remove", aliases=["r", "del", "d", "-"])
    async def remove(self, ctx: Context, message: Message, emoji: FixedEmojiConverter):
        """
        remove a reactionrole link
        """

        emoji: PartialEmoji

        if (link := await run_in_thread(ReactionRole.get, message.channel.id, message.id, str(emoji))) is None:
            raise CommandError("Such a link does not exist.")

        await run_in_thread(db.delete, link)
        for reaction in message.reactions:
            if str(emoji) == str(reaction.emoji):
                await reaction.clear()
        await ctx.send("Link has been removed successfully.")
        await send_to_changelog(ctx.guild, f"ReactionRole link for {emoji} has been deleted on {message.jump_url}")
