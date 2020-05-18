from discord import Embed, Guild, Status, Game
from discord import Role
from discord.ext import commands, tasks
from discord.ext.commands import Cog, Bot, guild_only, Context
from discord.utils import get

from database import run_in_thread, db
from models.allowed_invite import AllowedInvite
from models.btp_role import BTPRole
from translations import translations


class InfoCog(Cog, name="Server Information"):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.current_status = 0

    async def on_ready(self):
        try:
            self.status_loop.start()
        except RuntimeError:
            self.status_loop.restart()

    @tasks.loop(seconds=20)
    async def status_loop(self):
        await self.bot.change_presence(
            status=Status.online, activity=Game(name=translations.profile_status[self.current_status])
        )
        self.current_status = (self.current_status + 1) % len(translations.profile_status)

    @commands.group(name="server")
    @guild_only()
    async def server(self, ctx: Context):
        """
        displays information about this discord server
        """

        if ctx.invoked_subcommand is not None:
            return

        guild: Guild = ctx.guild
        embed = Embed(title=guild.name, description=translations.info_description, color=0x005180)
        embed.set_thumbnail(url=guild.icon_url)
        created = guild.created_at.date()
        embed.add_field(name=translations.creation_date, value=f"{created.day}.{created.month}.{created.year}")
        online_count = sum(m.status != Status.offline for m in guild.members)
        embed.add_field(
            name=translations.f_cnt_members(guild.member_count), value=translations.f_cnt_online(online_count)
        )
        embed.add_field(name=translations.owner, value=guild.owner.mention)

        role: Role
        if (role := get(guild.roles, name="Admin")) is not None and role.members:
            embed.add_field(
                name=translations.f_cnt_admins(len(role.members)),
                value="\n".join(":small_orange_diamond: " + m.mention for m in role.members),
            )
        if (role := get(guild.roles, name="Moderator")) is not None and role.members:
            embed.add_field(
                name=translations.f_cnt_mods(len(role.members)),
                value="\n".join(":small_orange_diamond: " + m.mention for m in role.members),
            )
        if (role := get(guild.roles, name="Supporter")) is not None and role.members:
            embed.add_field(
                name=translations.f_cnt_supps(len(role.members)),
                value="\n".join(":small_orange_diamond: " + m.mention for m in role.members),
            )

        bots = [m for m in guild.members if m.bot]
        bots_online = sum(m.status != Status.offline for m in bots)
        embed.add_field(name=translations.f_cnt_bots(len(bots)), value=translations.f_cnt_online(bots_online))
        embed.add_field(
            name=translations.topics, value=translations.f_cnt_topics(len(await run_in_thread(db.all, BTPRole)))
        )
        embed.add_field(
            name=translations.allowed_discord_server,
            value=translations.f_cnt_servers_whitelisted(len(await run_in_thread(db.all, AllowedInvite))),
        )

        await ctx.send(embed=embed)

    @server.command(name="bots")
    async def list_bots(self, ctx: Context):
        """
        list all bots on the server
        """

        guild: Guild = ctx.guild
        bots = [(str(m), m.status != Status.offline) for m in guild.members if m.bot]
        bots.sort(key=lambda m: (-m[1], m[0]))
        out = []
        for (bot, online) in bots:
            out.append(f"- `@{bot}` ({['offline', 'online'][online]})")
        await ctx.send("\n".join(out))
