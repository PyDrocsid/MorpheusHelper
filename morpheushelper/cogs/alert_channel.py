import logging
from typing import Optional

from PyDrocsid.database import db, db_thread
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from discord import TextChannel, Embed, Guild, Member, VoiceState
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Bot, Context
from discord.utils import get

from colours import Colours
from models.alert_channel import AlertChannel
from permissions import PermissionLevel


async def getAlertChannel(guild: Guild) -> Optional[TextChannel]:
    """
    Retrieves the alert-channel of the specified guild
    """
    alert_channel: AlertChannel = await db_thread(db.get, AlertChannel, guild.id)
    if not alert_channel:
        return None

    text_channel: TextChannel = get(guild.text_channels, id=alert_channel.channel)
    if not text_channel:
        db.delete(alert_channel)

    return text_channel


async def getMaxHops() -> int:
    """
    Retrieves the channel hops per minute in order for a message to appear
    """
    return await Settings.get(int, "alert_channel_warn_channel_hops", 5)


class AlertChannelCog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.user_hops = {}

    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        """
        Checks for channel-hopping
        """
        if not (before.channel and after.channel):
            return
        try:
            self.user_hops[member.id] += 1
        except KeyError:
            self.user_hops[member.id] = 1

        if self.user_hops[member.id] >= (max := await getMaxHops()) and max > 0:
            del self.user_hops[member.id]
            embed = Embed(title=translations.alert_channel_hop, color=Colours.AlertChannel)
            embed.add_field(name=translations.member, value=member.mention)
            embed.add_field(name=translations.alert_channel_hop_current_channel, value=after.channel.mention)
            if ch := await getAlertChannel(member.guild):
                await ch.send(embed=embed)
            else:
                logging.warning("No alert channel so far")

    @tasks.loop(minutes=1)
    async def hop_loop(self):
        # Once a minute, all possible channel hops are being reset
        self.user_hops = {}

    @commands.group(name="alert")
    @PermissionLevel.ADMINISTRATOR.check
    async def alert_channel(self, ctx: Context):
        """
        Configures the alert channel
        """
        if not ctx.subcommand_passed:
            embed = Embed(title=translations.alert_channel, colour=Colours.AlertChannel)
            embed.add_field(name=translations.alert_channel_get,
                            value=(await getAlertChannel(ctx.guild)).mention,
                            inline=False)
            embed.add_field(name=translations.alert_channel_hop_current_amount, value=str(await getMaxHops()),
                            inline=False)
            await ctx.send(embed=embed)

    @alert_channel.command(name="set")
    async def alertch_set(self, ctx: Context, channel: TextChannel):
        """
        Updated the alert channel
        """
        await db_thread(AlertChannel.create, ctx.guild.id, channel.id)

        embed = Embed(title=translations.alert_channel, description=translations.alert_channel_set,
                      color=Colours.AlertChannel)
        embed.add_field(name=translations.channel, value=str(channel))
        await ctx.send(embed=embed)

    @alert_channel.command(name="hops")
    async def alertch_set_hops(self, ctx: Context, amount: Optional[int]):
        """
        Updates the value of minimum hops per minute in order for a message to occur
        """
        if amount:
            await Settings.set(int, "alert_channel_warn_channel_hops", amount)
            embed = Embed(title=translations.alert_channel_hop, description=translations.alert_channel_hop_set_amount,
                          colour=Colours.AlertChannel)
            embed.add_field(name=translations.alert_channel_hop_new_amount, value=str(amount))
            await ctx.send(embed=embed)
        else:
            embed = Embed(title=translations.alert_channel_hop,
                          colour=Colours.AlertChannel)
            embed.add_field(name=translations.alert_channel_hop_current_amount, value=str(await getMaxHops()))
            await ctx.send(embed=embed)
