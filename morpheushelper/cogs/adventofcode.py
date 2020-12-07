import os
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Union

import requests
from PyDrocsid.database import db_thread, db
from PyDrocsid.emojis import name_to_emoji
from PyDrocsid.translations import translations
from PyDrocsid.util import send_long_embed
from discord import Embed, Member, User
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, UserInputError, CommandError

from models.aoc_link import AOCLink
from permissions import Permission

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

        cls.REFRESH_INTERVAL = int(os.getenv("AOC_REFRESH_INTERVAL", 900))

        return True

    @classmethod
    def _request(cls, url):
        return requests.get(url, cookies={"session": cls.SESSION})

    @classmethod
    def get_leaderboard(cls) -> dict:
        ts = time.time()
        if ts - cls.last_update >= cls.REFRESH_INTERVAL:
            cls.last_update = ts
            cls._leaderboard = cls._request(cls.LEADERBOARD_URL).json()

            members = cls._leaderboard["members"] = dict(
                sorted(
                    cls._leaderboard["members"].items(),
                    reverse=True,
                    key=lambda m: (m[1]["local_score"], m[1]["stars"], -int(m[1]["last_star_ts"])),
                )
            )
            for i, member in enumerate(members.values()):
                member["rank"] = i + 1

        return cls._leaderboard

    @classmethod
    def get_member(cls, name: str) -> Optional[dict]:
        members = cls.get_leaderboard()["members"]

        if name in members:
            return members[name]

        for member in members.values():
            if member["name"] is not None and member["name"].lower().strip() == name.lower().strip():
                return member

        return None

    @classmethod
    async def find_member(cls, member: Union[User, Member]) -> tuple[Optional[dict], bool]:
        if link := await db_thread(db.get, AOCLink, member.id):
            return cls.get_member(link.aoc_id), True

        if isinstance(member, Member) and member.nick:
            if result := cls.get_member(member.nick):
                return result, False
        return cls.get_member(member.name), False


def make_leaderboard(last_update: float, members: list[tuple[int, int, int, Optional[str]]]) -> str:
    rank_len, score_len, stars_len, name_len = [max(len(str(e)) for e in column) for column in zip(*map(list, members))]
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
            delta = timedelta(
                seconds=int(day[part]["get_star_ts"])
                - datetime(AOCConfig.YEAR, 12, i + 1, 5, 0, 0, tzinfo=timezone.utc).timestamp()
            )
            avg.append(delta.total_seconds())
            d, h, m, s = delta.days, delta.seconds // 3600, delta.seconds // 60 % 60, delta.seconds % 60
            line += f"  {d:2}d {h:2}h {m:2}m {s:2}s"
        stars.append(line)

    if completed:
        stars.append("-" * 37)
        line = "Avg"
        for part in part_avg:
            if not part:
                break

            delta = timedelta(seconds=sum(part) / len(part))
            d, h, m, s = delta.days, delta.seconds // 3600, delta.seconds // 60 % 60, delta.seconds % 60
            line += f"  {d:2}d {h:2}h {m:2}m {s:2}s"
        stars.append(line)

    return completed, stars


def escape_aoc_name(name: Optional[str]) -> str:
    return "".join(c for c in name if c.isalnum() or c in " _-") if name else ""


