import os
import string
from typing import Optional, Iterable

from discord import Message, Role, Status, Game, Embed
from discord.ext.commands import Bot, Context, CommandError, guild_only, CommandNotFound

from cogs.betheprofessional import BeTheProfessionalCog
from cogs.invites import InvitesCog
from cogs.logging import LoggingCog
from cogs.mediaonly import MediaOnlyCog
from cogs.metaquestion import MetaQuestionCog
from cogs.reaction_pin import ReactionPinCog
from cogs.rules import RulesCog
from cogs.voice_channel import VoiceChannelCog
from database import db, run_in_thread
from models.authorized_role import AuthorizedRole
from models.settings import Settings
from util import permission_level, make_error, measure_latency, send_to_changelog

db.create_tables()

DEFAULT_PREFIX = "!"


def get_prefix() -> str:
    return Settings.get(str, "prefix", DEFAULT_PREFIX)


def set_prefix(new_prefix: str):
    Settings.set(str, "prefix", new_prefix)


async def fetch_prefix(_, message: Message) -> Iterable[str]:
    if message.guild is None:
        return ""
    return await run_in_thread(get_prefix), f"<@!{bot.user.id}> ", f"<@{bot.user.id}> "


bot = Bot(command_prefix=fetch_prefix)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    await bot.change_presence(status=Status.online, activity=Game(name="github.com/Defelo/MorpheusHelper"))


@bot.command()
async def ping(ctx: Context):
    """
    display bot latency
    """

    latency: Optional[float] = measure_latency()
    out = "Pong!"
    if latency is not None:
        out += f" ({latency * 1000:.0f} ms)"
    await ctx.send(out)


@bot.command(name="prefix")
@permission_level(1)
@guild_only()
async def change_prefix(ctx: Context, new_prefix: str):
    """
    change the bot prefix
    """

    if not 0 < len(new_prefix) <= 16:
        raise CommandError("Length of prefix must be between 1 and 16.")

    valid_chars = set(string.ascii_letters + string.digits + string.punctuation)
    if any(c not in valid_chars for c in new_prefix):
        raise CommandError("Prefix contains invalid characters.")

    await run_in_thread(set_prefix, new_prefix)
    await ctx.send("Prefix has been updated.")
    await send_to_changelog(ctx.guild, f"Bot prefix has been changed to `{new_prefix}`")


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
    for auth_role in await run_in_thread(db.all, AuthorizedRole):
        if (role := ctx.guild.get_role(auth_role.role)) is not None:
            roles.append(f" - `@{role}` (`{role.id}`)")
        else:
            await run_in_thread(db.delete, auth_role)
    if roles:
        await ctx.send("The following roles are authorized to control this bot:\n" + "\n".join(roles))
    else:
        await ctx.send("Except administrators nobody can control this bot.")


@auth.command(name="add")
async def auth_add(ctx: Context, *, role: Role):
    """
    authorize role to control this bot
    """

    authorization: Optional[AuthorizedRole] = await run_in_thread(db.get, AuthorizedRole, role.id)
    if authorization is not None:
        raise CommandError(f"Role `@{role}` is already authorized.")

    await run_in_thread(AuthorizedRole.create, role.id)
    await ctx.send(f"Role `@{role}` has been authorized to control this bot.")
    await send_to_changelog(ctx.guild, f"Role `@{role}` has been authorized to control this bot.")


@auth.command(name="del")
async def auth_del(ctx: Context, *, role: Role):
    """
    unauthorize role to control this bot
    """

    authorization: Optional[AuthorizedRole] = await run_in_thread(db.get, AuthorizedRole, role.id)
    if authorization is None:
        raise CommandError(f"Role `@{role}` is not authorized.")

    await run_in_thread(db.delete, authorization)
    await ctx.send(f"Role `@{role}` has been unauthorized to control this bot.")
    await send_to_changelog(ctx.guild, f"Role `@{role}` has been unauthorized to control this bot.")


async def build_info_embed(authorized: bool) -> Embed:
    embed = Embed(
        title="MorpheusHelper",
        color=0x007700,
        description="Helper Bot for the Discord Server of The Morpheus Tutorials",
    )
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/avatars/686299664726622258/cb99c816286bdd1d988ec16d8ae85e15.png"
    )
    prefix = await run_in_thread(get_prefix)
    features = [
        "Role system for topics you are interested in",
        "Pin your own messages by reacting with :pushpin: in specific channels",
        "Automatic role assignment upon entering a voice channel",
        "Discord server invite whitelist",
        "Meta question information command",
    ]
    if authorized:
        features.append("Logging of message edit and delete events")
        features.append("Send/Edit/Delete text and embed messages as the bot")
        features.append("Media only channels")
    embed.add_field(
        name="Features", value="\n".join(f":small_orange_diamond: {feature}" for feature in features), inline=False
    )
    embed.add_field(name="Author", value="<@370876111992913922>", inline=True)
    embed.add_field(name="Contributors", value="<@212866839083089921>, <@330148908531580928>", inline=True)
    embed.add_field(name="GitHub", value="https://github.com/Defelo/MorpheusHelper", inline=False)
    embed.add_field(name="Prefix", value=f"`{prefix}` or {bot.user.mention}", inline=True)
    embed.add_field(name="Help Command", value=f"`{prefix}help`", inline=True)
    embed.add_field(
        name="Bug Reports / Feature Requests",
        value="Please create an issue in the GitHub repository or contact me (<@370876111992913922>) via Discord.",
        inline=False,
    )
    return embed


@bot.command(name="info", aliases=["about"])
async def info(ctx: Context):
    """
    show information about the bot
    """

    await ctx.send(embed=await build_info_embed(False))


@bot.command(name="admininfo")
@permission_level(1)
async def admininfo(ctx: Context):
    """
    show information about the bot (admin view)
    """

    await ctx.send(embed=await build_info_embed(True))


@bot.event
async def on_command_error(ctx: Context, error: CommandError):
    if isinstance(error, CommandNotFound) and ctx.guild is not None and ctx.prefix == get_prefix():
        return
    await ctx.send(make_error(error))


@bot.event
async def on_message(message: Message):
    if message.author == bot.user:
        return

    if message.content.strip() in (f"<@!{bot.user.id}>", f"<@{bot.user.id}>"):
        if message.guild is None:
            await message.channel.send("Ping!")
        else:
            await message.channel.send(embed=await build_info_embed(False))
        return

    await bot.process_commands(message)


bot.add_cog(VoiceChannelCog(bot))
bot.add_cog(ReactionPinCog(bot))
bot.add_cog(BeTheProfessionalCog(bot))
bot.add_cog(LoggingCog(bot))
bot.add_cog(MediaOnlyCog(bot))
bot.add_cog(RulesCog(bot))
bot.add_cog(InvitesCog(bot))
bot.add_cog(MetaQuestionCog(bot))
bot.run(os.environ["TOKEN"])
