from typing import Optional

from PyDrocsid.database import db_thread, db
from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.events import StopEventHandling
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from discord import TextChannel, Message, Guild, Member, MessageType, HTTPException, PartialEmoji, Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, guild_only, CommandError, UserInputError

from models.reactionpin_channel import ReactionPinChannel
from permissions import Permission
from util import make_error, send_to_changelog, get_colour

EMOJI = name_to_emoji["pushpin"]


class ReactionPinCog(Cog, name="ReactionPin"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_raw_reaction_add(self, message: Message, emoji: PartialEmoji, member: Member):
        if str(emoji) != EMOJI or member.bot or message.guild is None:
            return

        access: bool = await Permission.rp_pin.check_permissions(member)
        if not (await db_thread(db.get, ReactionPinChannel, message.channel.id) is not None or access):
            return

        blocked_role = await Settings.get(int, "mute_role", None)
        if access or (member == message.author and all(r.id != blocked_role for r in member.roles)):
            if message.type != MessageType.default:
                await message.remove_reaction(emoji, member)
                await message.channel.send(embed=make_error(translations.msg_not_pinned_system))
                raise StopEventHandling
            try:
                await message.pin()
            except HTTPException:
                await message.remove_reaction(emoji, member)
                await message.channel.send(embed=make_error(translations.msg_not_pinned_limit))
        else:
            await message.remove_reaction(emoji, member)

        raise StopEventHandling

    async def on_raw_reaction_remove(self, message: Message, emoji: PartialEmoji, member: Member):
        if str(emoji) != EMOJI or member.bot or message.guild is None:
            return

        access: bool = await Permission.rp_pin.check_permissions(member)
        is_reactionpin_channel = await db_thread(db.get, ReactionPinChannel, message.channel.id) is not None
        if message.pinned and (access or (is_reactionpin_channel and member == message.author)):
            await message.unpin()
            raise StopEventHandling

    async def on_raw_reaction_clear(self, message: Message):
        if message.guild is not None and message.pinned:
            await message.unpin()
        raise StopEventHandling

    async def on_self_message(self, message: Message):
        if message.guild is None:
            return

        pin_messages_enabled = await Settings.get(bool, "reactionpin_pin_message", True)
        if not pin_messages_enabled and message.author == self.bot.user and message.type == MessageType.pins_add:
            await message.delete()
            raise StopEventHandling

    @commands.group(aliases=["rp"])
    @Permission.rp_manage.check
    @guild_only()
    async def reactionpin(self, ctx: Context):
        """
        manage ReactionPin
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @reactionpin.command(name="list", aliases=["l", "?"])
    async def reactionpin_list(self, ctx: Context):
        """
        list configured channels
        """

        out = []
        guild: Guild = ctx.guild
        for channel in await db_thread(db.all, ReactionPinChannel):
            text_channel: Optional[TextChannel] = guild.get_channel(channel.channel)
            if text_channel is None:
                continue
            out.append(f":small_orange_diamond: {text_channel.mention}")
        embed = Embed(title=translations.reactionpin, colour=get_colour(self))
        if out:
            embed.description = translations.whitelisted_channels_header + "\n" + "\n".join(out)
        else:
            embed.colour = get_colour("red")
            embed.description = translations.no_whitelisted_channels
        await ctx.send(embed=embed)

    @reactionpin.command(name="add", aliases=["a", "+"])
    async def reactionpin_add(self, ctx: Context, channel: TextChannel):
        """
        add channel to whitelist
        """

        if await db_thread(db.get, ReactionPinChannel, channel.id) is not None:
            raise CommandError(translations.channel_already_whitelisted)

        await db_thread(ReactionPinChannel.create, channel.id)
        embed = Embed(title=translations.reactionpin, colour=get_colour(self),
                      description=translations.channel_whitelisted)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_channel_whitelisted_rp(channel.mention))

    @reactionpin.command(name="remove", aliases=["del", "r", "d", "-"])
    async def reactionpin_remove(self, ctx: Context, channel: TextChannel):
        """
        remove channel from whitelist
        """

        if (row := await db_thread(db.get, ReactionPinChannel, channel.id)) is None:
            raise CommandError(translations.channel_not_whitelisted)

        await db_thread(db.delete, row)
        embed = Embed(title=translations.reactionpin, colour=get_colour(self), description=translations.channel_removed)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_channel_removed_rp(channel.mention))

    @reactionpin.command(name="pin_message", aliases=["pm"])
    async def reactionpin_pin_message(self, ctx: Context, enabled: bool = None):
        """
        enable/disable "pinned a message" notification
        """

        embed = Embed(title=translations.reactionpin, colour=get_colour(self))
        if enabled is None:
            if await Settings.get(bool, "reactionpin_pin_message", True):
                embed.description = translations.pin_messages_enabled
            else:
                embed.description = translations.pin_messages_disabled
        else:
            await Settings.set(bool, "reactionpin_pin_message", enabled)
            if enabled:
                embed.description = translations.pin_messages_now_enabled
                await send_to_changelog(ctx.guild, translations.pin_messages_now_enabled)
            else:
                embed.description = translations.pin_messages_now_disabled
                await send_to_changelog(ctx.guild, translations.pin_messages_now_disabled)
        await ctx.send(embed=embed)
