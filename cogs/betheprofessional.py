from typing import Union

from discord import Role, Guild
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.btp_role import BTPRole
from util import permission_level


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

        pass

    @btp.command(name="+")
    async def add_role(self, ctx: Context, *topics: Role):
        """
        add one or more topics you are interested in
        """

        pass

    @btp.command(name="-")
    async def remove_roles(self, ctx: Context, *topics: Union[Role, str]):
        """
        remove one or more topics (use * to remove all topics)
        """

        pass

    @btp.command(name="*")
    @permission_level(1)
    async def register_role(self, ctx: Context, topic: Union[Role, str]):
        """
        register a new topic
        """

        guild: Guild = ctx.guild
        if isinstance(topic, str):
            role: Role = await guild.create_role(name=topic, mentionable=True)
        else:
            role: Role = topic

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
    async def unregister_role(self, ctx: Context, topic: Role):
        """
        deletes a topic
        """

        if (role := await run_in_thread(db.get, BTPRole, topic.id)) is None:
            raise CommandError("Topic has not been registered.")

        await run_in_thread(db.delete, role)
        await topic.delete()
        await ctx.send("Topic has been deleted successfully.")
