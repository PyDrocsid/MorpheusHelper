from aiohttp import ClientSession


class CoinMarketCap:
    URL = "https://pro-api.coinmarketcap.com"

    def __init__(self, token):
        self.token = token

    async def get_cryptocurrencies_list(self):
        parameters = {
            'start': '1',
            'limit': '3',
            'convert': 'USD'
        }

        headers = {
            "X-CMC_PRO_API_KEY": self.token,
            'Accepts': 'application/json'
        }
        async with ClientSession(headers=headers) as session:
            async with session.get(f"{self.URL}/v1/cryptocurrency/listings/latest", params=parameters) as response:
                return await response.text()
