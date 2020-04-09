from typing import Union, Optional

from discord import Invite, Member, Guild, Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.allowed_invite import AllowedInvite
from util import permission_level


class InvitesCog(Cog, name="Allowed Discord Invites"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group()
    @guild_only()
    async def invites(self, ctx: Context):
        """
        manage allowed discord invites
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.invites)

    @invites.command(name="list")
    async def list_invites(self, ctx: Context):
        """
        list allowed discord servers
        """

        out = []
        for row in await run_in_thread(db.query, AllowedInvite):  # type: AllowedInvite
            out.append(f"- {row.guild_name} (discord.gg/{row.code})")
        if out:
            await ctx.send("Allowed discord servers:\n```\n" + "\n".join(out) + "```")
        else:
            await ctx.send("No discord servers allowed.")

    @invites.command(name="show", aliases=["info"])
    async def show_invite(self, ctx: Context, *, invite: Union[Invite, str]):
        """
        show more information about a allowed discord server
        """

        row: Optional[AllowedInvite] = None
        if isinstance(invite, str):
            for row in await run_in_thread(db.query, AllowedInvite):  # type: AllowedInvite
                if row.guild_name.lower() == invite.lower():
                    break
        else:
            if invite.guild is None:
                raise CommandError("Invalid invite.")
            row = await run_in_thread(db.get, AllowedInvite, invite.guild.id)

        if row is None:
            raise CommandError("Allowed discord server not found.")

        date = row.created_at
        embed = Embed(title="Allowed Discord Server", color=0x007700)
        embed.add_field(name="Server Name", value=row.guild_name)
        embed.add_field(name="Server ID", value=row.guild_id)
        embed.add_field(name="Invite Link", value=f"https://discord.gg/{row.code}")
        embed.add_field(name="Applicant", value=f"<@{row.applicant}>")
        embed.add_field(name="Approver", value=f"<@{row.approver}>")
        embed.add_field(name="Date", value=f"{date.day:02}.{date.month:02}.{date.year:02}")
        await ctx.send(embed=embed)

    @invites.command(name="add")
    @permission_level(1)
    async def add_invite(self, ctx: Context, invite: Invite, applicant: Member):
        """
        allow a new discord server
        """

        if invite.guild is None:
            raise CommandError("Invalid invite.")

        guild: Guild = invite.guild
        if await run_in_thread(db.get, AllowedInvite, guild.id) is not None:
            raise CommandError("This server has already been whitelisted.")

        await run_in_thread(AllowedInvite.create, guild.id, invite.code, guild.name, applicant.id, ctx.author.id)
        await ctx.send("Server has been whitelisted successfully.")

    @invites.command(name="remove")
    @permission_level(1)
    async def remove_invite(self, ctx: Context, server: Union[Invite, int, str]):
        """
        disallow a discord server
        """

        row: Optional[AllowedInvite] = None
        if isinstance(server, Invite):
            if server.guild is None:
                raise CommandError("Invalid invite.")
            row = await run_in_thread(db.get, AllowedInvite, server.guild.id)
        elif isinstance(server, str):
            for row in await run_in_thread(db.query, AllowedInvite):  # type: AllowedInvite
                if row.guild_name.lower() == server.lower():
                    break
        else:
            row = await run_in_thread(db.get, AllowedInvite, server)

        if row is None:
            raise CommandError("Server is not whitelisted.")

        await run_in_thread(db.delete, row)
        await ctx.send("Server has been removed from the whitelist successfully.")
