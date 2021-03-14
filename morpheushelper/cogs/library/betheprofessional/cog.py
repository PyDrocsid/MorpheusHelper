import string
from typing import List

from discord import Role, Guild, Member, Embed
from discord.ext import commands
from discord.ext.commands import guild_only, Context, CommandError, UserInputError

from PyDrocsid.cog import Cog
from PyDrocsid.database import db_thread, db
from PyDrocsid.translations import t
from PyDrocsid.util import calculate_edit_distance, send_long_embed
from .colors import Colors
from .models import BTPRole
from .permissions import BeTheProfessionalPermission
from ..contributor import Contributor
from ..pubsub import send_to_changelog

tg = t.g
t = t.betheprofessional


def split_topics(topics: str) -> List[str]:
    return [topic for topic in map(str.strip, topics.replace(";", ",").split(",")) if topic]


async def parse_topics(guild: Guild, topics: str, author: Member) -> List[Role]:
    roles: List[Role] = []
    all_topics: List[Role] = await list_topics(guild)
    for topic in split_topics(topics):
        for role in guild.roles:
            if role.name.lower() == topic.lower():
                if role in all_topics:
                    break
                if not role.managed and role >= guild.me.top_role:
                    raise CommandError(t.youre_not_the_first_one(topic, author.mention))
        else:
            if all_topics:
                best_match = min(
                    [r.name for r in all_topics], key=lambda a: calculate_edit_distance(a.lower(), topic.lower())
                )
                raise CommandError(t.topic_not_found_did_you_mean(topic, best_match))
            raise CommandError(t.topic_not_found(topic))
        roles.append(role)
    return roles


async def list_topics(guild: Guild) -> List[Role]:
    roles: List[Role] = []
    for btp_role in await db_thread(db.all, BTPRole):
        if (role := guild.get_role(btp_role.role_id)) is None:
            await db_thread(db.delete, btp_role)
        else:
            roles.append(role)
    return roles


async def unregister_roles(ctx: Context, topics: str, *, delete_roles: bool):
    guild: Guild = ctx.guild
    roles: List[Role] = []
    btp_roles: List[BTPRole] = []
    names = split_topics(topics)
    if not names:
        raise UserInputError

    for topic in names:
        for role in guild.roles:
            if role.name.lower() == topic.lower():
                break
        else:
            raise CommandError(t.topic_not_registered(topic))
        if (btp_role := await db_thread(db.get, BTPRole, role.id)) is None:
            raise CommandError(t.topic_not_registered(topic))

        roles.append(role)
        btp_roles.append(btp_role)

    for role, btp_role in zip(roles, btp_roles):
        await db_thread(db.delete, btp_role)
        if delete_roles:
            await role.delete()

    embed = Embed(title=t.betheprofessional, colour=Colors.BeTheProfessional)
    embed.description = t.topics_unregistered(cnt=len(roles))
    await send_to_changelog(
        ctx.guild, t.log_topics_unregistered(cnt=len(roles), topics=", ".join(f"`{r}`" for r in roles))
    )
    await send_long_embed(ctx, embed)


class BeTheProfessionalCog(Cog, name="Self Assignable Topic Roles"):
    CONTRIBUTORS = [Contributor.Defelo, Contributor.wolflu, Contributor.MaxiHuHe04, Contributor.AdriBloober]
    PERMISSIONS = BeTheProfessionalPermission

    @commands.command(name="?")
    @guild_only()
    async def list_roles(self, ctx: Context):
        """
        list all registered topics
        """

        embed = Embed(title=t.available_topics_header, colour=Colors.BeTheProfessional)
        out = [role.name for role in await list_topics(ctx.guild)]
        if not out:
            embed.colour = Colors.error
            embed.description = t.no_topics_registered
            await ctx.send(embed=embed)
            return

        out.sort(key=str.lower)
        embed.description = ", ".join(f"`{topic}`" for topic in out)
        await send_long_embed(ctx, embed)

    @commands.command(name="+")
    @guild_only()
    async def add_role(self, ctx: Context, *, topics: str):
        """
        add one or more topics (comma separated) you are interested in
        """

        member: Member = ctx.author
        roles: List[Role] = [r for r in await parse_topics(ctx.guild, topics, ctx.author) if r not in member.roles]

        await member.add_roles(*roles)

        embed = Embed(title=t.betheprofessional, colour=Colors.BeTheProfessional)
        embed.description = t.topics_added(cnt=len(roles))
        if not roles:
            embed.colour = Colors.error

        await ctx.send(embed=embed)

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

        embed = Embed(title=t.betheprofessional, colour=Colors.BeTheProfessional)
        embed.description = t.topics_removed(cnt=len(roles))
        await ctx.send(embed=embed)

    @commands.command(name="*")
    @BeTheProfessionalPermission.manage.check
    @guild_only()
    async def register_role(self, ctx: Context, *, topics: str):
        """
        register one or more new topics
        """

        guild: Guild = ctx.guild
        names = split_topics(topics)
        if not names:
            raise UserInputError

        valid_chars = set(string.ascii_letters + string.digits + " !#$%&'()+-./:<=>?[\\]^_`{|}~")
        to_be_created: List[str] = []
        roles: List[Role] = []
        for topic in names:
            if any(c not in valid_chars for c in topic):
                raise CommandError(t.f_topic_invalid_chars(topic))

            for role in guild.roles:
                if role.name.lower() == topic.lower():
                    break
            else:
                to_be_created.append(topic)
                continue

            if await db_thread(db.get, BTPRole, role.id) is not None:
                raise CommandError(t.topic_already_registered(topic))
            if role >= ctx.me.top_role:
                raise CommandError(t.topic_not_registered_too_high(role, ctx.me.top_role))
            if role.managed:
                raise CommandError(t.topic_not_registered_managed_role(role))
            roles.append(role)

        for name in to_be_created:
            roles.append(await guild.create_role(name=name, mentionable=True))

        for role in roles:
            await db_thread(BTPRole.create, role.id)

        embed = Embed(title=t.betheprofessional, colour=Colors.BeTheProfessional)
        embed.description = t.topics_registered(cnt=len(roles))
        await send_to_changelog(
            ctx.guild, t.log_topics_registered(cnt=len(roles), topics=", ".join(f"`{r}`" for r in roles))
        )
        await ctx.send(embed=embed)

    @commands.command(name="/")
    @BeTheProfessionalPermission.manage.check
    @guild_only()
    async def delete_roles(self, ctx: Context, *, topics: str):
        """
        delete one or more topics
        """

        await unregister_roles(ctx, topics, delete_roles=True)

    @commands.command(name="%")
    @BeTheProfessionalPermission.manage.check
    @guild_only()
    async def unregister_roles(self, ctx: Context, *, topics: str):
        """
        unregister one or more topics without deleting the roles
        """

        await unregister_roles(ctx, topics, delete_roles=False)
