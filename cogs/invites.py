import re
from typing import Optional

import requests
from discord import Invite, Member, Guild, Embed, Message, NotFound, Forbidden, HTTPException
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError, Converter, BadArgument

from database import run_in_thread, db
from models.allowed_invite import AllowedInvite
from permission import Permission
from translations import translations
from util import permission_level, check_permissions, send_to_changelog, get_prefix


class AllowedServerConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> AllowedInvite:
        try:
            invite: Invite = await ctx.bot.fetch_invite(argument)
            if invite.guild is None:
                raise CommandError(translations.invalid_invite)
            row = await run_in_thread(db.get, AllowedInvite, invite.guild.id)
            if row is not None:
                return row
        except (NotFound, HTTPException):
            pass

        if argument.isnumeric():
            row = await run_in_thread(db.get, AllowedInvite, int(argument))
            if row is not None:
                return row

        for row in await run_in_thread(db.all, AllowedInvite):  # type: AllowedInvite
            if row.guild_name.lower().strip() == argument.lower().strip() or row.code == argument:
                return row

        raise BadArgument(translations.allowed_server_not_found)


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
        if message.guild is None or message.author.bot:
            return True
        if await check_permissions(message.author, Permission.invite_bypass):
            return True

        forbidden = []
        legal_invite = False
        for url, *_ in re.findall(r"((https?://)?([a-zA-Z0-9\-_~]+\.)+[a-zA-Z0-9\-_~]+(/\S*)?)", message.content):
            if (url := get_discord_invite(url)) is None:
                continue
            try:
                invite = await self.bot.fetch_invite(url)
            except NotFound:
                continue
            except Forbidden:
                forbidden.append(f"`{url}` (banned from this server)")
                continue
            if invite.guild is None:
                continue
            if invite.guild == message.guild:
                legal_invite = True
                continue
            if await run_in_thread(db.get, AllowedInvite, invite.guild.id) is None:
                forbidden.append(f"`{invite.code}` ({invite.guild.name})")
            else:
                legal_invite = True
        if forbidden:
            can_delete = message.channel.permissions_for(message.guild.me).manage_messages
            if can_delete:
                await message.delete()
            prefix = await get_prefix()
            await message.channel.send(
                translations.f_illegal_invite_link(message.author.mention, prefix + "invites list"), delete_after=30
            )
            if can_delete:
                await send_to_changelog(
                    message.guild,
                    translations.f_log_illegal_invite(
                        message.author.mention, message.channel.mention, ", ".join(forbidden)
                    ),
                )
            else:
                await send_to_changelog(
                    message.guild,
                    translations.f_log_illegal_invite_not_deleted(
                        message.author.mention, message.channel.mention, ", ".join(forbidden)
                    ),
                )
            return False
        elif legal_invite:
            await message.add_reaction(chr(9989))
        return True

    async def on_message(self, message: Message):
        return await self.check_message(message)

    async def on_message_edit(self, _, after: Message):
        return await self.check_message(after)

    async def check_invite(self, url: str) -> bool:
        try:
            await self.bot.fetch_invite(url)
        except (NotFound, HTTPException):
            return False
        else:
            return True

    @commands.group(aliases=["i"])
    @guild_only()
    async def invites(self, ctx: Context):
        """
        manage allowed discord invites
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(self.invites)

    @invites.command(name="list", aliases=["l", "?"])
    async def list_invites(self, ctx: Context):
        """
        list allowed discord servers
        """

        out = []
        for row in sorted(await run_in_thread(db.query, AllowedInvite), key=lambda a: a.guild_name):
            out.append(f"- {row.guild_name} ({row.guild_id})")
        if out:
            await ctx.send(translations.allowed_servers_header + "\n```\n" + "\n".join(out) + "```")
        else:
            await ctx.send(translations.no_server_allowed)

    @invites.command(name="show", aliases=["info", "s", "i"])
    async def show_invite(self, ctx: Context, *, invite: AllowedServerConverter):
        """
        show more information about an allowed discord server
        """

        invite: AllowedInvite
        date = invite.created_at
        if await self.check_invite(invite.code):
            invite_title = translations.invite_link
        else:
            invite_title = translations.invite_link_expired

        embed = Embed(title=translations.allowed_server, color=0x007700)
        embed.add_field(name=translations.server_name, value=invite.guild_name)
        embed.add_field(name=translations.server_id, value=invite.guild_id)
        embed.add_field(name=invite_title, value=f"https://discord.gg/{invite.code}")
        embed.add_field(name=translations.applicant, value=f"<@{invite.applicant}>")
        embed.add_field(name=translations.approver, value=f"<@{invite.approver}>")
        embed.add_field(name=translations.date, value=f"{date.day:02}.{date.month:02}.{date.year:02}")
        await ctx.send(embed=embed)

    @invites.command(name="add", aliases=["+", "a"])
    @permission_level(Permission.invite_manage)
    async def add_invite(self, ctx: Context, invite: Invite, applicant: Member):
        """
        allow a new discord server
        """

        if invite.guild is None:
            raise CommandError(translations.invalid_invite)

        guild: Guild = invite.guild
        if await run_in_thread(db.get, AllowedInvite, guild.id) is not None:
            raise CommandError(translations.server_already_whitelisted)

        await run_in_thread(AllowedInvite.create, guild.id, invite.code, guild.name, applicant.id, ctx.author.id)
        await ctx.send(translations.server_whitelisted)
        await send_to_changelog(ctx.guild, translations.f_log_server_whitelisted(guild.name))

    @invites.command(name="update", aliases=["u"])
    async def update_invite(self, ctx: Context, invite: Invite):
        """
        update the invite link of an allowed discord server
        """

        if invite.guild is None:
            raise CommandError(translations.invalid_invite)

        guild: Guild = invite.guild
        row: Optional[AllowedInvite] = await run_in_thread(db.get, AllowedInvite, guild.id)
        if row is None:
            raise CommandError(translations.server_not_whitelisted)

        if not await check_permissions(ctx.author, Permission.invite_manage) and ctx.author.id != row.applicant:
            raise CommandError(translations.not_allowed)

        await run_in_thread(AllowedInvite.update, guild.id, invite.code)
        await ctx.send(translations.f_invite_updated(row.guild_name))
        await send_to_changelog(ctx.guild, translations.f_log_invite_updated(ctx.author.mention, row.guild_name))

    @invites.command(name="remove", aliases=["r", "del", "d", "-"])
    @permission_level(Permission.invite_manage)
    async def remove_invite(self, ctx: Context, *, server: AllowedServerConverter):
        """
        disallow a discord server
        """

        server: AllowedInvite
        await run_in_thread(db.delete, server)
        await ctx.send(translations.server_removed)
        await send_to_changelog(ctx.guild, translations.f_log_server_removed(server.guild_name))
