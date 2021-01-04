import asyncio
import string
from typing import Optional, Dict

from PyDrocsid.database import db_thread, db
from PyDrocsid.translations import translations
from PyDrocsid.util import send_long_embed
from discord import TextChannel, Message, Guild, Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, guild_only, CommandError, UserInputError

from cleverbot_api import CleverBot
from colours import Colours
from models.cleverbot_channel import CleverBotChannel
from permissions import Permission
from util import send_to_changelog


class CleverBotCog(Cog, name="CleverBot"):
    def __init__(self, bot: Bot):
        self.bot = bot
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
                None, lambda: cleverbot.say(message.clean_content)
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
    @Permission.cb_list.check
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
        embed = Embed(title=translations.whitelisted_channels, colour=Colours.CleverBot)
        embed.set_thumbnail(url="https://upload.wikimedia.org/wikipedia/de/1/15/Cleverbot_Logo.jpg")
        if out:
            embed.description = "\n".join(out)
        else:
            embed.description = translations.no_whitelisted_channels
        await send_long_embed(ctx, embed)

    @cleverbot.command(name="add", aliases=["a", "+"])
    @Permission.cb_manage.check
    async def cleverbot_add(self, ctx: Context, channel: TextChannel):
        """
        add channel to whitelist
        """

        if await db_thread(db.get, CleverBotChannel, channel.id) is not None:
            raise CommandError(translations.channel_already_whitelisted)

        await db_thread(CleverBotChannel.create, channel.id)
        embed = Embed(
            title=translations.cleverbot, description=translations.channel_whitelisted, colour=Colours.CleverBot
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_channel_whitelisted_cb(channel.mention))

    @cleverbot.command(name="remove", aliases=["del", "d", "-"])
    @Permission.cb_manage.check
    async def cleverbot_remove(self, ctx: Context, channel: TextChannel):
        """
        remove channel from whitelist
        """

        if (row := await db_thread(db.get, CleverBotChannel, channel.id)) is None:
            raise CommandError(translations.channel_not_whitelisted)

        if channel in self.states:
            self.states.pop(channel)

        await db_thread(db.delete, row)
        embed = Embed(title=translations.cleverbot, description=translations.channel_removed, colour=Colours.CleverBot)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, translations.f_log_channel_removed_cb(channel.mention))

    @cleverbot.command(name="reset", aliases=["r"])
    @Permission.cb_reset.check
    async def cleverbot_reset(self, ctx: Context, channel: TextChannel):
        """
        reset cleverbot session for a channel
        """

        embed = Embed(title=translations.cleverbot, colour=Colours.CleverBot)

        if channel in self.states or await db_thread(db.get, CleverBotChannel, channel.id) is not None:
            embed.description = translations.f_session_reset(channel.mention)
            if channel in self.states:
                self.states.pop(channel)
        else:
            embed.description = translations.channel_not_whitelisted
        await ctx.send(embed=embed)
