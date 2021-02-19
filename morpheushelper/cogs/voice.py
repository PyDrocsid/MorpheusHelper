import discord
from discord.ext import commands, tasks
from discord.utils import get
import time
import asyncio
from datetime import date
from models.voice_plus import VoiceMutedLog, VoicePlusMember

bot = commands.Bot(command_prefix='$')


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
        channel = find_channel()
        overwrite = channel.overwrites_for(ctx.message.author)
        if overwrite.send_messages == True:
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

    async def find_channel():
        channel = get(ctx.message.server, name="voiceplus",
                      type=discord.ChannelType.text)
        return channel
