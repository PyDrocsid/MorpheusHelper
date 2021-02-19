import discord
from discord.ext import commands, tasks
import time
import asyncio
from datetime import date

bot = commands.Bot(command_prefix='$')

# links
#
# https://github.com/Defelo/MorpheusHelper/blob/master/morpheushelper/cogs/mod.py#L41
# https://github.com/Defelo/MorpheusHelper/blob/master/morpheushelper/cogs/mod.py#L50


class VoicePlus(discord.Client):

    def __init__():
        self.users = []
        self.user_dict = {}

    async def member_leave(self, member: discord.Member, channel: VoiceChannel, group: Optional[DynamicVoiceGroup], dyn_channel: Optional[DynamicVoiceChannel]):
        self.user_dict.update(
            {'user': member.username, 'timemuted': datetime.datetime.now()})
        self.users.append(user_dict)

    @tasks.loop(minutes=1)
    async def check_dict(self):
        for item in self.users:
            if item["timemuted"].minute < 60:
                if item["timemuted"].minute + 5 == datetime.datetime.now().minute:
                    self.users.remove(item)
            else:
                item["timemuted"].minute = item["timemuted"].minute - 60

    @bot.command(name="vmute", aliases=['vm', 'm'])
    async def vmute(self, ctx, member: discord.Member, duration=0, *, unit=None):
        role = discord.utils.find(
            lambda r: r.name == 'InVoice', ctx.message.server.roles)
        if user.has_role(role):
            await member.edit(mute=True)
        elif member in self.users["user"]:
            await member.edit(mute=True)
            if unit == "s":
                wait = 1 * duration
                await asyncio.sleep(wait)
            elif unit == "m":
                wait = 60 * duration
                await asyncio.sleep(wait)
            await member.edit(mute=False)

    @bot.command(name="vunmute", aliases=['vu', 'u'])
    async def unmute(self, member: discord.Member):
        await member.edit(mute=False)

    @bot.command(name="vkick", aliases=['vk', 'k'])
    async def vkick(self, member: discord.Member):
        await member.move_to(None)
