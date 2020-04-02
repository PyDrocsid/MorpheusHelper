import string
from typing import List
from similar import best_match

from discord import Role, Guild, Member
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.btp_role import BTPRole
from util import permission_level


def split_topics(topics: str) -> List[str]:
    return [topic for topic in map(str.strip, topics.replace(";", ",").split(",")) if topic]


async def filter_role(guild: Guild, role: Role) -> bool:
    p = role.permissions
    if p.administrator or p.ban_members or p.kick_members or p.manage_guild or p.manage_nicknames or p.manage_roles:
        return False
    if await run_in_thread(db.get, BTPRole, role.id) is not None:
        return True
    elif not role.managed and role > guild.me.top_role:
        return False


async def topic_not_found(guild: Guild, topic: str):
    list_of_available_topics = []
    for role in guild.roles:
        if await filter_role(guild, role):
            list_of_available_topics.append(role.name.lower())
    if len(list_of_available_topics) == 0:
        raise CommandError(f"Topic `{topic}` not found.")
    else:
        raise CommandError(f"Topic `{topic}` not found. Did you mean `{best_match(topic.lower(), list_of_available_topics)}`?")


async def parse_topics(guild: Guild, topics: str, author: Member) -> List[Role]:
    roles: List[Role] = []
    for topic in split_topics(topics):
        for role in guild.roles:
            if role.name.lower() == topic.lower():
                if await filter_role(guild, role):
                    break
                elif not role.managed and role > guild.me.top_role:
                    raise CommandError(
                        f"Topic `{topic}` not found.\nYou're not the first one to try this, {author.mention}"
                    )
        else:
            await topic_not_found(guild, topic)  # raise 100% Exception
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

    @commands.command(name="?")
    @guild_only()
    async def list_roles(self, ctx: Context):
        """
        lists all registered topics
        """

        out = [role.name for role in await list_topics(ctx.guild)]
        out.sort()
        if out:
            await ctx.send("Available Topics:\n" + ", ".join(out))
        else:
            await ctx.send("No topics have been registered yet.")

    @commands.command(name="+")
    @guild_only()
    async def add_role(self, ctx: Context, *, topics: str):
        """
        add one or more topics you are interested in
        """

        member: Member = ctx.author
        roles: List[Role] = [r for r in await parse_topics(ctx.guild, topics, ctx.author) if r not in member.roles]

        await member.add_roles(*roles)
        if len(roles) > 1:
            await ctx.send(f"{len(roles)} topics have been added successfully.")
        elif len(roles) == 1:
            await ctx.send(f"Topic has been added successfully.")
        else:
            await ctx.send("No topic has been added.")

    @commands.command(name="-")
    @guild_only()
    async def remove_roles(self, ctx: Context, *, topics: str):
        """
        remove one or more topics (use * to remove all topics)
        """

        member: Member = ctx.author
        if topics.strip() == "*":
            roles: List[Role] = await list_topics(ctx.guild)
        else:
            roles: List[Role] = await parse_topics(ctx.guild, topics, ctx.author)
        roles = [r for r in roles if r in member.roles]

        await member.remove_roles(*roles)
        if len(roles) > 1:
            await ctx.send(f"{len(roles)} topics have been removed successfully.")
        elif len(roles) == 1:
            await ctx.send(f"Topic has been removed successfully.")
        else:
            await ctx.send("No topic has been removed.")

    @commands.command(name="*")
    @permission_level(1)
    @guild_only()
    async def register_role(self, ctx: Context, *, topics: str):
        """
        register one or more new topics
        """

        guild: Guild = ctx.guild
        names = split_topics(topics)
        if not names:
            await ctx.send_help(self.register_role)
            return

        valid_chars = set(string.ascii_letters + string.digits + " !\"#$%&'()*+-./:<=>?[\\]^_`{|}~")
        to_be_created: List[str] = []
        roles: List[Role] = []
        for topic in names:
            if any(c not in valid_chars for c in topic):
                raise CommandError(f"Topic name `{topic}` contains invalid characters.")
            elif not topic:
                raise CommandError("Topic name may not be empty.")

            for role in guild.roles:
                if role.name.lower() == topic.lower():
                    break
            else:
                to_be_created.append(topic)
                continue

            if await run_in_thread(db.get, BTPRole, role.id) is not None:
                raise CommandError(f"Topic `{topic}` has already been registered.")
            if role > ctx.me.top_role:
                raise CommandError(
                    f"Topic could not be registered because `@{role}` is higher than `@{ctx.me.top_role}`."
                )
            if role.managed:
                raise CommandError(f"Topic could not be registered because `@{role}` cannot be assigned manually.")
            roles.append(role)

        for name in to_be_created:
            roles.append(await guild.create_role(name=name, mentionable=True))

        for role in roles:
            await run_in_thread(BTPRole.create, role.id)

        if len(roles) > 1:
            await ctx.send(f"{len(roles)} topics have been registered successfully.")
        elif len(roles) == 1:
            await ctx.send(f"Topic has been registered successfully.")

    @commands.command(name="/")
    @permission_level(1)
    @guild_only()
    async def unregister_role(self, ctx: Context, *, topics: str):
        """
        deletes one or more topics
        """

        guild: Guild = ctx.guild
        roles: List[Role] = []
        btp_roles: List[BTPRole] = []
        names = split_topics(topics)
        if not names:
            await ctx.send_help(self.register_role)
            return
        for topic in names:
            for role in guild.roles:
                if role.name.lower() == topic.lower():
                    break
            else:
                raise CommandError(f"Topic `{topic}` has not been registered.")
            if (btp_role := await run_in_thread(db.get, BTPRole, role.id)) is None:
                raise CommandError(f"Topic `{topic}` has not been registered.")

            roles.append(role)
            btp_roles.append(btp_role)

        for role, btp_role in zip(roles, btp_roles):
            await run_in_thread(db.delete, btp_role)
            await role.delete()
        if len(roles) > 1:
            await ctx.send(f"{len(roles)} topics have been deleted successfully.")
        elif len(roles) == 1:
            await ctx.send(f"Topic has been deleted successfully.")
