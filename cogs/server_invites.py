from discord import Invite, Guild, Member, utils, NotFound
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context

from database import run_in_thread, db
from models.mod import Join
from models.server_invites import ServerInvites
from util import send_help


class ServerInvitesCog(Cog, name="Server invites"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_ready(self):
        guild: Guild = self.bot.guilds[0]
        guild_invites = await guild.invites()

        for invite in await run_in_thread(db.query, ServerInvites, is_expired=False):
            try:
                guild_invite = utils.get(guild_invites, code=invite.code)
                if invite.uses is not guild_invite.uses:
                    await run_in_thread(ServerInvites.update, invite.code, guild_invite.uses)
            except NotFound:
                await run_in_thread(ServerInvites.updateExpired, invite.code, True)

        for invite in guild_invites:
            db_invite = await run_in_thread(db.first, ServerInvites, code=invite.code, is_expired=False)
            if db_invite is None:
                await run_in_thread(
                    ServerInvites.create,
                    invite.inviter.id,
                    str(invite.inviter),
                    invite.code,
                    invite.uses,
                    invite.created_at,
                )

    async def on_member_join(self, member: Member):
        invites_before_join = await run_in_thread(db.query, ServerInvites, is_expired=False)
        for invite in await member.guild.invites():
            db_invite = utils.find(lambda i: i.code == invite.code, invites_before_join)
            if invite.uses > db_invite.uses:
                await run_in_thread(Join.create, member.id, str(member), invite.code)
                await run_in_thread(ServerInvites.update, db_invite.code, invite.uses)
                return

        return True

    async def on_invite_create(self, invite: Invite):
        await run_in_thread(
            ServerInvites.create, invite.inviter.id, str(invite.inviter), invite.code, invite.uses, invite.created_at
        )
        return True

    async def on_invite_delete(self, invite: Invite):
        await run_in_thread(ServerInvites.updateExpired, invite.code, True)
        return True

    @commands.group(name="serverinvites", aliases=["si"])
    @guild_only()
    async def server_invites(self, ctx: Context):
        """
        manage all created invites for this server
        """

        if ctx.invoked_subcommand is None:
            await send_help(ctx, self.server_invites)
