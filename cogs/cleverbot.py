import asyncio
import string
from asyncio import Lock
from typing import Optional, Dict

from discord import TextChannel, Message, Guild
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, guild_only, CommandError

from cleverbot import CleverBot
from database import run_in_thread, db
from models.cleverbot_channel import CleverBotChannel
from translations import translations
from util import permission_level, send_to_changelog, SUPPORTER, MODERATOR

cleverbot_lock = Lock()


class CleverBotCog(Cog, name="CleverBot"):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.states: Dict[TextChannel, CleverBot] = {}

    async def on_message(self, message: Message) -> bool:
        if message.guild is None or message.author.bot:
            return True
        if message.content[:1].lower() not in string.ascii_letters + "äöüß" + string.digits:
            return True
        if await run_in_thread(db.get, CleverBotChannel, message.channel.id) is None:
            return True

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

        return True

    @commands.group(aliases=["cb"])
    @guild_only()
    async def cleverbot(self, ctx: Context):
        """
        manage CleverBot
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(CleverBotCog.cleverbot)

    @cleverbot.command(name="list", aliases=["l", "?"])
    @permission_level(SUPPORTER)
    async def list_channels(self, ctx: Context):
        """
        list cleverbot channels
        """

        out = []
        guild: Guild = ctx.guild
        for channel in await run_in_thread(db.query, CleverBotChannel):
            text_channel: Optional[TextChannel] = guild.get_channel(channel.channel)
            if text_channel is not None:
                out.append(f"- {text_channel.mention}")
                if text_channel in self.states:
                    out[-1] += f" ({self.states[text_channel].cnt})"
        if out:
            await ctx.send(translations.whitelisted_channels_header + "\n" + "\n".join(out))
        else:
            await ctx.send(translations.no_whitelisted_channels)

    @cleverbot.command(name="add", aliases=["a", "+"])
    @permission_level(MODERATOR)
    async def add_channel(self, ctx: Context, channel: TextChannel):
        """
        add channel to whitelist
        """

        if await run_in_thread(db.get, CleverBotChannel, channel.id) is not None:
            raise CommandError(translations.channel_already_whitelisted)

        await run_in_thread(CleverBotChannel.create, channel.id)
        await ctx.send(translations.channel_whitelisted)
        await send_to_changelog(ctx.guild, translations.f_log_channel_whitelisted_cb(channel.mention))

    @cleverbot.command(name="remove", aliases=["del", "d", "-"])
    @permission_level(MODERATOR)
    async def remove_channel(self, ctx: Context, channel: TextChannel):
        """
        remove channel from whitelist
        """

        if (row := await run_in_thread(db.get, CleverBotChannel, channel.id)) is None:
            raise CommandError(translations.channel_not_whitelisted)

        if channel in self.states:
            self.states.pop(channel)

        await run_in_thread(db.delete, row)
        await ctx.send(translations.channel_removed)
        await send_to_changelog(ctx.guild, translations.f_log_channel_removed_cb(channel.mention))

    @cleverbot.command(name="reset")
    @permission_level(SUPPORTER)
    async def reset_session(self, ctx: Context, channel: TextChannel):
        """
        reset cleverbot session for a channel
        """

        if channel in self.states:
            self.states.pop(channel)
        await ctx.send(translations.f_session_reset(channel.mention))
