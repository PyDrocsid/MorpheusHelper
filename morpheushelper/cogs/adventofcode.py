import os

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

    @classmethod
    def load(cls) -> bool:
        cls.SESSION = os.getenv('AOC_SESSION')
        if not cls.SESSION:
            return False

        response = requests.get(BASE_URL + "leaderboard/private", cookies={"session": cls.SESSION})
        if not response.ok or not response.url.endswith("private"):
            return False

        cls.YEAR = int(response.url.split("/")[3])
        cls.INVITE_CODE, cls.USER_ID = re.search(r"<code>((\d+)-[\da-f]+)</code>", response.text).groups()
        cls.LEADERBOARD_URL = BASE_URL + f"{cls.YEAR}/leaderboard/private/view/{cls.USER_ID}.json"

        return True


class AdventOfCodeCog(Cog, name="Advent of Code Integration"):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.group()
    async def aoc(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            raise UserInputError

    @aoc.command(name="join")
    async def aoc_join(self, ctx: Context):
        await ctx.send(translations.f_aoc_join_instructions(AOCConfig.INVITE_CODE))
