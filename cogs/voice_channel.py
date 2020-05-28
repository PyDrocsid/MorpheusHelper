from typing import Optional

from discord import Member, VoiceState, Guild, VoiceChannel, Role
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.role_voice_link import RoleVoiceLink
from translations import translations
from util import permission_level, send_to_changelog, MODERATOR


class VoiceChannelCog(Cog, name="Voice Channels"):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def on_ready(self) -> bool:
        guild: Guild = self.bot.guilds[0]
        print(translations.updating_voice_roles)
        linked_roles = {}
        for link in await run_in_thread(db.query, RoleVoiceLink):
            role = guild.get_role(link.role)
            voice = guild.get_channel(link.voice_channel)
            if role is not None and voice is not None:
                linked_roles.setdefault(role, set()).add(voice)

        for member in guild.members:
            for role, channels in linked_roles.items():
                if member.voice is not None and member.voice.channel in channels:
                    if role not in member.roles:
                        await member.add_roles(role)
                else:
                    if role in member.roles:
                        await member.remove_roles(role)
        print(translations.voice_init_done)
        return True

    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> bool:
        if before.channel == after.channel:
            return True

        guild: Guild = member.guild
        if before.channel is not None:
            await member.remove_roles(
                *(
                    role
                    for link in await run_in_thread(db.query, RoleVoiceLink, voice_channel=before.channel.id)
                    if (role := guild.get_role(link.role)) is not None
                )
            )
        if after.channel is not None:
            await member.add_roles(
                *(
                    role
                    for link in await run_in_thread(db.query, RoleVoiceLink, voice_channel=after.channel.id)
                    if (role := guild.get_role(link.role)) is not None
                )
            )
        return True

    @commands.group(aliases=["vc"])
    @permission_level(MODERATOR)
    @guild_only()
    async def voice(self, ctx: Context):
        """
        manage links between voice channels and roles
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(VoiceChannelCog.voice)

    @voice.command(name="list", aliases=["l", "?"])
    async def list_links(self, ctx: Context):
        """
        list all links between voice channels and roles
        """

        out = []
        guild: Guild = ctx.guild
        for link in await run_in_thread(db.all, RoleVoiceLink):
            role: Optional[Role] = guild.get_role(link.role)
            voice: Optional[VoiceChannel] = guild.get_channel(link.voice_channel)
            if role is None or voice is None:
                await run_in_thread(db.delete, link)
            else:
                out.append(f"`{voice}` (`{voice.id}`) -> `@{role}` (`{role.id}`)")

        await ctx.send("\n".join(out) or translations.no_links_created)

    @voice.command(name="link", aliases=["add", "a", "+"])
    async def create_link(self, ctx: Context, voice_channel: VoiceChannel, *, role: Role):
        """
        link a voice channel with a role
        """

        if await run_in_thread(db.first, RoleVoiceLink, role=role.id, voice_channel=voice_channel.id) is not None:
            raise CommandError(translations.link_already_exists)

        if role > ctx.me.top_role:
            raise CommandError(translations.f_link_not_created_too_high(role, ctx.me.top_role))
        if role.managed:
            raise CommandError(translations.f_link_not_created_managed_role(role))

        await run_in_thread(RoleVoiceLink.create, role.id, voice_channel.id)
        for member in voice_channel.members:
            await member.add_roles(role)

        await ctx.send(translations.f_link_created(voice_channel, role))
        await send_to_changelog(ctx.guild, translations.f_link_created(voice_channel, role))

    @voice.command(name="unlink", aliases=["remove", "del", "u", "r", "d", "-"])
    async def remove_link(self, ctx: Context, voice_channel: VoiceChannel, *, role: Role):
        """
        delete the link between a voice channel and a role
        """

        if (link := await run_in_thread(db.first, RoleVoiceLink, role=role.id, voice_channel=voice_channel.id)) is None:
            raise CommandError(translations.link_not_found)

        await run_in_thread(db.delete, link)
        for member in voice_channel.members:
            await member.remove_roles(role)

        await ctx.send(translations.link_deleted)
        await send_to_changelog(ctx.guild, translations.f_log_link_deleted(voice_channel, role))
