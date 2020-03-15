import os
import string
from typing import Optional, Iterable

from discord import Member, VoiceState, Message, Role, Guild, VoiceChannel
from discord.ext.commands import Bot, Context, check, CommandError, CheckFailure

from database import db, run_in_thread
from models.authorizes_roles import AuthorizedRoles
from models.role_voice_link import RoleVoiceLink
from models.server import Server

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
    return await run_in_thread(get_prefix, message.guild), f"<@!{bot.user.id}> "


bot = Bot(command_prefix=fetch_prefix)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    for guild in bot.guilds:  # type: Guild
        print(f"Updating roles for {guild}")
        linked_roles = {}
        for link in await run_in_thread(db.query, RoleVoiceLink, server=guild.id):
            role = guild.get_role(link.role)
            voice = guild.get_channel(link.voice_channel)
            if role is not None and voice is not None:
                linked_roles.setdefault(role, set()).add(voice)

        for member in guild.members:
            for role, channels in linked_roles.items():
                if member.voice is not None and member.voice.channel in channels:
                    if role not in member.roles:
                        await member.add_roles(role)
                else:
                    if role in member.roles:
                        await member.remove_roles(role)
    print("Initialization complete")


async def check_access(member: Member) -> int:
    if member.id == 370876111992913922:
        return 3

    if member.guild_permissions.administrator:
        return 2

    roles = set(role.id for role in member.roles)
    for authorization in await run_in_thread(db.query, AuthorizedRoles, server=member.guild.id):
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


@bot.command()
@permission_level(1)
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
    if auth is None:
        raise CommandError(f"Role `@{role}` is not authorized.")

    await run_in_thread(db.delete, authorization)
    await ctx.send(f"Role `@{role}` has been unauthorized to control this bot.")


@bot.command(name="list")
@permission_level(1)
async def list_links(ctx: Context):
    """
    list all links between voice channels and roles
    """

    out = []
    for link in await run_in_thread(db.query, RoleVoiceLink, server=ctx.guild.id):
        if (role := ctx.guild.get_role(link.role)) is None:
            continue
        if (voice := ctx.guild.get_channel(link.voice_channel)) is None:
            continue

        out.append(f"`{voice}` (`{voice.id}`) -> `@{role}` (`{role.id}`)")

    await ctx.send("\n".join(out) or "No links have been created yet.")


@bot.command(name="link")
@permission_level(1)
async def create_link(ctx: Context, voice_channel: VoiceChannel, *, role: Role):
    """
    link a voice channel with a role
    """

    if (
        await run_in_thread(db.first, RoleVoiceLink, server=ctx.guild.id, role=role.id, voice_channel=voice_channel.id)
        is not None
    ):
        raise CommandError("Link already exists.")

    if role > ctx.me.top_role:
        raise CommandError(f"Link could not be created because `@{role}` is higher than `@{ctx.me.top_role}`.")

    await run_in_thread(RoleVoiceLink.create, ctx.guild.id, role.id, voice_channel.id)
    await ctx.send(f"Link has been created between voice channel `{voice_channel}` and role `@{role}`.")


@bot.command(name="unlink")
@permission_level(1)
async def remove_link(ctx: Context, voice_channel: VoiceChannel, *, role: Role):
    """
    delete the link between a voice channel and a role
    """

    if (
        link := await run_in_thread(
            db.first, RoleVoiceLink, server=ctx.guild.id, role=role.id, voice_channel=voice_channel.id
        )
    ) is None:
        raise CommandError("Link does not exist.")

    await run_in_thread(db.delete, link)
    await ctx.send(f"Link has been deleted.")


@bot.event
async def on_voice_state_update(member: Member, before: VoiceState, after: VoiceState):
    if before.channel == after.channel:
        return

    guild: Guild = member.guild
    if before.channel is not None:
        await member.remove_roles(
            *(
                role
                for link in await run_in_thread(
                    db.query, RoleVoiceLink, server=guild.id, voice_channel=before.channel.id
                )
                if (role := guild.get_role(link.role)) is not None
            )
        )
    if after.channel is not None:
        await member.add_roles(
            *(
                role
                for link in await run_in_thread(
                    db.query, RoleVoiceLink, server=guild.id, voice_channel=after.channel.id
                )
                if (role := guild.get_role(link.role)) is not None
            )
        )


@bot.event
async def on_command_error(ctx: Context, error: CommandError):
    await ctx.send(f":x: Error: {error}")


@bot.event
async def on_message(message: Message):
    if message.guild is not None:
        await bot.process_commands(message)


bot.run(os.environ["TOKEN"])
