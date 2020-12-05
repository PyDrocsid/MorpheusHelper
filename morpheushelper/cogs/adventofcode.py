import os
import time
from datetime import datetime
from typing import Optional

import requests
import re

from PyDrocsid.translations import translations
from discord.ext import commands
from discord.ext.commands import Cog, Bot, Context, UserInputError

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
        return cls._last_leaderboard_ts, cls._leaderboard


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
        members = list(leaderboard["members"].values())
        members.sort(reverse=True, key=lambda m: (m["local_score"], m["stars"], -int(m["last_star_ts"])))

        out = translations.f_aoc_leaderboard_header(AOCConfig.YEAR) + "\n"
        out += make_leaderboard(
            last_update,
            [
                (i + 1, m["local_score"], m["stars"], escape_aoc_name(m["name"]) or f"[anonymous user #{m['id']}]")
                for i, m in enumerate(members[:20])
            ],
        )

        await ctx.send(out)
