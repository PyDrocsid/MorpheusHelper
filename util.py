import io
import socket
import time
from typing import Optional, Tuple, List, Union

from discord import Member, TextChannel, Guild, PartialEmoji, Message, File, Embed, User, Attachment
from discord.ext.commands import (
    check,
    Context,
    CheckFailure,
    Bot,
    Cog,
    PartialEmojiConverter,
    BadArgument,
    CommandError,
    Command,
    Group,
)

from database import run_in_thread
from models.settings import Settings
from multilock import MultiLock
from permission import Permission
from translations import translations


class FixedEmojiConverter(PartialEmojiConverter):
    async def convert(self, ctx, argument):
        try:
            return await super().convert(ctx, argument)
        except BadArgument:
            pass

        # noinspection PyProtectedMember
        # skipcq: PYL-W0212
        return PartialEmoji.with_state(ctx.bot._connection, animated=False, name=argument, id=None)


def make_error(message) -> str:
    return f":x: Error: {message}"


async def can_run_command(command: Command, ctx: Context) -> bool:
    try:
        return await command.can_run(ctx)
    except CommandError:
        return False


PUBLIC, SUPPORTER, MODERATOR, ADMINISTRATOR, OWNER = range(5)


async def get_permission_level(member: Union[Member, User]) -> int:
    if member.id == 370876111992913922:
        return OWNER

    if not isinstance(member, Member):
        return PUBLIC

    roles = {role.id for role in member.roles}

    async def has_role(role_name):
        return await run_in_thread(Settings.get, int, role_name + "_role") in roles

    if member.guild_permissions.administrator or await has_role("admin"):
        return ADMINISTRATOR
    if await has_role("mod"):
        return MODERATOR
    if await has_role("supp"):
        return SUPPORTER

    return PUBLIC


async def check_permissions(member: Union[Member, User], permission: Union[Permission, int]) -> bool:
    if isinstance(permission, Permission):
        permission = await permission.resolve()
    return await get_permission_level(member) >= permission


def permission_level(permission: Union[Permission, int]):
    @check
    async def inner(ctx: Context):
        member: Union[Member, User] = ctx.author
        if not isinstance(member, Member):
            member = ctx.bot.guilds[0].get_member(ctx.author.id) or member
        if not await check_permissions(member, permission):
            raise CheckFailure(translations.not_allowed)

        return True

    return inner


def calculate_edit_distance(a: str, b: str) -> int:
    dp = [[max(i, j) for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            dp[i][j] = min(dp[i - 1][j - 1] + (a[i - 1] != b[j - 1]), dp[i - 1][j] + 1, dp[i][j - 1] + 1)
    return dp[len(a)][len(b)]


def measure_latency() -> Optional[float]:
    host = socket.gethostbyname("discordapp.com")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)

    t = time.time()

    try:
        s.connect((host, 443))
        s.shutdown(socket.SHUT_RD)
    except (socket.timeout, OSError):
        return None

    return time.time() - t


async def send_to_changelog(guild: Guild, message: str):
    channel: Optional[TextChannel] = guild.get_channel(await run_in_thread(Settings.get, int, "logging_changelog", -1))
    if channel is not None:
        await channel.send(message)


event_handlers = {}
cog_instances = {}
handler_lock = MultiLock()


async def call_event_handlers(event: str, *args, identifier=None, prepare=None):
    async with handler_lock[(event, identifier) if identifier is not None else None]:
        if prepare is not None:
            args = await prepare()
            if args is None:
                return False

        for handler in event_handlers.get(event, []):
            if not await handler(*args):
                return False

        return True


def register_cogs(bot: Bot, *cogs):
    for cog_class in cogs:
        if cog_class is None:
            continue
        cog: Cog = cog_class(bot)
        for e in dir(cog):
            func = getattr(cog, e)
            if e.startswith("on_") and callable(func):
                event_handlers.setdefault(e[3:], []).append(func)
        bot.add_cog(cog)


async def get_prefix() -> str:
    return await run_in_thread(Settings.get, str, "prefix", ".")


async def set_prefix(new_prefix: str):
    await run_in_thread(Settings.set, str, "prefix", new_prefix)


async def attachment_to_file(attachment: Attachment) -> File:
    file = io.BytesIO()
    await attachment.save(file)
    return File(file, filename=attachment.filename, spoiler=attachment.is_spoiler())


async def read_normal_message(bot: Bot, channel: TextChannel, author: Member) -> Tuple[str, List[File]]:
    msg: Message = await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)
    return msg.content, [await attachment_to_file(attachment) for attachment in msg.attachments]


async def read_embed(bot: Bot, channel: TextChannel, author: Member) -> Embed:
    await channel.send(translations.send_embed_title)
    title: str = (await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)).content
    if len(title) > 256:
        raise CommandError(translations.title_too_long)
    await channel.send(translations.send_embed_content)
    content: str = (await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)).content
    return Embed(title=title, description=content)


async def read_complete_message(message: Message) -> Tuple[str, List[File], Optional[Embed]]:
    for embed in message.embeds:
        if embed.type == "rich":
            break
    else:
        embed = None

    return message.content, [await attachment_to_file(attachment) for attachment in message.attachments], embed


async def send_help(ctx: Context, command_name: Optional[Union[str, Command]]):
    def format_command(cmd: Command) -> str:
        doc = " - " + cmd.short_doc if cmd.short_doc else ""
        return f"`{cmd.name}`{doc}"

    async def add_commands(cog_name: str, commands: List[Command]):
        desc: List[str] = []
        for cmd in commands:
            if not cmd.hidden and await can_run_command(cmd, ctx):
                desc.append(format_command(cmd))
        if desc:
            embed.add_field(name=cog_name, value="\n".join(desc), inline=False)

    prefix: str = await get_prefix()
    embed = Embed(title=translations.help, color=0x008080)
    if command_name is None:
        for cog in ctx.bot.cogs.values():
            await add_commands(cog.qualified_name, cog.get_commands())
        await add_commands(translations.no_category, [command for command in ctx.bot.commands if command.cog is None])

        embed.add_field(name="** **", value=translations.f_help_usage(prefix), inline=False)

        await ctx.send(embed=embed)
        return

    if isinstance(command_name, str):
        cog: Optional[Cog] = ctx.bot.get_cog(command_name)
        if cog is not None:
            await add_commands(cog.qualified_name, cog.get_commands())
            await ctx.send(embed=embed)
            return

        command: Optional[Union[Command, Group]] = ctx.bot.get_command(command_name)
        if command is None:
            raise CommandError(translations.cog_or_command_not_found)
    else:
        command: Command = command_name

    description = prefix
    if command.full_parent_name:
        description += command.full_parent_name + " "
    if command.aliases:
        description += "[" + "|".join([command.name] + command.aliases) + "] "
    else:
        description += command.name + " "
    description += command.signature

    embed.description = f"```css\n{description.strip()}\n```"
    embed.add_field(name=translations.description, value=command.help, inline=False)

    if isinstance(command, Group):
        await add_commands(translations.subcommands, command.commands)

    await ctx.send(embed=embed)