class AdventOfCodeCog(Cog, name="Advent of Code Integration"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def get_from_aoc(self, aoc_name: str) -> tuple[Optional[dict], Optional[User], bool]:
        aoc_member = AOCConfig.get_member(aoc_name)
        if not aoc_member:
            return None, None, False

        if link := await db_thread(db.first, AOCLink, aoc_id=aoc_member["id"]):
            if member := self.bot.get_user(link.discord_id):
                return aoc_member, member, True
        return aoc_member, None, False

    async def get_from_discord(self, member: User, ignore_link: bool) -> tuple[Optional[dict], Optional[User], bool]:
        aoc_member, verified = await AOCConfig.find_member(member)
        if not aoc_member:
            return None, None, False
        if verified:
            return aoc_member, member, verified

        if link := await db_thread(db.first, AOCLink, aoc_id=aoc_member["id"]):
            if not ignore_link:
                return None, None, False

            return aoc_member, self.bot.get_user(link.discord_id), True

        return aoc_member, member, verified

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

        await ctx.send(translations.f_aoc_join_instructions(AOCConfig.INVITE_CODE))

    @aoc.command(name="leaderboard", aliases=["lb", "ranking"])
    async def aoc_leaderboard(self, ctx: Context):
        """
        show the current state of the private leaderboard
        """

        leaderboard = AOCConfig.get_leaderboard()

        out = translations.f_aoc_leaderboard_header(AOCConfig.YEAR) + "\n"
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
            aoc_member, member, verified = await self.get_from_aoc(user)
        else:
            aoc_member, member, verified = await self.get_from_discord(user or ctx.author, user is not None)

        if not aoc_member:
            raise CommandError(translations.user_not_found)

        if aoc_member["name"]:
            name = f"{aoc_member['name']} (#{aoc_member['id']})"
        else:
            name = f"(anonymous user #{aoc_member['id']})"

        trophy = "trophy"
        rank = str(aoc_member["rank"]) + {1: "st", 2: "nd", 3: "rd"}.get(
            aoc_member["rank"] % 10 * (aoc_member["rank"] // 10 % 10 != 1), "th"
        )
        if aoc_member["rank"] <= 10:
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
            progress = f"{completed}/{unlocked} ({full}{completed/unlocked*100:.1f}%{full})"

        embed = Embed(title=f"Advent of Code {AOCConfig.YEAR}", colour=0x0F0F23)
        icon_url = member.avatar_url if member else "https://adventofcode.com/favicon.png"
        embed.set_author(name=name, icon_url=icon_url)

        linked = f"<@{member.id}>" + " (unverified)" * (not verified) if member else "Not Linked"
        embed.add_field(name=":link: Member", value=linked, inline=True)
        embed.add_field(name=":chart_with_upwards_trend: Progress", value=progress, inline=True)

        embed.add_field(name=":star: Stars", value=aoc_member["stars"], inline=True)
        embed.add_field(name=f":{trophy}: Local Score", value=f"{aoc_member['local_score']} ({rank})", inline=True)
        embed.add_field(name=":globe_with_meridians: Global Score", value=aoc_member["global_score"], inline=True)

        embed.add_field(name="** **", value="```hs\n" + "\n".join(stars) + "\n```", inline=False)
        embed.set_footer(text="Last Update:")
        embed.timestamp = datetime.utcfromtimestamp(AOCConfig.last_update)

        await ctx.send(embed=embed)

    @aoc.command(name="clear_cache", aliases=["clear", "cc"])
    @Permission.aoc_clear.check
    async def aoc_clear_cache(self, ctx: Context):
        """
        clear the leaderboard cache to force a refresh on the next request
        """

        AOCConfig.last_update = 0
        await ctx.message.add_reaction(name_to_emoji["white_check_mark"])

    @aoc.group(name="link", aliases=["l"])
    @Permission.aoc_link.check
    async def aoc_link(self, ctx: Context):
        """
        manage links between discord members and aoc users on the private leaderboard
        """

        if len(ctx.message.content.lstrip(ctx.prefix).split()) > 2:
            if ctx.invoked_subcommand is None:
                raise UserInputError
            return

        embed = Embed(title=translations.aoc_links, colour=0x0F0F23)
        leaderboard = AOCConfig.get_leaderboard()
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
            embed.description = translations.aoc_no_links
            embed.colour = 0xCF0606
        else:
            embed.description = "\n".join(out)
        await send_long_embed(ctx, embed)

    @aoc_link.command(name="add", aliases=["a", "+"])
    async def aoc_link_add(self, ctx: Context, member: Member, *, aoc_user: str):
        """
        add a new link
        """

        aoc_member = AOCConfig.get_member(aoc_user)
        if not aoc_member:
            raise CommandError(translations.user_not_found)

        if await db_thread(db.get, AOCLink, member.id) or await db_thread(db.first, AOCLink, aoc_id=aoc_member["id"]):
            raise CommandError(translations.aoc_link_already_exists)

        await db_thread(AOCLink.create, member.id, aoc_member["id"])
        await ctx.send(translations.aoc_link_created)

    @aoc_link.command(name="remove", aliases=["r", "del", "d", "-"])
    async def aoc_link_remove(self, ctx: Context, *, member: Union[Member, str]):
        """
        remove a link
        """

        if isinstance(member, Member):
            link = await db_thread(db.get, AOCLink, member.id)
        else:
            aoc_member = AOCConfig.get_member(member)
            link = aoc_member and await db_thread(db.first, AOCLink, aoc_id=aoc_member["id"])

        if not link:
            raise CommandError(translations.aoc_link_not_found)

        await db_thread(db.delete, link)
        await ctx.send(translations.aoc_link_removed)
