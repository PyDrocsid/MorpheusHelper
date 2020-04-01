from typing import List

from discord import Role, Guild, Member
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.btp_role import BTPRole
from util import permission_level


async def parse_topics(guild: Guild, topics: str) -> List[Role]:
    roles: List[Role] = []
    for topic in map(str.strip, topics.replace(";", ",").split(",")):
        for role in guild.roles:
            if role.name.lower() == topic.lower() and await run_in_thread(db.get, BTPRole, role.id) is not None:
                break
        else:
            raise CommandError(f"Topic `{topic}` not found.")
        roles.append(role)
    return roles


async def list_topics(guild: Guild) -> List[Role]:
    roles: List[Role] = []
    for btp_role in await run_in_thread(db.all, BTPRole):
        if (role := guild.get_role(btp_role.role_id)) is None:
            await run_in_thread(db.delete, btp_role)
        else:
            roles.append(role)
    return roles


class BeTheProfessionalCog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group(name="btp")
    @guild_only()
    async def btp(self, ctx: Context):
        """
        manage language roles
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help("btp")

    @btp.command(name="?")
    async def list_roles(self, ctx: Context):
        """
        lists all registered topics
        """

        out = [role.name for role in await list_topics(ctx.guild)]
        if out:
            await ctx.send("Available Topics:\n" + ", ".join(out))
        else:
            await ctx.send("No topics have been registered yet.")

    @btp.command(name="+")
    async def add_role(self, ctx: Context, *, topics: str):
        """
        add one or more topics you are interested in
        """

        member: Member = ctx.author
        roles: List[Role] = [r for r in await parse_topics(ctx.guild, topics) if r not in member.roles]

        await member.add_roles(*roles)
        if roles:
            await ctx.send(f"{len(roles)} topic" + [" has", "s have"][len(roles) > 1] + " been added successfully.")
        else:
            await ctx.send("No topic has been added.")

    @btp.command(name="-")
    async def remove_roles(self, ctx: Context, *, topics: str):
        """
        remove one or more topics (use * to remove all topics)
        """

        member: Member = ctx.author
        if topics.strip() == "*":
            roles: List[Role] = await list_topics(ctx.guild)
        else:
            roles: List[Role] = await parse_topics(ctx.guild, topics)
        roles = [r for r in roles if r in member.roles]

        await member.remove_roles(*roles)
        if roles:
            await ctx.send(f"{len(roles)} topic" + [" has", "s have"][len(roles) > 1] + " been removed successfully.")
        else:
            await ctx.send("No topic has been removed.")

    @btp.command(name="*")
    @permission_level(1)
    async def register_role(self, ctx: Context, *, topic: str):
        """
        register a new topic
        """

        guild: Guild = ctx.guild
        for role in guild.roles:
            if role.name.lower() == topic.lower():
                break
        else:
            role: Role = await guild.create_role(name=topic, mentionable=True)

        if await run_in_thread(db.get, BTPRole, role.id) is not None:
            raise CommandError("Topic has already been registered.")
        if role > ctx.me.top_role:
            raise CommandError(f"Topic could not be registered because `@{role}` is higher than `@{ctx.me.top_role}`.")
        if role.managed:
            raise CommandError(f"Topic could not be registered because `@{role}` cannot be assigned manually.")

        await run_in_thread(BTPRole.create, role.id)
        await ctx.send("Topic has been registered successfully.")

    @btp.command(name="/")
    @permission_level(1)
    async def unregister_role(self, ctx: Context, *, topic: str):
        """
        delete a topic
        """

        guild: Guild = ctx.guild
        for role in guild.roles:
            if role.name.lower() == topic.lower():
                break
        else:
            raise CommandError("Topic has not been registered.")
        if (btp_role := await run_in_thread(db.get, BTPRole, role.id)) is None:
            raise CommandError("Topic has not been registered.")

        await run_in_thread(db.delete, btp_role)
        await role.delete()
        await ctx.send("Topic has been deleted successfully.")
