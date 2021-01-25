import requests
from aiohttp import ClientSession


class Emekc:
    URL = "https://emkc.org/api/v1/piston/execute"

    @staticmethod
    async def run_code(data: dict):
        async with ClientSession() as session:
            async with session.post(Emekc.URL, data=data) as response:
                return await response.text()
