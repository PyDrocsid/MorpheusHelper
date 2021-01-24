from PyDrocsid.translations import translations
from PyDrocsid.util import send_long_embed
from discord import Embed
from discord.ext import commands
from discord.ext.commands import Cog, Bot, CommandError
from requests import RequestException

from colours import Colours
from models.emkc_api import Emekc
import json


class RunCodeCog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    @commands.command(name="run")
    async def run(self, ctx, language: str, *, source: str):
        try:
            api_result = json.loads(Emekc.run_code({'language': language, 'source': source.replace("`", "")}))
            if "output" not in api_result:
                raise CommandError(translations.f_error_unsupported_language(language))
            await send_long_embed(ctx, Embed(colour=Colours.green, description=api_result["output"]))
        except RequestException:
            raise CommandError(translations.error_run_code)
