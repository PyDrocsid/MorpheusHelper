from collections import OrderedDict
from typing import List, OrderedDict as OrderedDictType

from discord import Message, NotFound
from discord.ext.commands import Bot

error_cache: OrderedDictType[int, List[Message]] = OrderedDict()


async def handle_command_edit(bot: Bot, message: Message):
    if message.id not in error_cache:
        return

    for msg in error_cache.pop(message.id):
        try:
            await msg.delete()
        except NotFound:
            pass
    await bot.process_commands(message)


def add_to_error_cache(message: Message, response: List[Message]):
    if message.author.bot:
        return

    error_cache[message.id] = response

    while len(error_cache) > 1000:
        error_cache.popitem(last=False)
