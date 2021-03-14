from typing import Optional

from discord import Embed, Message, Status, Game
from discord.ext import commands, tasks
from discord.ext.commands import Context

from PyDrocsid.cog import Cog
from PyDrocsid.config import Config
from PyDrocsid.github_api import GitHubUser, get_users, get_repo_description
from PyDrocsid.translations import t
from PyDrocsid.util import send_long_embed, get_prefix
from .colors import Colors
from .permissions import InfoPermission
from ..contributor import Contributor

tg = t.g
t = t.info


class BotInfoCog(Cog, name="Bot Information"):
    CONTRIBUTORS = [Contributor.Defelo, Contributor.ce_phox]
    PERMISSIONS = InfoPermission

    def __init__(self, *, info_icon: Optional[str] = None):
        super().__init__()

        self.info_icon: Optional[str] = info_icon
        self.repo_description: str = ""
        self.github_users: Optional[dict[str, GitHubUser]] = {}
        self.current_status = 0

    async def load_github_users(self):
        self.github_users = await get_users([c for _, c in Config.CONTRIBUTORS]) or {}

    def format_contributor(self, contributor: Contributor, long: bool = False) -> Optional[str]:
        discord_id, github_id = contributor

        discord_mention = f"<@{discord_id}>" if discord_id else None

        github_profile = None
        if github_id in self.github_users:
            _, name, profile = self.github_users[github_id]
            github_profile = f"[[{name}]]({profile})"

        if not discord_mention and not github_profile:
            return None

        if not long:
            return discord_mention or github_profile

        return " ".join(x for x in [discord_mention, github_profile] if x)

    async def on_ready(self):
        try:
            self.status_loop.start()
        except RuntimeError:
            self.status_loop.restart()

    @tasks.loop(seconds=20)
    async def status_loop(self):
        await self.bot.change_presence(status=Status.online, activity=Game(name=t.profile_status[self.current_status]))
        self.current_status = (self.current_status + 1) % len(t.profile_status)

    async def build_info_embed(self, authorized: bool) -> Embed:
        embed = Embed(title=Config.NAME, colour=Colors.info, description=t.bot_description)

        if self.info_icon:
            embed.set_thumbnail(url=self.info_icon)

        prefix: str = await get_prefix()

        features = t.features
        if authorized:
            features += t.admin_features

        embed.add_field(
            name=t.features_title,
            value="\n".join(f":small_orange_diamond: {feature}" for feature in features),
            inline=False,
        )

        if not self.github_users:
            await self.load_github_users()

        embed.add_field(name=t.author_title, value=self.format_contributor(Config.AUTHOR), inline=True)

        embed.add_field(
            name=t.contributors_title,
            value=" ".join(
                f
                for c, _ in Config.CONTRIBUTORS.most_common()
                if (f := self.format_contributor(c)) and c != Config.AUTHOR
            ),
            inline=True,
        )

        embed.add_field(name=t.version_title, value=Config.VERSION, inline=True)
        embed.add_field(name=t.github_title, value=Config.REPO_LINK, inline=False)
        embed.add_field(name=t.prefix_title, value=f"`{prefix}` or {self.bot.user.mention}", inline=True)
        embed.add_field(name=t.help_command_title, value=f"`{prefix}help`", inline=True)
        embed.add_field(
            name=t.bugs_features_title,
            value=t.bugs_features(repo=Config.REPO_LINK),
            inline=False,
        )
        return embed

    @commands.command(aliases=["gh"])
    async def github(self, ctx: Context):
        """
        return the github link
        """

        if not self.repo_description:
            self.repo_description = await get_repo_description(Config.REPO_OWNER, Config.REPO_NAME)

        embed = Embed(
            title=f"{Config.REPO_OWNER}/{Config.REPO_NAME}",
            description=self.repo_description,
            colour=Colors.github,
            url=Config.REPO_LINK,
        )
        embed.set_author(name="GitHub", icon_url="https://github.com/fluidicon.png")
        embed.set_thumbnail(url=Config.REPO_ICON)
        await ctx.send(embed=embed)

    @commands.command()
    async def version(self, ctx: Context):
        """
        show version
        """

        embed = Embed(title=f"{Config.NAME} v{Config.VERSION}", colour=Colors.version)
        await ctx.send(embed=embed)

    @commands.command(aliases=["infos", "about"])
    async def info(self, ctx: Context):
        """
        show information about the bot
        """

        await send_long_embed(ctx, await self.build_info_embed(False))

    @commands.command(aliases=["admininfos"])
    @InfoPermission.admininfo.check
    async def admininfo(self, ctx: Context):
        """
        show information about the bot (admin view)
        """

        await send_long_embed(ctx, await self.build_info_embed(True))

    @commands.command(aliases=["contri", "con"])
    async def contributors(self, ctx: Context):
        """
        show list of contributors
        """

        if not self.github_users:
            await self.load_github_users()

        await send_long_embed(
            ctx,
            Embed(
                title=t.contributors_title,
                colour=Colors.info,
                description="\n".join(
                    f":small_orange_diamond: {f}"
                    for c, cnt in [(Config.AUTHOR, 0), *Config.CONTRIBUTORS.most_common()]
                    if (f := self.format_contributor(c, long=True)) and (c != Config.AUTHOR or not cnt)
                ),
            ),
        )

    async def on_bot_ping(self, message: Message):
        await message.channel.send(embed=await self.build_info_embed(False))
