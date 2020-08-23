from datetime import datetime, timedelta
from typing import Optional, Set

from discord import (
    TextChannel,
    Message,
    Embed,
    RawMessageDeleteEvent,
)
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError, UserInputError

from database import run_in_thread
from models.log_exclude import LogExclude
from models.settings import Settings
from permission import Permission
from translations import translations
from util import permission_level, calculate_edit_distance, send_to_changelog

ignored_messages: Set[int] = set()


def ignore(message: Message):
    ignored_messages.add(message.id)


async def delete_nolog(message: Message, delay: Optional[int] = None):
    ignore(message)
    await message.delete(delay=delay)


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
        return self.bot.get_channel(await run_in_thread(Settings.get, int, "logging_" + event, -1))

    async def is_logging_channel(self, channel: TextChannel) -> bool:
        return channel.id in [(await self.get_logging_channel(event)).id for event in ["edit", "delete"]]

    async def on_ready(self):
        try:
            self.cleanup_loop.start()
        except RuntimeError:
            self.cleanup_loop.restart()
        return True

    @tasks.loop(minutes=30)
    async def cleanup_loop(self):
        days: int = await run_in_thread(Settings.get, int, "logging_maxage", -1)
        if days == -1:
            return

        timestamp = datetime.utcnow() - timedelta(days=days)
        for event in ["edit", "delete"]:
            channel: Optional[TextChannel] = await self.get_logging_channel(event)
            if channel is None:
                continue

            async for message in channel.history(limit=None, oldest_first=True):  # type: Message
                if message.created_at > timestamp:
                    break

                await message.delete()

    async def on_message_edit(self, before: Message, after: Message) -> bool:
        if before.id in ignored_messages:
            ignored_messages.remove(before.id)
            return True
        mindiff: int = await run_in_thread(Settings.get, int, "logging_edit_mindiff", 1)
        if calculate_edit_distance(before.content, after.content) < mindiff:
            return True
        if (edit_channel := await self.get_logging_channel("edit")) is None:
            return True
        if await run_in_thread(LogExclude.exists, after.channel.id):
            return True

        embed = Embed(title=translations.message_edited, color=0xFFFF00, timestamp=datetime.utcnow())
        embed.add_field(name=translations.channel, value=before.channel.mention)
        embed.add_field(name=translations.author_title, value=before.author.mention)
        embed.add_field(name=translations.url, value=before.jump_url, inline=False)
        add_field(embed, translations.old_content, before.content)
        add_field(embed, translations.new_content, after.content)
        await edit_channel.send(embed=embed)

        return True

    async def on_raw_message_edit(self, channel: TextChannel, message: Optional[Message]) -> bool:
        if message.id in ignored_messages:
            ignored_messages.remove(message.id)
            return True
        if (edit_channel := await self.get_logging_channel("edit")) is None:
            return True
        if await run_in_thread(LogExclude.exists, message.channel.id):
            return True

        embed = Embed(title=translations.message_edited, color=0xFFFF00, timestamp=datetime.utcnow())
        embed.add_field(name=translations.channel, value=channel.mention)
        if message is not None:
            embed.add_field(name=translations.author_title, value=message.author.mention)
            embed.add_field(name=translations.url, value=message.jump_url, inline=False)
            add_field(embed, translations.new_content, message.content)
        await edit_channel.send(embed=embed)

        return True

    async def on_message_delete(self, message: Message) -> bool:
        if message.id in ignored_messages:
            ignored_messages.remove(message.id)
            return True
        if (delete_channel := await self.get_logging_channel("delete")) is None:
            return True
        if await self.is_logging_channel(message.channel):
            return True
        if await run_in_thread(LogExclude.exists, message.channel.id):
            return True

        embed = Embed(title=translations.message_deleted, color=0xFF0000, timestamp=(datetime.utcnow()))
        embed.add_field(name=translations.channel, value=message.channel.mention)
        embed.add_field(name=translations.author_title, value=message.author.mention)
        add_field(embed, translations.old_content, message.content)
        if message.attachments:
            out = []
            for attachment in message.attachments:
                size = attachment.size
                for unit in "BKMG":
                    if size < 1000:
                        break
                    size /= 1000
                out.append(f"{attachment.filename} ({size:.1f} {unit})")
            embed.add_field(name=translations.attachments, value="\n".join(out), inline=False)
        await delete_channel.send(embed=embed)

        return True

    async def on_raw_message_delete(self, event: RawMessageDeleteEvent) -> bool:
        if event.message_id in ignored_messages:
            ignored_messages.remove(event.message_id)
            return True
        if (delete_channel := await self.get_logging_channel("delete")) is None:
            return True
        if await run_in_thread(LogExclude.exists, event.channel_id):
            return True

        embed = Embed(title=translations.message_deleted, color=0xFF0000, timestamp=datetime.utcnow())
        channel: Optional[TextChannel] = self.bot.get_channel(event.channel_id)
        if channel is not None:
            if await self.is_logging_channel(channel):
                return True

            embed.add_field(name=translations.channel, value=channel.mention)
            embed.add_field(name=translations.message_id, value=event.message_id, inline=False)
        await delete_channel.send(embed=embed)

        return True

    @commands.group(name="logging", aliases=["log"])
    @permission_level(Permission.log_manage)
    @guild_only()
    async def logging(self, ctx: Context):
        """
        view and change logging settings
        """

        if ctx.subcommand_passed is not None:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        edit_channel: Optional[TextChannel] = await self.get_logging_channel("edit")
        delete_channel: Optional[TextChannel] = await self.get_logging_channel("delete")
        changelog_channel: Optional[TextChannel] = await self.get_logging_channel("changelog")
        maxage: int = await run_in_thread(Settings.get, int, "logging_maxage", -1)

        embed = Embed(title=translations.logging, color=0x256BE6)

        if maxage != -1:
            embed.add_field(name=translations.maxage, value=translations.f_x_days(maxage), inline=False)
        else:
            embed.add_field(name=translations.maxage, value=translations.disabled, inline=False)

        if edit_channel is not None:
            mindiff: int = await run_in_thread(Settings.get, int, "logging_edit_mindiff", 1)
            embed.add_field(name=translations.msg_edit, value=edit_channel.mention, inline=True)
            embed.add_field(name=translations.mindiff, value=str(mindiff), inline=True)
        else:
            embed.add_field(name=translations.msg_edit, value=translations.logging_disabled, inline=False)

        if delete_channel is not None:
            embed.add_field(name=translations.msg_delete, value=delete_channel.mention, inline=False)
        else:
            embed.add_field(name=translations.msg_delete, value=translations.logging_disabled, inline=False)

        if changelog_channel is not None:
            embed.add_field(name=translations.changelog, value=changelog_channel.mention, inline=False)
        else:
            embed.add_field(name=translations.changelog, value=translations.disabled, inline=False)

        await ctx.send(embed=embed)

    @logging.command(name="maxage", aliases=["ma"])
    async def maxage(self, ctx: Context, days: int):
        """
        configure period after which old log entries should be deleted
        set to -1 to disable
        """

        if days != -1 and not 0 < days < (1 << 31):
            raise CommandError(translations.invalid_duration)

        await run_in_thread(Settings.set, int, "logging_maxage", days)
        if days == -1:
            await ctx.send(translations.maxage_set_disabled)
            await send_to_changelog(ctx.guild, translations.maxage_set_disabled)
        else:
            await ctx.send(translations.f_maxage_set(days))
            await send_to_changelog(ctx.guild, translations.f_maxage_set(days))

    @logging.group(name="edit", aliases=["e"])
    async def edit(self, ctx: Context):
        """
        change settings for edit event logging
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @edit.command(name="mindist", aliases=["md"])
    async def edit_mindist(self, ctx: Context, mindist: int):
        """
        change the minimum edit distance between the old and new content of the message to be logged
        """

        if mindist <= 0:
            raise CommandError(translations.min_diff_gt_zero)

        await run_in_thread(Settings.set, int, "logging_edit_mindiff", mindist)
        await ctx.send(translations.f_edit_mindiff_updated(mindist))
        await send_to_changelog(ctx.guild, translations.f_log_mindiff_updated(mindist))

    @edit.command(name="channel", aliases=["ch", "c"])
    async def edit_channel(self, ctx: Context, channel: TextChannel):
        """
        change logging channel for edit events
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(translations.log_not_changed_no_permissions)

        await run_in_thread(Settings.set, int, "logging_edit", channel.id)
        await ctx.send(translations.f_log_edit_updated(channel.mention))
        await send_to_changelog(ctx.guild, translations.f_log_edit_updated(channel.mention))

    @edit.command(name="disable", aliases=["d"])
    async def edit_disable(self, ctx: Context):
        """
        disable edit event logging
        """

        await run_in_thread(Settings.set, int, "logging_edit", -1)
        await ctx.send(translations.log_edit_disabled)
        await send_to_changelog(ctx.guild, translations.log_edit_disabled)

    @logging.group(name="delete", aliases=["d"])
    async def delete(self, ctx: Context):
        """
        change settings for delete event logging
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @delete.command(name="channel", aliases=["ch", "c"])
    async def delete_channel(self, ctx: Context, channel: TextChannel):
        """
        change logging channel for delete events
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(translations.log_not_changed_no_permissions)

        await run_in_thread(Settings.set, int, "logging_delete", channel.id)
        await ctx.send(translations.f_log_delete_updated(channel.mention))
        await send_to_changelog(ctx.guild, translations.f_log_delete_updated(channel.mention))

    @delete.command(name="disable", aliases=["d"])
    async def delete_disable(self, ctx: Context):
        """
        disable delete event logging
        """

        await run_in_thread(Settings.set, int, "logging_delete", -1)
        await ctx.send(translations.log_delete_disabled)
        await send_to_changelog(ctx.guild, translations.log_delete_disabled)

    @logging.group(name="changelog", aliases=["cl", "c", "change"])
    async def changelog(self, ctx: Context):
        """
        change settings for internal changelog
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @changelog.command(name="channel", aliases=["ch", "c"])
    async def changelog_channel(self, ctx: Context, channel: TextChannel):
        """
        change changelog channel
        """

        if not channel.permissions_for(channel.guild.me).send_messages:
            raise CommandError(translations.log_not_changed_no_permissions)

        await run_in_thread(Settings.set, int, "logging_changelog", channel.id)
        await ctx.send(translations.f_log_changelog_updated(channel.mention))
        await send_to_changelog(ctx.guild, translations.f_log_changelog_updated(channel.mention))

    @changelog.command(name="disable", aliases=["d"])
    async def changelog_disable(self, ctx: Context):
        """
        disable changelog
        """

        await send_to_changelog(ctx.guild, translations.log_changelog_disabled)
        await run_in_thread(Settings.set, int, "logging_changelog", -1)
        await ctx.send(translations.log_changelog_disabled)

    @logging.group(name="exclude", aliases=["x", "ignore", "i"])
    async def exclude(self, ctx: Context):
        """
        manage excluded channels
        """

        if len(ctx.message.content.lstrip(ctx.prefix).split()) > 2:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        embed = Embed(title=translations.excluded_channels, colour=0x256BE6)
        out = []
        for channel_id in await run_in_thread(LogExclude.all):
            channel: Optional[TextChannel] = self.bot.get_channel(channel_id)
            if channel is None:
                await run_in_thread(LogExclude.remove, channel_id)
            else:
                out.append(f":small_blue_diamond: {channel.mention}")
        if not out:
            embed.description = translations.no_channels_excluded
            embed.colour = 0xCF0606
        else:
            embed.description = "\n".join(out)
        await ctx.send(embed=embed)

    @exclude.command(name="add", aliases=["a", "+"])
    async def exclude_add(self, ctx: Context, channel: TextChannel):
        """
        exclude a channel from logging
        """

        if await run_in_thread(LogExclude.exists, channel.id):
            raise CommandError(translations.already_excluded)

        await run_in_thread(LogExclude.add, channel.id)
        await ctx.send(translations.excluded)
        await send_to_changelog(ctx.guild, translations.f_log_excluded(channel.mention))

    @exclude.command(name="remove", aliases=["r", "del", "d", "-"])
    async def exclude_remove(self, ctx: Context, channel: TextChannel):
        """
        remove a channel from exclude list
        """

        if not await run_in_thread(LogExclude.exists, channel.id):
            raise CommandError(translations.not_excluded)

        await run_in_thread(LogExclude.remove, channel.id)
        await ctx.send(translations.unexcluded)
        await send_to_changelog(ctx.guild, translations.f_log_unexcluded(channel.mention))
