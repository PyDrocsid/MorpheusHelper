import socket
import time
from typing import Optional

from discord import Member, TextChannel, Guild
from discord.ext.commands import check, Context, CheckFailure, Bot, Cog

from database import run_in_thread, db
from models.authorized_role import AuthorizedRole
from models.settings import Settings
from multilock import MultiLock


def make_error(message) -> str:
    return f":x: Error: {message}"


async def check_access(member: Member) -> int:
    if member.id == 370876111992913922:
        return 3

    if member.guild_permissions.administrator:
        return 2

    roles = set(role.id for role in member.roles)
    for authorization in await run_in_thread(db.query, AuthorizedRole):
        if authorization.role in roles:
            return 1
    return 0


def permission_level(level: int):
    @check
    async def admin_only(ctx: Context):
        if await check_access(ctx.author) < level:
            raise CheckFailure("You are not allowed to use this command.")

        return True

    return admin_only


def calculate_edit_distance(a: str, b: str) -> int:
    dp = [[max(i, j) for j in range(len(b) + 1)] for i in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            dp[i][j] = min(dp[i - 1][j - 1] + (a[i - 1] != b[j - 1]), dp[i - 1][j] + 1, dp[i][j - 1] + 1,)
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
