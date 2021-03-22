import logging
from typing import Optional

from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from discord import TextChannel, Embed, Member, VoiceState, Message
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Bot, Context

from colours import Colours
from permissions import Permission
from util import send_to_changelog
import re

async def get_max_hops() -> int:
    """
    Retrieves the channel hops per minute in order for a message to appear
    """

    return await Settings.get(int, "alert_channel_warn_channel_hops", 5)


class AlertChannelCog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.user_hops: dict[int, int] = {}

    async def on_ready(self):
        try:
            self.hop_loop.start()
        except RuntimeError:
            self.hop_loop.restart()

    async def get_alert_channel(self) -> Optional[TextChannel]:
        """
        Retrieves the alert-channel of the specified guild
        """

        alert_channel_id: int = await Settings.get(int, "alert_channel", -1)
        if alert_channel_id <= 0:
            return None

        text_channel: TextChannel = self.bot.get_channel(alert_channel_id)
        if not text_channel:
            await Settings.set(int, "alert_channel", -1)

        return text_channel

    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        """
        Checks for channel-hopping
        """

        if before.channel == after.channel:
            return

        hops: int = self.user_hops.setdefault(member.id, 0) + 1
        temp_max: int = await get_max_hops()

        if temp_max <= 0 or self.user_hops[member.id] < temp_max:
            self.user_hops[member.id] = hops
            return

        del self.user_hops[member.id]
        embed = Embed(title=translations.alert_channel_hop, color=Colours.AlertChannel)
        embed.add_field(name=translations.member, value=member.mention)
        embed.add_field(name=translations.alert_channel_hop_current_channel, value=after.channel.name)

        if ch := await self.get_alert_channel():
            await ch.send(embed=embed)
        else:
            logging.warning("No alert channel so far")

    async def on_member_join(self, member: Member):
        if re.match(r"^[a-zA-Z0-9 ./<>?;:\"'`!@#$%^&*()\[\]{}_+=|\\-]+$", member.display_name):
            return

        embed = Embed(title=translations.illegal_username, color=Colours.AlertChannel)
        embed.add_field(name=translations.member, value=member.mention)

        if (channel := await self.get_alert_channel()) is not None:
            await channel.send(embed=embed)

    async def on_message(self, message: Message):
        """
        Checks whether a message contains the teamrole mention and sends an alert if necessary
        """
        channel: TextChannel = await self.get_alert_channel()
        if channel is None:
            return

        teamrole_id: int = await Settings.get(int, "team_role", -1)
        if teamrole_id == -1:
            return

        teamrole: int = message.guild.get_role(teamrole_id)
        if teamrole not in message.role_mentions:
            return

        embed = Embed(title=translations.team_role_pinged, color=Colours.AlertChannel, timestamp=message.created_at)
        embed.set_author(name=message.author.name, icon_url=message.author.avatar_url)
        embed.add_field(name=translations.channel, value=message.channel.mention)
        embed.add_field(name=translations.member, value=message.author.mention)
        embed.add_field(name=translations.message_link,
                        value="[" + translations.link_click_here + "](" + message.jump_url + ")")
        embed.add_field(name=translations.message, value=message.content, inline=False)
        await channel.send(embed=embed)

    @tasks.loop(minutes=1)
    async def hop_loop(self):
        """
        Once a minute, all possible channel hops are being reset
        """

        self.user_hops = {}

    @commands.group(name="alert")
    @Permission.log_manage.check
    async def alert_channel(self, ctx: Context):
        """
        Configures the alert channel
        """

        if ctx.subcommand_passed:
            return

        embed = Embed(title=translations.alert_channel, colour=Colours.AlertChannel)
        channel: TextChannel = await self.get_alert_channel()
        embed.add_field(
            name=translations.alert_channel_get, value=channel.mention if channel else translations.none, inline=False
        )
        embed.add_field(
            name=translations.alert_channel_hop_current_amount, value=str(await get_max_hops()), inline=False
        )
        await ctx.send(embed=embed)

    @alert_channel.command(name="set")
    async def alertch_set(self, ctx: Context, channel: TextChannel):
        """
        Updated the alert channel
        """

        await Settings.set(int, "alert_channel", channel.id)

        embed = Embed(
            title=translations.alert_channel, description=translations.alert_channel_set, color=Colours.AlertChannel
        )
        embed.add_field(name=translations.channel, value=channel.mention)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_alert_channel_log_updated(channel.mention))

    @alert_channel.command(name="unset")
    async def alertch_unset(self, ctx: Context):
        """
        Unsets the alert channel
        """

        await Settings.set(int, "alert_channel", 0)

        embed = Embed(
            title=translations.alert_channel, description=translations.alert_channel_set, color=Colours.AlertChannel
        )
        embed.add_field(name=translations.channel, value=translations.none)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.alert_channel_log_unset)

    @alert_channel.command(name="hops")
    async def alertch_set_hops(self, ctx: Context, amount: Optional[int]):
        """
        Updates the value of minimum hops per minute in order for a message to occur (<=0: no limit)
        """

        if amount is not None:
            await Settings.set(int, "alert_channel_warn_channel_hops", amount)
            embed = Embed(
                title=translations.alert_channel_hop,
                description=translations.alert_channel_hop_set_amount,
                colour=Colours.AlertChannel,
            )
            embed.add_field(name=translations.alert_channel_hop_new_amount, value=str(amount))
            await ctx.send(embed=embed)
            await send_to_changelog(ctx.guild, translations.f_alert_channel_hop_log_updated(str(amount)))
        else:
            embed = Embed(title=translations.alert_channel_hop, colour=Colours.AlertChannel)
            embed.add_field(name=translations.alert_channel_hop_current_amount, value=str(await get_max_hops()))
            await ctx.send(embed=embed)
