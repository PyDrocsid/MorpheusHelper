import io
import socket
import time
from typing import Optional, Tuple, List, Union

from discord import Member, TextChannel, Guild, PartialEmoji, Message, File, Embed, User
from discord.ext.commands import check, Context, CheckFailure, Bot, Cog, PartialEmojiConverter, BadArgument

from database import run_in_thread
from models.settings import Settings
from multilock import MultiLock
from translations import translations


class FixedEmojiConverter(PartialEmojiConverter):
    async def convert(self, ctx, argument):
        try:
            return await super().convert(ctx, argument)
        except BadArgument:
            pass

        # noinspection PyProtectedMember
        return PartialEmoji.with_state(ctx.bot._connection, animated=False, name=argument, id=None)


def make_error(message) -> str:
    return f":x: Error: {message}"


PUBLIC, SUPPORTER, MODERATOR, ADMINISTRATOR, OWNER = range(5)


async def get_permission_level(member: Union[Member, User]) -> int:
    if member.id == 370876111992913922:
        return OWNER

    if not isinstance(member, Member):
        return PUBLIC

    roles = set(role.id for role in member.roles)

    async def has_role(role_name):
        return await run_in_thread(Settings.get, int, role_name + "_role") in roles

    if member.guild_permissions.administrator or await has_role("admin"):
        return ADMINISTRATOR
    if await has_role("mod"):
        return MODERATOR
    if await has_role("supp"):
        return SUPPORTER

    return PUBLIC


async def check_permissions(member: Union[Member, User], minimum_permission_level: int) -> bool:
    return await get_permission_level(member) >= minimum_permission_level


def permission_level(level: int):
    @check
    async def inner(ctx: Context):
        member: Union[Member, User] = ctx.author
        if not isinstance(member, Member):
            member = ctx.bot.guilds[0].get_member(ctx.author.id) or member
        if not await check_permissions(member, level):
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
    if identifier is not None:
        await handler_lock.acquire((event, identifier))

    if prepare is not None:
        args = await prepare()
        if args is None:
            if identifier is not None:
                handler_lock.release((event, identifier))
            return False

    for handler in event_handlers.get(event, []):
        if not await handler(*args):
            if identifier is not None:
                handler_lock.release((event, identifier))
            return False

    if identifier is not None:
        handler_lock.release((event, identifier))

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


async def read_normal_message(bot: Bot, channel: TextChannel, author: Member) -> Tuple[str, List[File]]:
    msg: Message = await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)
    files = []
    for attachment in msg.attachments:
        file = io.BytesIO()
        await attachment.save(file)
        files.append(File(file, filename=attachment.filename, spoiler=attachment.is_spoiler()))
    return msg.content, files


async def read_embed(bot: Bot, channel: TextChannel, author: Member) -> Embed:
    await channel.send(translations.send_embed_title)
    title: str = (await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)).content
    await channel.send(translations.send_embed_content)
    content: str = (await bot.wait_for("message", check=lambda m: m.channel == channel and m.author == author)).content
    return Embed(title=title, description=content)
