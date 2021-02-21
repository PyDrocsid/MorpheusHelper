from typing import Optional

from discord import Embed, Message, Status, Game
from discord.ext import commands, tasks
from discord.ext.commands import Context

from PyDrocsid.cog import Cog
from PyDrocsid.config import Config
from PyDrocsid.github_api import GitHubUser, get_users, get_repo_description
from PyDrocsid.help import send_help
from PyDrocsid.translations import translations
from PyDrocsid.util import send_long_embed
from cogs.contributor import Contributor
from cogs.settings.cog import get_prefix
from colours import Colours
from .permissions import Permission


class BotInfoCog(Cog, name="Bot Information"):
    CONTRIBUTORS = [Contributor.Defelo, Contributor.ce_phox]
    PERMISSIONS = Permission

    def __init__(self, *, info_icon: Optional[str] = None):
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
        await self.bot.change_presence(
            status=Status.online, activity=Game(name=translations.profile_status[self.current_status])
        )
        self.current_status = (self.current_status + 1) % len(translations.profile_status)

    async def build_info_embed(self, authorized: bool) -> Embed:
        embed = Embed(title=Config.NAME, colour=Colours.info, description=translations.bot_description)

        if self.info_icon:
            embed.set_thumbnail(url=self.info_icon)

        prefix: str = await get_prefix()

        features = translations.features
        if authorized:
            features += translations.admin_features

        embed.add_field(
            name=translations.features_title,
            value="\n".join(f":small_orange_diamond: {feature}" for feature in features),
            inline=False,
        )

        if not self.github_users:
            await self.load_github_users()

        embed.add_field(name=translations.author_title, value=self.format_contributor(Config.AUTHOR), inline=True)

        embed.add_field(
            name=translations.contributors_title,
            value=" ".join(
                f
                for c, _ in Config.CONTRIBUTORS.most_common()
                if (f := self.format_contributor(c)) and c != Config.AUTHOR
            ),
            inline=True,
        )

        embed.add_field(name=translations.version_title, value=Config.VERSION, inline=True)
        embed.add_field(name=translations.github_title, value=Config.REPO_LINK, inline=False)
        embed.add_field(name=translations.prefix_title, value=f"`{prefix}` or {self.bot.user.mention}", inline=True)
        embed.add_field(name=translations.help_command_title, value=f"`{prefix}help`", inline=True)
        embed.add_field(
            name=translations.bugs_features_title,
            value=translations.bugs_features,
            inline=False,
        )
        return embed

    @commands.command(aliases=["gh"])
    async def github(self, ctx: Context):
        """
        return the github link
        """

        if not self.repo_description:
            self.repo_description = await get_repo_description(*Config.REPO.split("/"))

        embed = Embed(
            title=Config.REPO,
            description=self.repo_description,
            colour=Colours.github,
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

        embed = Embed(title=f"{Config.NAME} v{Config.VERSION}", colour=Colours.version)
        await ctx.send(embed=embed)

    @commands.command(aliases=["infos", "about"])
    async def info(self, ctx: Context):
        """
        show information about the bot
        """

        await send_long_embed(ctx, await self.build_info_embed(False))

    @commands.command(aliases=["admininfos"])
    @Permission.admininfo.check
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
                title=translations.contributors_title,
                colour=Colours.info,
                description="\n".join(
                    f":small_orange_diamond: {f}"
                    for c, cnt in [(Config.AUTHOR, 0), *Config.CONTRIBUTORS.most_common()]
                    if (f := self.format_contributor(c, long=True)) and (c != Config.AUTHOR or not cnt)
                ),
            ),
        )

    async def on_bot_ping(self, message: Message):
        await message.channel.send(embed=await self.build_info_embed(False))

    @commands.command()
    async def help(self, ctx: Context, *, cog_or_command: Optional[str]):
        """
        Shows this Message
        """

        await send_help(ctx, cog_or_command)
