from discord import Embed, Member, VoiceState
from discord.ext import tasks, commands
from discord.ext.commands import Context, guild_only, UserInputError

from PyDrocsid.cog import Cog
from PyDrocsid.config import Contributor
from PyDrocsid.settings import Settings
from PyDrocsid.translations import t
from cogs.library.moderation.spam_detection.colors import Colors
from cogs.library.moderation.spam_detection.permissions import SpamDetectionPermission
from cogs.library.pubsub import send_to_changelog, send_alert

tg = t.g
t = t.spam_detection


async def get_max_hops() -> int:
    """
    Retrieves the channel hops per minute in order for a message to appear
    """

    return await Settings.get(int, "spam_detection_max_hops", 5)


class SpamDetectionCog(Cog, name="Spam Detection"):
    CONTRIBUTORS = [Contributor.ce_phox, Contributor.Defelo]
    PERMISSIONS = SpamDetectionPermission

    def __init__(self):
        self.user_hops: dict[int, int] = {}

    async def on_ready(self):
        try:
            self.hop_loop.start()
        except RuntimeError:
            self.hop_loop.restart()

    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        """
        Checks for channel-hopping
        """

        if before.channel == after.channel:
            return

        hops: int = self.user_hops.setdefault(member.id, 0) + 1
        max_hops: int = await get_max_hops()

        if max_hops <= 0 or self.user_hops[member.id] < max_hops:
            self.user_hops[member.id] = hops
            return

        del self.user_hops[member.id]
        embed = Embed(title=t.channel_hopping, color=Colors.SpamDetection)
        embed.add_field(name=tg.member, value=member.mention)
        embed.add_field(name=t.member_id, value=member.id)
        embed.set_author(name=str(member), icon_url=member.avatar_url)
        if after.channel:
            embed.add_field(name=t.current_channel, value=after.channel.name)

        await send_alert(member.guild, embed)

    @tasks.loop(minutes=1)
    async def hop_loop(self):
        """
        Once a minute, all possible channel hops are being reset
        """

        self.user_hops.clear()

    @commands.group(aliases=["spam", "sd"])
    @guild_only()
    async def spam_detection(self, ctx: Context):
        """
        view and change spam detection settings
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        embed = Embed(title=t.spam_detection, color=Colors.SpamDetection)

        if (max_hops := await get_max_hops()) <= 0:
            embed.add_field(name=t.channel_hopping, value=tg.disabled)
        else:
            embed.add_field(name=t.channel_hopping, value=t.max_x_hops(cnt=max_hops))

        await ctx.send(embed=embed)

    @spam_detection.command(name="hops", aliases=["h"])
    async def spam_detection_hops(self, ctx: Context, amount: int):
        """
        Changes the number of maximum channel hops per minute allowed before an alert is issued
        set this to 0 to disable channel hopping alerts
        """

        await Settings.set(int, "spam_detection_max_hops", amount)
        embed = Embed(
            title=t.channel_hopping,
            description=t.hop_amount_set(amount) if amount > 0 else t.hop_detection_disabled,
            colour=Colors.SpamDetection,
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, t.hop_amount_set(amount) if amount > 0 else t.hop_detection_disabled)
