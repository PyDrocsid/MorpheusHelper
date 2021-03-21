import asyncio
import string
from typing import Optional, Dict

from discord import TextChannel, Message, Guild, Embed
from discord.ext import commands
from discord.ext.commands import Context, guild_only, CommandError, UserInputError

from PyDrocsid.cog import Cog
from PyDrocsid.database import db_thread, db
from PyDrocsid.translations import t
from PyDrocsid.util import send_long_embed
from .api import CleverBot
from .colors import Colors
from .models import CleverBotChannel
from .permissions import CleverBotPermission
from cogs.library.contributor import Contributor
from cogs.library.pubsub import send_to_changelog

tg = t.g
t = t.cleverbot


class CleverBotCog(Cog, name="CleverBot"):
    CONTRIBUTORS = [Contributor.Defelo, Contributor.wolflu]
    PERMISSIONS = CleverBotPermission

    def __init__(self):
        super().__init__()

        self.states: Dict[TextChannel, CleverBot] = {}

    async def on_message(self, message: Message):
        if message.guild is None or message.author.bot:
            return
        if message.content[:1].lower() not in string.ascii_letters + "äöüß" + string.digits:
            return
        if await db_thread(db.get, CleverBotChannel, message.channel.id) is None:
            return

        async with message.channel.typing():
            if message.channel in self.states:
                cleverbot: CleverBot = self.states[message.channel]
            else:
                cleverbot = self.states[message.channel] = CleverBot()
            response = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: cleverbot.say(message.clean_content),
            )
            if not response:
                response = "..."

            await message.channel.send(response)

    @commands.group(aliases=["cb"])
    @guild_only()
    async def cleverbot(self, ctx: Context):
        """
        manage CleverBot
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @cleverbot.command(name="list", aliases=["l", "?"])
    @CleverBotPermission.list.check
    async def cleverbot_list(self, ctx: Context):
        """
        list cleverbot channels
        """

        out = []
        guild: Guild = ctx.guild
        for channel in await db_thread(db.all, CleverBotChannel):
            text_channel: Optional[TextChannel] = guild.get_channel(channel.channel)
            if text_channel is not None:
                out.append(f":small_orange_diamond: {text_channel.mention}")
                if text_channel in self.states:
                    out[-1] += f" ({self.states[text_channel].cnt})"
        embed = Embed(title=t.whitelisted_channels, colour=Colors.CleverBot)
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/de/1/15/Cleverbot_Logo.jpg")
        if out:
            embed.description = "\n".join(out)
        else:
            embed.description = t.no_whitelisted_channels
        await send_long_embed(ctx, embed)

    @cleverbot.command(name="add", aliases=["a", "+"])
    @CleverBotPermission.manage.check
    async def cleverbot_add(self, ctx: Context, channel: TextChannel):
        """
        add channel to whitelist
        """

        if await db_thread(db.get, CleverBotChannel, channel.id) is not None:
            raise CommandError(t.channel_already_whitelisted)

        await db_thread(CleverBotChannel.create, channel.id)
        embed = Embed(title=t.cleverbot, description=t.channel_whitelisted, colour=Colors.CleverBot)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, t.log_channel_whitelisted(channel.mention))

    @cleverbot.command(name="remove", aliases=["del", "d", "-"])
    @CleverBotPermission.manage.check
    async def cleverbot_remove(self, ctx: Context, channel: TextChannel):
        """
        remove channel from whitelist
        """

        if (row := await db_thread(db.get, CleverBotChannel, channel.id)) is None:
            raise CommandError(t.channel_not_whitelisted)

        if channel in self.states:
            self.states.pop(channel)

        await db_thread(db.delete, row)
        embed = Embed(title=t.cleverbot, description=t.channel_removed, colour=Colors.CleverBot)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, t.log_channel_removed(channel.mention))

    @cleverbot.command(name="reset", aliases=["r"])
    @CleverBotPermission.reset.check
    async def cleverbot_reset(self, ctx: Context, channel: TextChannel):
        """
        reset cleverbot session for a channel
        """

        embed = Embed(title=t.cleverbot, colour=Colors.CleverBot)

        if channel in self.states or await db_thread(db.get, CleverBotChannel, channel.id) is not None:
            embed.description = t.session_reset(channel.mention)
            if channel in self.states:
                self.states.pop(channel)
        else:
            embed.description = t.channel_not_whitelisted
        await ctx.send(embed=embed)
