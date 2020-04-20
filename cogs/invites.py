import re
from typing import Union, Optional

import requests
from discord import Invite, Member, Guild, Embed, Message, NotFound
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.allowed_invite import AllowedInvite
from util import permission_level, check_access, send_to_changelog


def get_discord_invite(url) -> Optional[str]:
    while True:
        if re.match(r"^(https?://)?(discord(.gg|app.com/invite)/[a-zA-Z0-9\-_]+)$", url):
            return url

        if not re.match(r"^(https?://).*$", url):
            url = "https://" + url

        try:
            response = requests.head(url)
        except (KeyError, AttributeError, requests.RequestException, UnicodeError, ConnectionError):
            return None

        if response.is_redirect and "Location" in response.headers:
            url = response.headers["Location"]
        else:
            return None


class InvitesCog(Cog, name="Allowed Discord Invites"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def check_message(self, message: Message) -> bool:
        if message.guild is None or message.author.bot or await check_access(message.author):
            return True

        forbidden = []
        for url, *_ in re.findall(r"((https?://)?([a-zA-Z0-9\-_~]+\.)+[a-zA-Z0-9\-_~]+(/\S*)?)", message.content):
            if (url := get_discord_invite(url)) is None:
                continue
            try:
                invite = await self.bot.fetch_invite(url)
            except NotFound:
                continue
            if invite.guild is None or invite.guild == message.guild:
                continue
            if await run_in_thread(db.get, AllowedInvite, invite.guild.id) is None:
                forbidden.append(f"`{invite.code}` ({invite.guild.name})")
        if forbidden:
            can_delete = message.channel.permissions_for(message.guild.me).manage_messages
            if can_delete:
                await message.delete()
            await message.channel.send(
                f"{message.author.mention} Illegal discord invite link! "
                "Please contact a team member to submit a request for whitelisting the invitation. "
                "Use the command `.invites list` to get a list of all allowed discord servers."
            )
            if can_delete:
                await send_to_changelog(
                    message.guild,
                    f"Deleted a message of {message.author.mention} in {message.channel.mention} "
                    f"because it contained one or more illegal discord invite links: {', '.join(forbidden)}",
                )
            else:
                await send_to_changelog(
                    message.guild,
                    f"{message.author.mention} sent a message in {message.channel.mention} which contained one or "
                    f"more illegal discord invite links: {', '.join(forbidden)}\n"
                    "The message could not be deleted because I don't have `manage_messages` permission "
                    "in this channel.",
                )
            return False
        return True

    async def on_message(self, message: Message):
        return await self.check_message(message)

    async def on_message_edit(self, _, after: Message):
        return await self.check_message(after)

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
        for row in sorted(await run_in_thread(db.query, AllowedInvite), key=lambda a: a.guild_name):
            out.append(f"- {row.guild_name} (discord.gg/{row.code})")
        if out:
            await ctx.send("Allowed discord servers:\n```\n" + "\n".join(out) + "```")
        else:
            await ctx.send("No discord servers allowed.")

    @invites.command(name="show", aliases=["info"])
    async def show_invite(self, ctx: Context, *, invite: Union[Invite, str]):
        """
        show more information about an allowed discord server
        """

        row: Optional[AllowedInvite]
        if isinstance(invite, str):
            for row in await run_in_thread(db.query, AllowedInvite):  # type: AllowedInvite
                if row.guild_name.lower() == invite.lower():
                    break
            else:
                row = None
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
        await send_to_changelog(ctx.guild, f"Discord Server `{guild.name}` has been added to the whitelist.")

    @invites.command(name="remove")
    @permission_level(1)
    async def remove_invite(self, ctx: Context, *, server: Union[Invite, int, str]):
        """
        disallow a discord server
        """

        row: Optional[AllowedInvite]
        if isinstance(server, Invite):
            if server.guild is None:
                raise CommandError("Invalid invite.")
            row = await run_in_thread(db.get, AllowedInvite, server.guild.id)
        elif isinstance(server, str):
            for row in await run_in_thread(db.all, AllowedInvite):  # type: AllowedInvite
                if row.guild_name.lower() == server.lower():
                    break
            else:
                row = None
        else:
            row = await run_in_thread(db.get, AllowedInvite, server)

        if row is None:
            raise CommandError("Server is not whitelisted.")

        await run_in_thread(db.delete, row)
        await ctx.send("Server has been removed from the whitelist successfully.")
        await send_to_changelog(ctx.guild, f"Discord Server `{row.guild_name}` has been removed from the whitelist.")
