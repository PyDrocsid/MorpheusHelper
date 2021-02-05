import json

from PyDrocsid.translations import translations
from discord import Embed
from discord.ext import commands
from discord.ext.commands import Context, UserInputError, guild_only, Cog, CommandError
from requests import RequestException

from coinmarketcap import CoinMarketCap
from colours import Colours
import os

coin_market_cap = CoinMarketCap(os.environ["CoinMarketCapToken"])


def get_prices(coins):
    coin_prices = ""
    for coin in coins:
        coin_prices += f"{coin['name']} : {'{:.2f}'.format(coin['quote']['USD']['price'])}\n"
    return coin_prices


class CryptoCurrenciesCog(Cog):
    @commands.group(aliases=["CryptoCurrencies", "cc"])
    @guild_only()
    async def crypto(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            raise UserInputError

    @crypto.command(name="prices")
    async def crypto_currencies_prices(self, ctx: Context):
        try:
            response = await coin_market_cap.get_cryptocurrencies_list()
            if "data" not in response:
                raise CommandError(translations.price_query_error)
            embed = Embed(description=f"```{get_prices(json.loads(response)['data'])}```", colour=Colours.crypto)
            await ctx.send(embed=embed)
        except RequestException:
            raise CommandError(translations.price_query_error)
