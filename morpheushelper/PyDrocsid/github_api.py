from collections import namedtuple
from typing import Optional

from aiohttp import ClientSession

from PyDrocsid.environment import GITHUB_TOKEN

GitHubUser = namedtuple("GitHubUser", ["id", "name", "profile"])

API_URL = "https://api.github.com/graphql"


async def graphql(query: str, **kwargs) -> Optional[dict]:
    headers = {"Authorization": f"bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    async with ClientSession() as session:
        async with session.post(API_URL, headers=headers, json={"query": query, "variables": kwargs}) as response:
            if response.status != 200:
                return None

            return (await response.json())["data"]


async def get_users(ids: list[str]) -> Optional[dict[str, GitHubUser]]:
    result: Optional[dict] = await graphql("query($ids:[ID!]!){nodes(ids:$ids){...on User{id,login,url}}}", ids=ids)
    if not result:
        return None

    return {user["id"]: GitHubUser(user["id"], user["login"], user["url"]) for user in result["nodes"]}


async def get_repo_description(owner: str, name: str) -> Optional[str]:
    result: Optional[dict] = await graphql(
        "query($owner:String!,$name:String!){repository(owner:$owner,name:$name){description}}",
        owner=owner,
        name=name,
    )
    if not result:
        return None

    return result["repository"]["description"]
