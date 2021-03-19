import re
from typing import Optional

import requests
from discord import Invite, Member, Guild, Embed, Message, NotFound, Forbidden, HTTPException
from discord.ext import commands
from discord.ext.commands import guild_only, Context, CommandError, Converter, BadArgument, UserInputError
from urllib3.exceptions import LocationParseError

from PyDrocsid.async_thread import run_in_thread
from PyDrocsid.cog import Cog
from PyDrocsid.database import db_thread, db
from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.events import StopEventHandling
from PyDrocsid.logger import get_logger
from PyDrocsid.translations import t
from PyDrocsid.util import get_prefix, send_long_embed
from .colors import Colors
from .models import InviteLog, AllowedInvite
from .permissions import InvitesPermission
from cogs.library.contributor import Contributor
from cogs.library.pubsub import send_to_changelog, get_ulog_entries

tg = t.g
t = t.invites

logger = get_logger(__name__)


class AllowedServerConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> AllowedInvite:
        try:
            invite: Invite = await ctx.bot.fetch_invite(argument)
            if invite.guild is None:
                raise CommandError(t.invalid_invite)
            row = await db_thread(db.get, AllowedInvite, invite.guild.id)
            if row is not None:
                return row
        except (NotFound, HTTPException):
            pass

        if argument.isnumeric():
            row = await db_thread(db.get, AllowedInvite, int(argument))
            if row is not None:
                return row

        for row in await db_thread(db.all, AllowedInvite):  # type: AllowedInvite
            if row.guild_name.lower().strip() == argument.lower().strip() or row.code == argument:
                return row

        raise BadArgument(t.allowed_server_not_found)


def get_discord_invite(url) -> Optional[str]:
    if not re.match(r"^(https?://).*$", url):
        url = "https://" + url
    try:
        url = requests.head(url, allow_redirects=True, timeout=10).url
    except (KeyError, AttributeError, requests.RequestException, UnicodeError, ConnectionError, LocationParseError):
        logger.info("URL could not be resolved: %s", url)
        return None

    if match := re.match(
        r"^https?://discord\.com/(\.*/)*invite/(\.*/)*(?P<code>[a-zA-Z0-9\-]+).*$",
        url,
        re.IGNORECASE,
    ):
        return match.group("code")

    return None


