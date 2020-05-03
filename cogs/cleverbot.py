from typing import Optional

from discord import TextChannel, Message, Guild
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, guild_only, CommandError

from database import run_in_thread, db
from models.cleverbot_channel import CleverBotChannel
from translations import translations
from util import permission_level, send_to_changelog


class CleverBotCog(Cog, name="CleverBot"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_message(self, message: Message) -> bool:
        if message.guild is None:
            return True

        return True

    @commands.group(aliases=["cb"])
    @permission_level(1)
    @guild_only()
    async def cleverbot(self, ctx: Context):
        """
        manage CleverBot
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(CleverBotCog.cleverbot)

    @cleverbot.command(name="list", aliases=["l", "?"])
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
        if out:
            await ctx.send(translations.whitelisted_channels_header + "\n" + "\n".join(out))
        else:
            await ctx.send(translations.no_whitelisted_channels)

    @cleverbot.command(name="add", aliases=["a", "+"])
    async def add_channel(self, ctx: Context, channel: TextChannel):
        """
        add channel to whitelist
        """

        if await run_in_thread(db.get, CleverBotChannel, channel.id) is not None:
            raise CommandError(translations.channel_already_whitelisted)

        await run_in_thread(CleverBotChannel.create, channel.id)
        await ctx.send(translations.channel_whitelisted)
        await send_to_changelog(ctx.guild, translations.f_log_channel_whitelisted_cb(channel.mention))

    @cleverbot.command(name="remove", aliases=["del", "r", "d", "-"])
    async def remove_channel(self, ctx: Context, channel: TextChannel):
        """
        remove channel from whitelist
        """

        if (row := await run_in_thread(db.get, CleverBotChannel, channel.id)) is None:
            raise CommandError(translations.channel_not_whitelisted)

        await run_in_thread(db.delete, row)
        await ctx.send(translations.channel_removed)
        await send_to_changelog(ctx.guild, translations.f_log_channel_removed_cb(channel.mention))
