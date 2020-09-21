from PyDrocsid.database import db_thread, db
from PyDrocsid.translations import translations
from operator import itemgetter
from discord import Message
from discord.ext.commands import Cog, Bot
import re

from models.links import Links


def filter_links(url: str):
    if match := re.match(r"(https?://)?([a-zA-Z0-9\-_~.]+).*$", url, re.IGNORECASE):
        return match.group(2).split(".")
    return None


class LinksCog(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_message(self, message: Message):
        for url, *_ in re.findall(r"((https?://)?([a-zA-Z0-9\-_~]+\.)+[a-zA-Z0-9\-_~.]+(/\S*)?)", message.content):
            if domain := filter_links(url):
                root_domain = ".".join(itemgetter(len(domain) - 2, len(domain) - 1)(domain)).lower()
                links = [item.link for item in await db_thread(db.all, Links)]
                if root_domain in links:
                    continue
                if f"*.{root_domain}" in links or f"*.{domain[len(domain) - 1]}" in links:
                    await message.channel.send(translations.f_illegal_link(message.author.mention))