class InvitesCog(Cog, name="Allowed Discord Invites"):
    CONTRIBUTORS = [Contributor.Defelo, Contributor.wolflu, Contributor.TNT2k, Contributor.Florian]
    PERMISSIONS = InvitesPermission

    @get_ulog_entries.subscribe
    async def handle_get_ulog_entries(self, user_id: int):
        out = []
        for log in await db_thread(db.all, InviteLog, applicant=user_id):  # type: InviteLog
            if log.approved:
                out.append((log.timestamp, t.ulog_invite_approved(f"<@{log.mod}>", log.guild_name)))
            else:
                out.append((log.timestamp, t.ulog_invite_removed(f"<@{log.mod}>", log.guild_name)))
        return out

    async def check_message(self, message: Message) -> bool:
        author: Member = message.author
        if message.guild is None or author.bot:
            return True
        if await InvitesPermission.bypass.check_permissions(author):
            return True

        forbidden = []
        legal_invite = False
        for url, *_ in re.findall(r"((https?://)?([a-zA-Z0-9\-_~]+\.)+[a-zA-Z0-9\-_~.]+(/\S*)?)", message.content):
            if (code := await run_in_thread(lambda: get_discord_invite(url))) is None:
                continue
            try:
                invite = await self.bot.fetch_invite(code)
            except NotFound:
                continue
            except Forbidden:
                forbidden.append(f"`{code}` (banned from this server)")
                continue
            if invite.guild is None:
                continue
            if invite.guild == message.guild:
                legal_invite = True
                continue
            if await db_thread(db.get, AllowedInvite, invite.guild.id) is None:
                forbidden.append(f"`{invite.code}` ({invite.guild.name})")
            else:
                legal_invite = True
        if forbidden:
            can_delete = message.channel.permissions_for(message.guild.me).manage_messages
            if can_delete:
                await message.delete()
            prefix = await get_prefix()
            embed = Embed(
                title=t.invites,
                description=t.illegal_invite_link(prefix + "invites list"),
                color=Colors.error,
            )
            await message.channel.send(content=author.mention, embed=embed, delete_after=30)
            if can_delete:
                await send_to_changelog(
                    message.guild,
                    t.log_illegal_invite(
                        f"{author.mention} (`@{author}`, {author.id})",
                        message.channel.mention,
                        ", ".join(forbidden),
                    ),
                )
            else:
                await send_to_changelog(
                    message.guild,
                    t.log_illegal_invite_not_deleted(
                        f"{author.mention} (`@{author}`, {author.id})",
                        message.channel.mention,
                        ", ".join(forbidden),
                    ),
                )
            return False
        if legal_invite:
            await message.add_reaction(name_to_emoji["white_check_mark"])
        return True

    async def on_message(self, message: Message):
        if not await self.check_message(message):
            raise StopEventHandling

    async def on_message_edit(self, _, after: Message):
        if not await self.check_message(after):
            raise StopEventHandling

    async def check_invite(self, url: str) -> Optional[Invite]:
        try:
            return await self.bot.fetch_invite(url)
        except (NotFound, HTTPException):
            return None

    @commands.group(aliases=["i"])
    @guild_only()
    async def invites(self, ctx: Context):
        """
        manage allowed discord invites
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @invites.command(name="list", aliases=["l", "?"])
    async def invites_list(self, ctx: Context):
        """
        list allowed discord servers
        """

        out = []
        for row in sorted(await db_thread(db.all, AllowedInvite), key=lambda a: a.guild_name):
            out.append(f":small_orange_diamond: {row.guild_name} ({row.guild_id})")
        embed = Embed(title=t.allowed_servers_title, colour=Colors.error)
        embed.description = t.allowed_servers_description
        if out:
            embed.colour = Colors.Invites
            embed.description += "\n".join(out)
            await send_long_embed(ctx, embed)
        else:
            embed.description = t.no_server_allowed
            await ctx.send(embed=embed)

    @invites.command(name="show", aliases=["info", "s", "i"])
    async def invites_show(self, ctx: Context, *, invite: AllowedServerConverter):
        """
        show more information about an allowed discord server
        """

        invite: AllowedInvite
        date = invite.created_at
        embed = Embed(title=t.allowed_server, color=Colors.Invites)
        invite_guild = await self.check_invite(invite.code)
        if invite_guild is not None:
            invite_title = t.invite_link
            embed.set_thumbnail(url=invite_guild.guild.icon_url)
        else:
            invite_title = t.invite_link_expired

        embed.add_field(name=t.server_name, value=invite.guild_name)
        embed.add_field(name=t.server_id, value=invite.guild_id)
        embed.add_field(name=invite_title, value=f"https://discord.gg/{invite.code}")
        embed.add_field(name=t.applicant, value=f"<@{invite.applicant}>")
        embed.add_field(name=t.approver, value=f"<@{invite.approver}>")
        embed.add_field(name=t.date, value=f"{date.day:02}.{date.month:02}.{date.year:02}")

        await ctx.send(embed=embed)

    @invites.command(name="add", aliases=["+", "a"])
    @InvitesPermission.manage.check
    async def invites_add(self, ctx: Context, invite: Invite, applicant: Member):
        """
        allow a new discord server
        """

        if invite.guild is None:
            raise CommandError(t.invalid_invite)

        guild: Guild = invite.guild
        if await db_thread(db.get, AllowedInvite, guild.id) is not None:
            raise CommandError(t.server_already_whitelisted)

        await db_thread(AllowedInvite.create, guild.id, invite.code, guild.name, applicant.id, ctx.author.id)
        await db_thread(InviteLog.create, guild.id, guild.name, applicant.id, ctx.author.id, True)
        embed = Embed(title=t.invites, description=t.server_whitelisted, color=Colors.Invites)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, t.log_server_whitelisted(guild.name))

    @invites.command(name="update", aliases=["u"])
    async def invites_update(self, ctx: Context, invite: Invite):
        """
        update the invite link of an allowed discord server
        """

        if invite.guild is None:
            raise CommandError(t.invalid_invite)

        guild: Guild = invite.guild
        row: Optional[AllowedInvite] = await db_thread(db.get, AllowedInvite, guild.id)
        if row is None:
            raise CommandError(t.server_not_whitelisted)

        if not await InvitesPermission.manage.check_permissions(ctx.author) and ctx.author.id != row.applicant:
            raise CommandError(tg.not_allowed)

        await db_thread(AllowedInvite.update, guild.id, invite.code, guild.name)
        embed = Embed(
            title=t.invites,
            description=t.invite_updated(guild.name),
            color=Colors.Invites,
        )
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, t.log_invite_updated(ctx.author.mention, guild.name))

    @invites.command(name="remove", aliases=["r", "del", "d", "-"])
    @InvitesPermission.manage.check
    async def invites_remove(self, ctx: Context, *, server: AllowedServerConverter):
        """
        disallow a discord server
        """

        server: AllowedInvite
        await db_thread(db.delete, server)
        await db_thread(InviteLog.create, server.guild_id, server.guild_name, server.applicant, ctx.author.id, False)
        embed = Embed(title=t.invites, description=t.server_removed, color=Colors.Invites)
        await ctx.send(embed=embed)
        await send_to_changelog(ctx.guild, t.log_server_removed(server.guild_name))
