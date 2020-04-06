from typing import Optional

from discord import TextChannel, Guild, RawMessageUpdateEvent, Message, Embed, RawMessageDeleteEvent
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, TextChannelConverter

from database import run_in_thread
from models.settings import Settings
from util import permission_level


class OptionalChannel(TextChannelConverter):
    async def convert(self, ctx: Context, argument: str) -> Optional[TextChannel]:
        if argument.lower() in ("no", "n", "false", "f", "0", "disable", "off"):
            return None
        return await super().convert(ctx, argument)


class LoggingCog(Cog, name="Logging"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_logging_channel(self, event: str) -> Optional[TextChannel]:
        channel_id = await run_in_thread(Settings.get, int, "logging_" + event, -1)
        return self.bot.get_channel(channel_id) if channel_id != -1 else None

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        edit_channel: Optional[TextChannel] = await self.get_logging_channel("edit")
        if edit_channel is None or before.content == after.content:
            return

        embed = Embed(title="Message Edited", color=0xFFFF00)
        embed.add_field(name="Channel", value=before.channel.mention)
        embed.add_field(name="Author", value=before.author.mention)
        embed.add_field(name="URL", value=before.jump_url, inline=False)
        embed.add_field(name="Old Content", value=before.content, inline=False)
        embed.add_field(name="New Content", value=after.content, inline=False)
        await edit_channel.send(embed=embed)

    @Cog.listener()
    async def on_raw_message_edit(self, event: RawMessageUpdateEvent):
        if event.cached_message is not None:
            return

        edit_channel: Optional[TextChannel] = await self.get_logging_channel("edit")
        if edit_channel is None:
            return

        embed = Embed(title="Message Edited", color=0xFFFF00)
        channel: Optional[TextChannel] = self.bot.get_channel(event.channel_id)
        if channel is not None:
            embed.add_field(name="Channel", value=channel.mention)
            message: Optional[Message] = await channel.fetch_message(event.message_id)
            if message is not None:
                embed.add_field(name="Author", value=message.author.mention)
                embed.add_field(name="URL", value=message.jump_url, inline=False)
                if message.content:
                    embed.add_field(name="New Content", value=message.content, inline=False)
        await edit_channel.send(embed=embed)

    @Cog.listener()
    async def on_message_delete(self, message: Message):
        delete_channel: Optional[TextChannel] = await self.get_logging_channel("delete")
        if delete_channel is None:
            return

        embed = Embed(title="Message Deleted", color=0xFF0000)
        embed.add_field(name="Channel", value=message.channel.mention)
        embed.add_field(name="Author", value=message.author.mention)
        if message.content:
            embed.add_field(name="Old Content", value=message.content, inline=False)
        await delete_channel.send(embed=embed)

    @Cog.listener()
    async def on_raw_message_delete(self, event: RawMessageDeleteEvent):
        if event.cached_message is not None:
            return

        delete_channel: Optional[TextChannel] = await self.get_logging_channel("delete")
        if delete_channel is None:
            return

        embed = Embed(title="Message Deleted", color=0xFF0000)
        channel: Optional[TextChannel] = self.bot.get_channel(event.channel_id)
        if channel is not None:
            embed.add_field(name="Channel", value=channel.mention)
            embed.add_field(name="Message ID", value=event.message_id, inline=False)
        await delete_channel.send(embed=embed)

    @commands.group(name="logging")
    @permission_level(1)
    @guild_only()
    async def logging(self, ctx: Context):
        """
        view and change logging settings
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                await ctx.send_help(self.logging)
            return

        guild: Guild = ctx.guild
        edit_id = await run_in_thread(Settings.get, int, "logging_edit", -1)
        delete_id = await run_in_thread(Settings.get, int, "logging_delete", -1)
        edit_channel: Optional[TextChannel] = guild.get_channel(edit_id) if edit_id != -1 else None
        delete_channel: Optional[TextChannel] = guild.get_channel(delete_id) if delete_id != -1 else None
        out = ["Logging channels:"]
        if edit_channel is not None:
            out.append(f" - message edit: {edit_channel.mention}")
        else:
            out.append(f" - message edit: *disabled*")
        if delete_channel is not None:
            out.append(f" - message delete: {delete_channel.mention}")
        else:
            out.append(f" - message delete: *disabled*")
        await ctx.send("\n".join(out))

    @logging.command(name="edit")
    async def edit(self, ctx: Context, channel: OptionalChannel):
        """
        change logging channel for message edit events (specify off to disable)
        """

        channel: Optional[TextChannel]
        if channel is None:
            await run_in_thread(Settings.set, int, "logging_edit", -1)
            await ctx.send("Logging for message edit events has been disabled.")
        else:
            await run_in_thread(Settings.set, int, "logging_edit", channel.id)
            await ctx.send(f"Logs for message edit events will now be sent to {channel.mention}.")

    @logging.command(name="delete")
    async def delete(self, ctx: Context, channel: OptionalChannel):
        """
        change logging channel for message delete events (specify off to disable)
        """

        channel: Optional[TextChannel]
        if channel is None:
            await run_in_thread(Settings.set, int, "logging_delete", -1)
            await ctx.send("Logging for message delete events has been disabled.")
        else:
            await run_in_thread(Settings.set, int, "logging_delete", channel.id)
            await ctx.send(f"Logs for message delete events will now be sent to {channel.mention}.")
