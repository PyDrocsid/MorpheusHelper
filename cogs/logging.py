from datetime import datetime
from typing import Optional

from discord import (
    TextChannel,
    Guild,
    RawMessageUpdateEvent,
    Message,
    Embed,
    RawMessageDeleteEvent,
)
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread
from models.settings import Settings
from util import permission_level, calculate_edit_distance


def add_field(embed: Embed, name: str, text: str):
    first = True
    while text:
        embed.add_field(name=["\ufeff", name][first], value=text[:1024], inline=False)
        text = text[1024:]
        first = False


class LoggingCog(Cog, name="Logging"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_logging_channel(self, event: str) -> Optional[TextChannel]:
        channel_id = await run_in_thread(Settings.get, int, "logging_" + event, -1)
        return self.bot.get_channel(channel_id) if channel_id != -1 else None

    @Cog.listener()
    async def on_message_edit(self, before: Message, after: Message):
        edit_channel: Optional[TextChannel] = await self.get_logging_channel("edit")
        mindiff: int = await run_in_thread(Settings.get, int, "logging_edit_mindiff", 1)
        if edit_channel is None or calculate_edit_distance(before.content, after.content) < mindiff:
            return

        embed = Embed(title="Message Edited", color=0xFFFF00, timestamp=datetime.utcnow())
        embed.add_field(name="Channel", value=before.channel.mention)
        embed.add_field(name="Author", value=before.author.mention)
        embed.add_field(name="URL", value=before.jump_url, inline=False)
        add_field(embed, "Old Content", before.content)
        add_field(embed, "New Content", after.content)
        await edit_channel.send(embed=embed)

    @Cog.listener()
    async def on_raw_message_edit(self, event: RawMessageUpdateEvent):
        if event.cached_message is not None:
            return

        edit_channel: Optional[TextChannel] = await self.get_logging_channel("edit")
        if edit_channel is None:
            return

        embed = Embed(title="Message Edited", color=0xFFFF00, timestamp=datetime.utcnow())
        channel: Optional[TextChannel] = self.bot.get_channel(event.channel_id)
        if channel is not None:
            embed.add_field(name="Channel", value=channel.mention)
            message: Optional[Message] = await channel.fetch_message(event.message_id)
            if message is not None:
                embed.add_field(name="Author", value=message.author.mention)
                embed.add_field(name="URL", value=message.jump_url, inline=False)
                add_field(embed, "New Content", message.content)
        await edit_channel.send(embed=embed)

    @Cog.listener()
    async def on_message_delete(self, message: Message):
        delete_channel: Optional[TextChannel] = await self.get_logging_channel("delete")
        if delete_channel is None:
            return

        embed = Embed(title="Message Deleted", color=0xFF0000, timestamp=(datetime.utcnow()))
        embed.add_field(name="Channel", value=message.channel.mention)
        embed.add_field(name="Author", value=message.author.mention)
        add_field(embed, "Old Content", message.content)
        if message.attachments:
            out = []
            for attachment in message.attachments:
                size = attachment.size
                for unit in "BKMG":
                    if size < 1000:
                        break
                    size /= 1000
                out.append(f"{attachment.filename} ({size:.1f} {unit})")
            embed.add_field(name="Attachments", value="\n".join(out), inline=False)
        await delete_channel.send(embed=embed)

    @Cog.listener()
    async def on_raw_message_delete(self, event: RawMessageDeleteEvent):
        if event.cached_message is not None:
            return

        delete_channel: Optional[TextChannel] = await self.get_logging_channel("delete")
        if delete_channel is None:
            return

        embed = Embed(title="Message Deleted", color=0xFF0000, timestamp=datetime.utcnow())
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
        changelog_id = await run_in_thread(Settings.get, int, "logging_changelog", -1)
        edit_channel: Optional[TextChannel] = guild.get_channel(edit_id) if edit_id != -1 else None
        delete_channel: Optional[TextChannel] = guild.get_channel(delete_id) if delete_id != -1 else None
        changelog_channel: Optional[TextChannel] = guild.get_channel(changelog_id) if changelog_id != -1 else None
        out = ["Logging channels:"]
        if edit_channel is not None:
            mindiff: int = await run_in_thread(Settings.get, int, "logging_edit_mindiff", 1)
            out.append(f" - message edit: {edit_channel.mention} (minimum difference: {mindiff})")
        else:
            out.append(f" - message edit: *disabled*")
        if delete_channel is not None:
            out.append(f" - message delete: {delete_channel.mention}")
        else:
            out.append(f" - message delete: *disabled*")
        if changelog_channel is not None:
            out.append(f" - changelog: {changelog_channel.mention}")
        else:
            out.append(f" - changelog: *disabled*")
        await ctx.send("\n".join(out))

    @logging.group(name="edit")
    async def edit(self, ctx: Context):
        """
        change settings for edit event logging
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.edit)

    @edit.command(name="mindiff")
    async def edit_mindiff(self, ctx: Context, mindiff: int):
        """
        change the minimum difference between the old and new content of the message to be logged
        """

        if mindiff <= 0:
            raise CommandError("Minimum difference must be greater than zero.")

        await run_in_thread(Settings.set, int, "logging_edit_mindiff", mindiff)
        await ctx.send(f"Message edit events will now only be logged if the difference is at least {mindiff}.")

    @edit.command(name="channel")
    async def edit_channel(self, ctx: Context, channel: TextChannel):
        """
        change logging channel for edit events
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(
                "Logging channel could not be changed because I don't have `send_messages` permission there."
            )

        await run_in_thread(Settings.set, int, "logging_edit", channel.id)
        await ctx.send(f"Logs for message edit events will now be sent to {channel.mention}.")

    @edit.command(name="disable")
    async def edit_disable(self, ctx: Context):
        """
        disable edit event logging
        """

        await run_in_thread(Settings.set, int, "logging_edit", -1)
        await ctx.send("Logging for message edit events has been disabled.")

    @logging.group(name="delete")
    async def delete(self, ctx: Context):
        """
        change settings for delete event logging
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.delete)

    @delete.command(name="channel")
    async def delete_channel(self, ctx: Context, channel: TextChannel):
        """
        change logging channel for delete events
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(
                "Logging channel could not be changed because I don't have `send_messages` permission there."
            )

        await run_in_thread(Settings.set, int, "logging_delete", channel.id)
        await ctx.send(f"Logs for message delete events will now be sent to {channel.mention}.")

    @delete.command(name="disable")
    async def delete_disable(self, ctx: Context):
        """
        disable delete event logging
        """

        await run_in_thread(Settings.set, int, "logging_delete", -1)
        await ctx.send("Logging for message delete events has been disabled.")

    @logging.group(name="changelog")
    async def changelog(self, ctx: Context):
        """
        change settings for internal changelog
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.changelog)

    @changelog.command(name="channel")
    async def changelog_channel(self, ctx: Context, channel: TextChannel):
        """
        change changelog channel
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(
                "Changelog channel could not be changed because I don't have `send_messages` permission there."
            )

        await run_in_thread(Settings.set, int, "logging_changelog", channel.id)
        await ctx.send(f"Changelog channel is now {channel.mention}.")

    @changelog.command(name="disable")
    async def changelog_disable(self, ctx: Context):
        """
        disable changelog
        """

        await run_in_thread(Settings.set, int, "logging_changelog", -1)
        await ctx.send("Changelog channel has been disabled.")
