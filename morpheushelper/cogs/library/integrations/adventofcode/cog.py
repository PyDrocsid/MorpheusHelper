import os
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Union

import requests
from discord import Embed, Member, User, Role, Guild
from discord.ext import commands, tasks
from discord.ext.commands import Context, UserInputError, CommandError, guild_only

from PyDrocsid.cog import Cog
from PyDrocsid.database import db_thread, db
from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.settings import Settings
from PyDrocsid.translations import t
from PyDrocsid.util import send_long_embed
from .colors import Colors
from .models import AOCLink
from .permissions import AdventOfCodePermission
from cogs.library.contributor import Contributor
from cogs.library.pubsub import send_to_changelog

tg = t.g
t = t.adventofcode

BASE_URL = "https://adventofcode.com/"


class AOCConfig:
    YEAR = None
    SESSION = None
    USER_ID = None
    INVITE_CODE = None
    LEADERBOARD_URL = None
    REFRESH_INTERVAL = None

    last_update = 0
    _leaderboard = None

    update_hook = None

    @classmethod
    def load(cls) -> bool:
        cls.SESSION = os.getenv("AOC_SESSION")
        if not cls.SESSION:
            return False

        response = requests.get(BASE_URL + "leaderboard/private", cookies={"session": cls.SESSION})
        if not response.ok or not response.url.endswith("private"):
            return False

        cls.YEAR = int(response.url.split("/")[3])
        cls.INVITE_CODE, cls.USER_ID = re.search(r"<code>((\d+)-[\da-f]+)</code>", response.text).groups()
        cls.LEADERBOARD_URL = BASE_URL + f"{cls.YEAR}/leaderboard/private/view/{cls.USER_ID}.json"

        cls.REFRESH_INTERVAL = int(os.getenv("AOC_REFRESH_INTERVAL", "900"))

        return True

    @classmethod
    def _request(cls, url):
        return requests.get(url, cookies={"session": cls.SESSION})

    @classmethod
    async def get_leaderboard(cls, disable_hook: bool = False) -> dict:
        ts = time.time()
        if ts - cls.last_update >= cls.REFRESH_INTERVAL:
            cls.last_update = ts
            cls._leaderboard = cls._request(cls.LEADERBOARD_URL).json()

            members = cls._leaderboard["members"] = dict(
                sorted(
                    cls._leaderboard["members"].items(),
                    reverse=True,
                    key=lambda m: (m[1]["local_score"], m[1]["stars"], -int(m[1]["last_star_ts"])),
                ),
            )
            for i, member in enumerate(members.values()):
                member["rank"] = i + 1

            if cls.update_hook and not disable_hook:
                await cls.update_hook(cls._leaderboard)

        return cls._leaderboard

    @classmethod
    async def get_member(cls, name: str) -> Optional[dict]:
        members = (await cls.get_leaderboard())["members"]

        if name in members:
            return members[name]

        for member in members.values():
            if member["name"] is not None and member["name"].lower().strip() == name.lower().strip():
                return member

        return None

    @classmethod
    async def find_member(cls, member: Union[User, Member]) -> tuple[Optional[dict], Optional[AOCLink]]:
        if link := await db_thread(db.get, AOCLink, member.id):
            return await cls.get_member(link.aoc_id), link

        if isinstance(member, Member) and member.nick:
            if result := await cls.get_member(member.nick):
                return result, None
        return await cls.get_member(member.name), None


def make_leaderboard(last_update: float, members: list[tuple[int, int, int, Optional[str]]]) -> str:
    rank_len, score_len, stars_len, _ = [max(len(str(e)) for e in column) for column in zip(*map(list, members))]
    score_len = max(score_len, 3)
    stars_len = max(stars_len, 5)

    out = [f" {' ' * rank_len}  {'SCORE':>{score_len + 2}}  STARS  NAME"]
    for rank, score, stars, name in members:
        out.append(f"#{rank:0{rank_len}}  [{score:{score_len}}]  {stars:{stars_len}}  {name[:50]}")
    out += ["", datetime.utcfromtimestamp(last_update).strftime("/* Last Update: %d.%m.%Y %H:%M:%S UTC */")]

    return "```css\n" + "\n".join(out) + "\n```"


