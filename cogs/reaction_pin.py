from typing import Optional

from discord import (
    RawReactionActionEvent,
    TextChannel,
    Message,
    Guild,
    Member,
    RawReactionClearEvent,
    MessageType,
    Role,
    HTTPException,
)
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, guild_only, CommandError

from database import run_in_thread, db
from models.reactionpin_channel import ReactionPinChannel
from models.settings import Settings
from util import permission_level, make_error, check_access

EMOJI = chr(int("1f4cc", 16))


class ReactionPinCog(Cog, name="ReactionPin"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        channel: TextChannel = self.bot.get_channel(payload.channel_id)
        message: Message = await channel.fetch_message(payload.message_id)
        guild: Guild = channel.guild
        if guild is None:
            return
        member: Member = guild.get_member(payload.user_id)
        access: bool = await check_access(member) > 0
        if str(payload.emoji) == EMOJI and (
            await run_in_thread(db.get, ReactionPinChannel, channel.id) is not None or access
        ):
            blocked_role = await run_in_thread(Settings.get, int, "reactionpin_blocked_role", None)
            if (payload.user_id == message.author.id and all(r.id != blocked_role for r in member.roles)) or access:
                try:
                    await message.pin()
                except HTTPException:
                    await message.remove_reaction(payload.emoji, self.bot.get_user(payload.user_id))
                    await channel.send(
                        make_error(
                            "Message could not be pinned, because 50 messages are already pinned in this channel."
                        )
                    )
            else:
                await message.remove_reaction(payload.emoji, self.bot.get_user(payload.user_id))

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        channel: TextChannel = self.bot.get_channel(payload.channel_id)
        message: Message = await channel.fetch_message(payload.message_id)
        guild: Guild = channel.guild
        if guild is None:
            return
        access: bool = await check_access(guild.get_member(payload.user_id)) > 0
        if str(payload.emoji) == EMOJI:
            if (
                await run_in_thread(db.get, ReactionPinChannel, channel.id) is not None
                and payload.user_id == message.author.id
            ) or access:
                await message.unpin()

    @Cog.listener()
    async def on_raw_reaction_clear(self, payload: RawReactionClearEvent):
        channel: TextChannel = self.bot.get_channel(payload.channel_id)
        message: Message = await channel.fetch_message(payload.message_id)
        guild: Guild = channel.guild
        if guild is None:
            return
        await message.unpin()

    @Cog.listener()
    async def on_message(self, message: Message):
        if message.guild is None:
            return
        pin_messages_enabled = await run_in_thread(Settings.get, bool, "reactionpin_pin_message", True)
        if not pin_messages_enabled and message.author == self.bot.user and message.type == MessageType.pins_add:
            await message.delete()

    @commands.group(aliases=["rp"])
    @permission_level(1)
    @guild_only()
    async def reactionpin(self, ctx: Context):
        """
        manage ReactionPin
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help("reactionpin")

    @reactionpin.command(name="list")
    async def list_channels(self, ctx: Context):
        """
        list configured channels
        """

        out = []
        guild: Guild = ctx.guild
        for channel in await run_in_thread(db.query, ReactionPinChannel):
            text_channel: Optional[TextChannel] = guild.get_channel(channel.channel)
            if text_channel is None:
                continue
            out.append(f"- {text_channel.mention}")
        if out:
            await ctx.send("Whitelisted channels:\n" + "\n".join(out))
        else:
            await ctx.send("No whitelisted channels.")

    @reactionpin.command(name="add")
    async def add_channel(self, ctx: Context, channel: TextChannel):
        """
        add channel to whitelist
        """

        if await run_in_thread(db.get, ReactionPinChannel, channel.id) is not None:
            raise CommandError("Channel is already whitelisted")

        await run_in_thread(ReactionPinChannel.create, channel.id)
        await ctx.send("Channel has been whitelisted.")

    @reactionpin.command(name="remove")
    async def remove_channel(self, ctx: Context, channel: TextChannel):
        """
        remove channel from whitelist
        """

        if (row := await run_in_thread(db.get, ReactionPinChannel, channel.id)) is None:
            raise CommandError("Channel is not whitelisted")

        await run_in_thread(db.delete, row)
        await ctx.send("Channel has been removed from the whitelist.")

    @reactionpin.command(name="pin_message")
    async def change_pin_message(self, ctx: Context, enabled: bool = None):
        """
        enable/disable "pinned a message" notification
        """

        if enabled is None:
            if await run_in_thread(Settings.get, bool, "reactionpin_pin_message", True):
                await ctx.send("Pin Messages are enabled.")
            else:
                await ctx.send("Pin Messages are disabled.")
        else:
            await run_in_thread(Settings.set, bool, "reactionpin_pin_message", enabled)
            if enabled:
                await ctx.send("Pin Messages have been enabled.")
            else:
                await ctx.send("Pin Messages have been disabled.")

    @reactionpin.command(name="blocked_role")
    async def change_blocked_role(self, ctx: Context, role: Role = None):
        """
        change the blocked role
        """

        if role is None:
            role_id: Optional[int] = await run_in_thread(Settings.get, int, "reactionpin_blocked_role", None)
            if role_id is None or (role := ctx.guild.get_role(role_id)) is None:
                await ctx.send("No blocked role configured.")
            else:
                await ctx.send(f"Blocked role: `@{role}`")
        else:
            await run_in_thread(Settings.set, int, "reactionpin_blocked_role", role.id)
            await ctx.send("Blocked role has been updated.")
