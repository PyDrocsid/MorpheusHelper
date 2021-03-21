from aiohttp import ClientSession


class EmkcAPIException(BaseException):
    @property
    def error(self) -> str:
        return self.args[0]["message"]


class Emkc:
    URL = "https://emkc.org/api/v1/piston/execute"

    @staticmethod
    async def run_code(language: str, source: str) -> dict:
        async with ClientSession() as session, session.post(
            Emkc.URL,
            json={"language": language, "source": source},
        ) as response:
            if response.status != 200:
                raise EmkcAPIException(await response.json())

            return await response.json()