def make_member_stats(member: dict) -> tuple[int, list[str]]:
    stars = ["Day  Part #1          Part #2"]
    completed = 0
    part_avg = [[], []]
    for i in range(25):
        day = member["completion_day_level"].get(str(i + 1))
        if not day:
            continue

        line = f" {i + 1:02}"
        for part, avg in zip("12", part_avg):
            if part not in day:
                break

            completed += 1
            release_ts = datetime(AOCConfig.YEAR, 12, i + 1, 5, 0, 0, tzinfo=timezone.utc).timestamp()
            delta = timedelta(seconds=int(day[part]["get_star_ts"]) - release_ts)
            avg.append(delta.total_seconds())
            d, h, m, s = delta.days, delta.seconds // 3600, delta.seconds // 60 % 60, delta.seconds % 60
            line += f"  {d:2}d {h:2}h {m:2}m {s:2}s"
        stars.append(line)

    #    if completed:
    #        stars.append("-" * 37)
    #        line = "Avg"
    #        for part in part_avg:
    #            if not part:
    #                break
    #
    #            delta = timedelta(seconds=sum(part) / len(part))
    #            d, h, m, s = delta.days, delta.seconds // 3600, delta.seconds // 60 % 60, delta.seconds % 60
    #            line += f"  {d:2}d {h:2}h {m:2}m {s:2}s"
    #        stars.append(line)

    return completed, stars


def escape_aoc_name(name: Optional[str]) -> str:
    return "".join(c for c in name if c.isalnum() or c in " _-") if name else ""


def get_github_repo(url: str) -> Optional[str]:
    if not (match := re.match(r"^(https?://)?github.com/([a-zA-Z0-9.\-_]+)/([a-zA-Z0-9.\-_]+)(/.*)?$", url)):
        return None
    _, user, repo, path = match.groups()
    if not (response := requests.get(f"https://api.github.com/repos/{user}/{repo}")).ok:
        return None
    url = response.json()["html_url"] + (path or "")
    if not requests.head(url).ok:
        return None
    return url


def parse_github_url(url: str) -> tuple[str, str]:
    user, repo = re.match(r"^https://github.com/([^/]+)/([^/]+).*", url).groups()
    return user, repo


