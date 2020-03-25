import os
import string
from typing import Optional, Iterable

from discord import Message, Role, Guild
from discord.ext.commands import Bot, Context, CommandError, guild_only, CommandNotFound

from cogs.voice_channel import VoiceChannelCog
from database import db, run_in_thread
from models.authorizes_roles import AuthorizedRoles
from models.server import Server
from util import permission_level

db.create_tables()

DEFAULT_PREFIX = "!"


def get_prefix(guild: Guild) -> str:
    if (server := db.get(Server, guild.id)) is None:
        server = Server.create(guild.id, DEFAULT_PREFIX)

    return server.prefix


def set_prefix(guild: Guild, new_prefix: str) -> str:
    if (server := db.get(Server, guild.id)) is None:
        server = Server.create(guild.id, new_prefix)
    else:
        server.prefix = new_prefix

    return server.prefix


async def fetch_prefix(_, message: Message) -> Iterable[str]:
    if message.guild is None:
        return ""
    return await run_in_thread(get_prefix, message.guild), f"<@!{bot.user.id}> ", f"<@{bot.user.id}> "


bot = Bot(command_prefix=fetch_prefix)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.command()
@permission_level(1)
@guild_only()
async def prefix(ctx: Context, *, new_prefix: str):
    """
    change the bot prefix
    """

    if not 0 < len(new_prefix) <= 16:
        raise CommandError("Length of prefix must be between 1 and 16.")

    valid_chars = set(string.ascii_letters + string.digits + string.punctuation)
    if any(c not in valid_chars for c in new_prefix):
        raise CommandError("Prefix contains invalid characters.")

    await run_in_thread(set_prefix, ctx.guild, new_prefix)
    await ctx.send("Prefix has been updated.")


@bot.group()
@permission_level(2)
@guild_only()
async def auth(ctx: Context):
    """
    manage roles authorized to control this bot
    """

    if ctx.invoked_subcommand is None:
        await ctx.send_help("auth")


@auth.command(name="list")
async def auth_list(ctx: Context):
    """
    list authorized roles
    """

    roles = []
    for auth_role in await run_in_thread(db.query, AuthorizedRoles, server=ctx.guild.id):
        if (role := ctx.guild.get_role(auth_role.role)) is not None:
            roles.append(f" - `@{role}` (`{role.id}`)")
    if roles:
        await ctx.send("The following roles are authorized to control this bot:\n" + "\n".join(roles))
    else:
        await ctx.send("Except administrators nobody can control this bot.")


@auth.command(name="add")
async def auth_add(ctx: Context, *, role: Role):
    """
    authorize role to control this bot
    """

    authorization: Optional[AuthorizedRoles] = await run_in_thread(
        db.first, AuthorizedRoles, server=ctx.guild.id, role=role.id
    )
    if authorization is not None:
        raise CommandError(f"Role `@{role}` is already authorized.")

    await run_in_thread(AuthorizedRoles.create, ctx.guild.id, role.id)
    await ctx.send(f"Role `@{role}` has been authorized to control this bot.")


@auth.command(name="del")
async def auth_del(ctx: Context, *, role: Role):
    """
    unauthorize role to control this bot
    """

    authorization: Optional[AuthorizedRoles] = await run_in_thread(
        db.first, AuthorizedRoles, server=ctx.guild.id, role=role.id
    )
    if authorization is None:
        raise CommandError(f"Role `@{role}` is not authorized.")

    await run_in_thread(db.delete, authorization)
    await ctx.send(f"Role `@{role}` has been unauthorized to control this bot.")


@bot.event
async def on_command_error(ctx: Context, error: CommandError):
    if isinstance(error, CommandNotFound) and ctx.guild is not None and ctx.prefix == get_prefix(ctx.guild):
        return
    await ctx.send(f":x: Error: {error}")


@bot.event
async def on_message(message: Message):
    if message.content.strip() in (f"<@!{bot.user.id}>", f"<@{bot.user.id}>"):
        if message.guild is None:
            await message.channel.send("Ping!")
        else:
            await message.channel.send(f"My prefix here is `{get_prefix(message.guild)}`")
        return

    await bot.process_commands(message)


bot.add_cog(VoiceChannelCog(bot))
bot.run(os.environ["TOKEN"])
