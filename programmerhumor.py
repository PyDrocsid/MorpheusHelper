import datetime
import json

import pytz
import requests

from discord import Embed
from info import VERSION


class ProgrammerHumor:
    LIMIT = 4

    @staticmethod
    def fetch_reddit_posts():
        resp = requests.get(
            "https://www.reddit.com/r/ProgrammerHumor/hot.json",
            headers={f"User-agent": "MorpheusHelper/{VERSION}"},
            params={"limit": str(ProgrammerHumor.LIMIT)},
        )

        if not resp.status_code == requests.codes.ok:
            # fail silently
            return []

        listing = resp.json()["data"]["children"]

        posts = []
        for post in listing:
            # t3 = link
            if not (post["kind"] == "t3" and post["data"]["post_hint"] == "image"):
                continue
            posts.append(
                {
                    "id": post["data"]["id"],
                    "author": post["data"]["author"],
                    "title": post["data"]["title"],
                    "created_utc": post["data"]["created_utc"],
                    "score": post["data"]["score"],
                    "num_comments": post["data"]["num_comments"],
                    "permalink": post["data"]["permalink"],
                    "url": post["data"]["url"],
                }
            )
        return posts

    @staticmethod
    def create_embed(post):
        embed = Embed(
            title=post["title"],
            url=f"https://reddit.com{post['permalink']}",
            description=f"{post['score']} :thumbsup: \u00B7 {post['num_comments']} :speech_balloon:",
            color=0xFF4500,  # Reddit's brand color
        )
        embed.set_author(
            name=f"u/{post['author']}", url=f"https://reddit.com/u/{post['author']}"
        )
        embed.set_image(url=post["url"])
        time = datetime.datetime.fromtimestamp(post["created_utc"], tz=pytz.utc)
        time = time.astimezone(pytz.timezone("Europe/Berlin"))
        time = time.strftime("%d.%m.%y %H:%M")
        embed.set_footer(text=f"r/ProgrammerHumor \u00B7 {time}")
        return embed

    @staticmethod
    def load_already_posted():
        try:
            with open("programmerhumor_already_posted.json") as json_file:
                return json.load(json_file)
        except FileNotFoundError:
            return []

    @staticmethod
    def save_already_posted(already_posted):
        with open("programmerhumor_already_posted.json", "w") as json_file:
            json.dump(already_posted, json_file)

    @staticmethod
    async def run(channel):
        already_posted = ProgrammerHumor.load_already_posted()

        for post in ProgrammerHumor.fetch_reddit_posts():
            if post["id"] in already_posted:
                continue
            else:
                await channel.send(embed=ProgrammerHumor.create_embed(post))
                already_posted.append(post["id"])

        if len(already_posted) > 3 * ProgrammerHumor.LIMIT:
            already_posted = already_posted[
                len(already_posted) - 3 * ProgrammerHumor.LIMIT :
            ]

        ProgrammerHumor.save_already_posted(already_posted)
