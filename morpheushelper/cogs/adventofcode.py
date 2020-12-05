import os
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Union

import requests
from PyDrocsid.translations import translations
from discord import Embed, Member, User
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, UserInputError, CommandError

BASE_URL = "https://adventofcode.com/"


class AOCConfig:
    YEAR = None
    SESSION = None
    USER_ID = None
    INVITE_CODE = None
    LEADERBOARD_URL = None
    REFRESH_INTERVAL = None

    _last_leaderboard_ts = 0
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
    def get_leaderboard(cls) -> tuple[float, dict]:
        ts = time.time()
        if ts - cls._last_leaderboard_ts >= cls.REFRESH_INTERVAL:
            cls._last_leaderboard_ts = ts
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

        return cls._last_leaderboard_ts, cls._leaderboard

    @classmethod
    def get_member(cls, name: str) -> tuple[float, Optional[dict]]:
        last_update, leaderboard = cls.get_leaderboard()
        members = leaderboard["members"]

        if name in members:
            return last_update, members[name]

        for member in members.values():
            if member["name"] is not None and member["name"].lower().strip() == name.lower().strip():
                return last_update, member

        return last_update, None

    @classmethod
    def find_member(cls, member: Union[User, Member]) -> tuple[float, Optional[dict]]:
        if isinstance(member, Member) and member.nick:
            if (result := cls.get_member(member.nick))[1]:
                return result
        return cls.get_member(member.name)


def make_leaderboard(last_update: float, members: list[tuple[int, int, int, Optional[str]]]) -> str:
    rank_len, score_len, stars_len, name_len = [max(len(str(e)) for e in column) for column in zip(*map(list, members))]
    score_len = max(score_len, 3)
    stars_len = max(stars_len, 5)

    out = [f" {' ' * rank_len}  {'SCORE':>{score_len + 2}}  STARS  NAME"]
    for rank, score, stars, name in members:
        out.append(f"#{rank:0{rank_len}}  [{score:{score_len}}]  {stars:{stars_len}}  {name[:50]}")
    out += ["", datetime.utcfromtimestamp(last_update).strftime("/* Last Update: %d.%m.%Y %H:%M:%S UTC */")]

    return "```css\n" + "\n".join(out) + "\n```"


def escape_aoc_name(name: Optional[str]) -> str:
    return "".join(c for c in name if c.isalnum() or c in " _-") if name else ""


class AdventOfCodeCog(Cog, name="Advent of Code Integration"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group()
    async def aoc(self, ctx: Context):
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

        last_update, leaderboard = AOCConfig.get_leaderboard()

        out = translations.f_aoc_leaderboard_header(AOCConfig.YEAR) + "\n"
        out += make_leaderboard(
            last_update,
            [
                (m["rank"], m["local_score"], m["stars"], escape_aoc_name(m["name"]) or f"[anonymous user #{m['id']}]")
                for i, m in enumerate(list(leaderboard["members"].values())[:20])
            ],
        )

        await ctx.send(out)

    @aoc.command(name="user")
    async def aoc_user(self, ctx: Context, *, user: Optional[str]):
        """
        show stats of a specific user
        """

        last_update, member = AOCConfig.get_member(user) if user else AOCConfig.find_member(ctx.author)
        if not member:
            raise CommandError(translations.user_not_found)

        if member["name"]:
            name = f"{member['name']} (#{member['id']})"
        else:
            name = f"(anonymous user #{member['id']})"

        rank = str(member["rank"]) + {1: "st", 2: "nd", 3: "rd"}.get(
            member["rank"] % 10 * (member["rank"] // 10 % 10 != 1), "th"
        )
        if member["rank"] <= 10:
            rank = f"**{rank}**"

        embed = Embed(title=f"Advent of Code {AOCConfig.YEAR}", colour=0x0F0F23)
        embed.set_author(name=name, icon_url="https://adventofcode.com/favicon.png")
        embed.add_field(name=":star: Stars", value=member["stars"], inline=True)
        embed.add_field(name=":trophy: Local Score", value=f"{member['local_score']} ({rank})", inline=True)
        embed.add_field(name=":globe_with_meridians: Global Score", value=member["global_score"], inline=True)

        stars = ["Day  Part #1          Part #2"]
        for i in range(25):
            day = member["completion_day_level"].get(str(i + 1))
            if not day:
                continue

            line = f" {i + 1:02}"
            for part in "12":
                if part not in day:
                    break

                delta = timedelta(
                    seconds=int(day[part]["get_star_ts"])
                    - datetime(AOCConfig.YEAR, 12, i + 1, 5, 0, 0, tzinfo=timezone.utc).timestamp()
                )
                d, h, m, s = delta.days, delta.seconds // 3600, delta.seconds // 60 % 60, delta.seconds % 60
                line += f"  {d:2}d {h:2}h {m:2}m {s:2}s"
            stars.append(line)

        embed.add_field(name="** **", value="```hs\n" + "\n".join(stars) + "\n```", inline=False)
        embed.set_footer(text="Last Update:")
        embed.timestamp = datetime.utcfromtimestamp(last_update)

        await ctx.send(embed=embed)