class AdventOfCodeCog(Cog, name="Advent of Code Integration"):
    CONTRIBUTORS = [Contributor.Defelo]
    PERMISSIONS = AdventOfCodePermission

    def __init__(self):
        super().__init__()

        AOCConfig.update_hook = self.update_roles

    @staticmethod
    def prepare() -> bool:
        return AOCConfig.load()

    async def on_ready(self):
        self.aoc_loop.cancel()
        try:
            self.aoc_loop.start()
        except RuntimeError:
            self.aoc_loop.restart()

    @tasks.loop(minutes=1)
    async def aoc_loop(self):
        await AOCConfig.get_leaderboard()

    async def update_roles(self, leaderboard: dict):
        guild: Guild = self.bot.guilds[0]
        role: Optional[Role] = guild.get_role(await Settings.get(int, "aoc_role", -1))
        if not role:
            return
        rank: int = await Settings.get(int, "aoc_rank", 10)

        new_members: set[Member] = set()
        for member in list(leaderboard["members"].values())[:rank]:
            if link := await db_thread(db.first, AOCLink, aoc_id=member["id"]):
                if member := guild.get_member(link.discord_id):
                    new_members.add(member)
        old_members: set[Member] = set(role.members)

        for member in old_members - new_members:
            await member.remove_roles(role)
        for member in new_members - old_members:
            await member.add_roles(role)

    async def get_from_aoc(self, aoc_name: str) -> tuple[Optional[dict], Optional[User], Optional[AOCLink]]:
        aoc_member = await AOCConfig.get_member(aoc_name)
        if not aoc_member:
            return None, None, None

        if link := await db_thread(db.first, AOCLink, aoc_id=aoc_member["id"]):
            if member := self.bot.get_user(link.discord_id):
                return aoc_member, member, link
        return aoc_member, None, None

    async def get_from_discord(
        self,
        member: User,
        ignore_link: bool,
    ) -> tuple[Optional[dict], Optional[User], Optional[AOCLink]]:
        aoc_member, link = await AOCConfig.find_member(member)
        if not aoc_member:
            return None, None, None
        if link:
            return aoc_member, member, link

        if link := await db_thread(db.first, AOCLink, aoc_id=aoc_member["id"]):
            if not ignore_link:
                return None, None, None

            return aoc_member, self.bot.get_user(link.discord_id), link

        return aoc_member, member, None

    @commands.group()
    async def aoc(self, ctx: Context):
        """
        Advent of Code Integration
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @aoc.command(name="join")
    async def aoc_join(self, ctx: Context):
        """
        request instructions on how to join the private leaderboard
        """

        await ctx.send(
            embed=Embed(
                title=t.join_title,
                colour=Colors.AdventOfCode,
                description=t.join_instructions(AOCConfig.INVITE_CODE),
            ),
        )

    @aoc.command(name="leaderboard", aliases=["lb", "ranking"])
    async def aoc_leaderboard(self, ctx: Context):
        """
        show the current state of the private leaderboard
        """

        leaderboard = await AOCConfig.get_leaderboard()

        out = t.leaderboard_header(AOCConfig.YEAR) + "\n"
        out += make_leaderboard(
            AOCConfig.last_update,
            [
                (m["rank"], m["local_score"], m["stars"], escape_aoc_name(m["name"]) or f"[anonymous user #{m['id']}]")
                for i, m in enumerate(list(leaderboard["members"].values())[:20])
            ],
        )

        await ctx.send(out)

    @aoc.command(name="user")
    async def aoc_user(self, ctx: Context, *, user: Optional[Union[Member, str]]):
        """
        show stats of a specific user
        """

        if isinstance(user, str):
            aoc_member, member, link = await self.get_from_aoc(user)
        else:
            aoc_member, member, link = await self.get_from_discord(user or ctx.author, user is not None)

        if not aoc_member:
            raise CommandError(tg.user_not_found)

        if aoc_member["name"]:
            name = f"{aoc_member['name']} (#{aoc_member['id']})"
        else:
            name = f"(anonymous user #{aoc_member['id']})"

        trophy = "trophy"
        rank = str(aoc_member["rank"]) + {1: "st", 2: "nd", 3: "rd"}.get(
            aoc_member["rank"] % 10 * (aoc_member["rank"] // 10 % 10 != 1),
            "th",
        )
        if aoc_member["rank"] <= await Settings.get(int, "aoc_rank", 10):
            rank = f"**{rank}**"
            trophy = "medal"
        if aoc_member["rank"] <= 3:
            trophy = ["first", "second", "third"][aoc_member["rank"] - 1] + "_place"

        completed, stars = make_member_stats(aoc_member)
        unlocked = (datetime.now(tz=timezone.utc) - datetime(AOCConfig.YEAR, 12, 1, 5, 0, 0, tzinfo=timezone.utc)).days
        unlocked = max(0, min(25, unlocked + 1)) * 2
        if not unlocked:
            progress = "N/A"
        else:
            full = "**" * (unlocked == completed)
            progress = f"{completed}/{unlocked} ({full}{completed / unlocked * 100:.1f}%{full})"

        embed = Embed(title=f"Advent of Code {AOCConfig.YEAR}", colour=Colors.AdventOfCode)
        icon_url = member.avatar_url if member else "https://adventofcode.com/favicon.png"
        embed.set_author(name=name, icon_url=icon_url)

        linked = f"<@{member.id}>" + " (unverified)" * (not link) if member else "Not Linked"
        embed.add_field(name=":link: Member", value=linked, inline=True)
        embed.add_field(name=":chart_with_upwards_trend: Progress", value=progress, inline=True)

        if link and link.solutions:
            user, repo = parse_github_url(link.solutions)
            embed.add_field(name=":package: Solutions", value=f"[[{user}/{repo}]]({link.solutions})", inline=True)

        embed.add_field(name=":star: Stars", value=aoc_member["stars"], inline=True)
        embed.add_field(name=f":{trophy}: Local Score", value=f"{aoc_member['local_score']} ({rank})", inline=True)
        embed.add_field(name=":globe_with_meridians: Global Score", value=aoc_member["global_score"], inline=True)

        embed.add_field(name="** **", value="```hs\n" + "\n".join(stars) + "\n```", inline=False)
        embed.set_footer(text="Last Update:")
        embed.timestamp = datetime.utcfromtimestamp(AOCConfig.last_update)

        await ctx.send(embed=embed)

    @aoc.command(name="clear_cache", aliases=["clear", "cc"])
    @AdventOfCodePermission.clear.check
    async def aoc_clear_cache(self, ctx: Context):
        """
        clear the leaderboard cache to force a refresh on the next request
        """

        AOCConfig.last_update = 0
        await ctx.message.add_reaction(name_to_emoji["white_check_mark"])

    @aoc.group(name="link", aliases=["l"])
    @AdventOfCodePermission.link.check
    async def aoc_link(self, ctx: Context):
        """
        manage links between discord members and aoc users on the private leaderboard
        """

        if len(ctx.message.content.lstrip(ctx.prefix).split()) > 2:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        embed = Embed(title=t.links, colour=Colors.AdventOfCode)
        leaderboard = await AOCConfig.get_leaderboard()
        out = []
        for link in await db_thread(db.all, AOCLink):  # type: AOCLink
            if link.aoc_id not in leaderboard["members"]:
                continue
            if not (user := self.bot.get_user(link.discord_id)):
                continue

            member = leaderboard["members"][link.aoc_id]
            if member["name"]:
                name = f"{member['name']} (#{member['id']})"
            else:
                name = f"(anonymous user #{member['id']})"

            out.append(f"{name} = <@{link.discord_id}> (`@{user}`)")

        if not out:
            embed.description = t.no_links
            embed.colour = Colors.error
        else:
            embed.description = "\n".join(out)
        await send_long_embed(ctx, embed)

    @aoc_link.command(name="add", aliases=["a", "+"])
    async def aoc_link_add(self, ctx: Context, member: Member, *, aoc_user: str):
        """
        add a new link
        """

        aoc_member = await AOCConfig.get_member(aoc_user)
        if not aoc_member:
            raise CommandError(tg.user_not_found)

        if await db_thread(db.get, AOCLink, member.id) or await db_thread(db.first, AOCLink, aoc_id=aoc_member["id"]):
            raise CommandError(t.link_already_exists)

        await db_thread(AOCLink.create, member.id, aoc_member["id"])
        await ctx.send(t.link_created)

    @aoc_link.command(name="remove", aliases=["r", "del", "d", "-"])
    async def aoc_link_remove(self, ctx: Context, *, member: Union[Member, str]):
        """
        remove a link
        """

        if isinstance(member, Member):
            link = await db_thread(db.get, AOCLink, member.id)
        else:
            aoc_member = await AOCConfig.get_member(member)
            link = aoc_member and await db_thread(db.first, AOCLink, aoc_id=aoc_member["id"])

        if not link:
            raise CommandError(t.link_not_found)

        await db_thread(db.delete, link)
        await ctx.send(t.link_removed)

    @aoc.group(name="role", aliases=["r"])
    @AdventOfCodePermission.role.check
    @guild_only()
    async def aoc_role(self, ctx: Context):
        """
        manage aoc role
        """

        if len(ctx.message.content.lstrip(ctx.prefix).split()) > 2:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        embed = Embed(title=t.aoc_role)

        role: Optional[Role] = ctx.guild.get_role(await Settings.get(int, "aoc_role", -1))
        rank: int = await Settings.get(int, "aoc_rank", 10)

        if not role:
            embed.colour = Colors.error
            embed.add_field(name=tg.role, value=tg.disabled)
        else:
            embed.colour = role.colour
            embed.add_field(name=tg.role, value=role.mention)
        embed.add_field(name=t.min_rank, value=str(rank))

        if role:
            embed.add_field(name=tg.members, value="\n".join(m.mention for m in role.members), inline=False)

        await send_long_embed(ctx, embed)

    @aoc_role.command(name="set", aliases=["s", "="])
    async def aoc_role_set(self, ctx: Context, role: Role):
        """
        configure aoc role
        """

        old_role: Optional[Role] = ctx.guild.get_role(await Settings.get(int, "aoc_role", -1))

        await Settings.set(int, "aoc_role", role.id)

        if old_role:
            for member in old_role.members:
                await member.remove_roles(old_role)
        await self.update_roles(await AOCConfig.get_leaderboard(disable_hook=True))

        await ctx.send(t.role_set)
        await send_to_changelog(ctx.guild, t.log_role_set(role.name, role.id))

    @aoc_role.command(name="disable", aliases=["d", "off"])
    async def aoc_role_disable(self, ctx: Context):
        """
        disable aoc role
        """

        role: Optional[Role] = ctx.guild.get_role(await Settings.get(int, "aoc_role", -1))

        await Settings.set(int, "aoc_role", -1)

        if role:
            for member in role.members:
                await member.remove_roles(role)

        await ctx.send(t.role_disabled)
        await send_to_changelog(ctx.guild, t.role_disabled)

    @aoc_role.command(name="rank", aliases=["r"])
    async def aoc_role_rank(self, ctx: Context, rank: int):
        """
        set the minimum rank users need to get the role
        """

        if not 1 <= rank <= 200:
            raise CommandError(t.invalid_rank)

        await Settings.set(int, "aoc_rank", rank)
        await self.update_roles(await AOCConfig.get_leaderboard(disable_hook=True))

        await ctx.send(t.rank_set)
        await send_to_changelog(ctx.guild, t.log_rank_set(rank))

    @aoc.command(name="publish")
    async def aoc_publish(self, ctx: Context, url: str):
        """
        publish a github repository containing solutions for the current advent of code round
        """

        if not await db_thread(db.get, AOCLink, ctx.author.id):
            raise CommandError(t.not_verified)

        url: Optional[str] = get_github_repo(url)
        if not url or len(url) > 128:
            raise CommandError(t.invalid_url)

        await db_thread(AOCLink.publish, ctx.author.id, url)
        await ctx.send(t.published)

    @aoc.command(name="unpublish")
    async def aoc_unpublish(self, ctx: Context):
        """
        unpublish a previously published repository
        """

        link: Optional[AOCLink] = await db_thread(db.get, AOCLink, ctx.author.id)
        if not link:
            raise CommandError(t.not_verified)
        if not link.solutions:
            raise CommandError(t.not_published)

        await db_thread(AOCLink.unpublish, ctx.author.id)
        await ctx.send(t.unpublished)

    @aoc.command(name="solutions", aliases=["repos"])
    async def aoc_solutions(self, ctx: Context):
        """
        list published solution repositories
        """

        embed = Embed(title=t.solutions, colour=Colors.AdventOfCode)
        members = (await AOCConfig.get_leaderboard())["members"]
        out = []
        for link in await db_thread(db.all, AOCLink):  # type: AOCLink
            if not link.solutions or link.aoc_id not in members:
                continue

            user, repo = parse_github_url(link.solutions)
            out.append(f"<@{link.discord_id}> ({members[link.aoc_id]['name']}): [[{user}/{repo}]]({link.solutions})")

        if not out:
            embed.description = t.no_solutions
            embed.colour = Colors.error
        else:
            embed.description = "\n".join(out)

        await send_long_embed(ctx, embed)
