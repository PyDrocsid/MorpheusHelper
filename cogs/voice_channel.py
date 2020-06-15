import random
import re
from typing import Optional, Union, Tuple, List

from discord import CategoryChannel, PermissionOverwrite, NotFound
from discord import Member, VoiceState, Guild, VoiceChannel, Role, HTTPException, TextChannel
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError

from database import run_in_thread, db
from models.dynamic_voice import DynamicVoiceChannel, DynamicVoiceGroup
from models.role_voice_link import RoleVoiceLink
from models.settings import Settings
from multilock import MultiLock
from permission import Permission
from translations import translations
from util import permission_level, send_to_changelog, check_permissions, get_prefix


async def gather_roles(guild: Guild, channel_id: int) -> List[Role]:
    return [
        role
        for link in await run_in_thread(db.query, RoleVoiceLink, voice_channel=channel_id)
        if (role := guild.get_role(link.role)) is not None
    ]


class VoiceChannelCog(Cog, name="Voice Channels"):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.channel_lock = MultiLock()

    async def on_ready(self) -> bool:
        guild: Guild = self.bot.guilds[0]
        print(translations.updating_voice_roles)
        linked_roles = {}
        for link in await run_in_thread(db.query, RoleVoiceLink):
            role = guild.get_role(link.role)
            voice = guild.get_channel(link.voice_channel)
            if role is not None and voice is not None:
                linked_roles.setdefault(role, set()).add(voice)

                group: Optional[DynamicVoiceGroup] = await run_in_thread(
                    db.first, DynamicVoiceGroup, channel_id=voice.id
                )
                if group is not None:
                    for dyn_channel in await run_in_thread(db.query, DynamicVoiceChannel, group_id=group.id):
                        channel: Optional[VoiceChannel] = guild.get_channel(dyn_channel.channel_id)
                        if channel is not None:
                            linked_roles[role].add(channel)

        for member in guild.members:
            for role, channels in linked_roles.items():
                if any(member in channel.members for channel in channels):
                    if role not in member.roles:
                        await member.add_roles(role)
                else:
                    if role in member.roles:
                        await member.remove_roles(role)

        for group in await run_in_thread(db.query, DynamicVoiceGroup):
            channel: Optional[VoiceChannel] = guild.get_channel(group.channel_id)
            if channel is None:
                continue

            for member in channel.members:
                await self.member_join(member, channel)

            for dyn_channel in await run_in_thread(db.all, DynamicVoiceChannel, group_id=group.id):
                channel: Optional[VoiceChannel] = guild.get_channel(dyn_channel.channel_id)
                if channel is not None and not channel.members:
                    await channel.delete()
                    if (text_channel := self.bot.get_channel(dyn_channel.text_chat_id)) is not None:
                        await text_channel.delete()
                    await run_in_thread(db.delete, dyn_channel)
            await self.update_dynamic_voice_group(group)

        print(translations.voice_init_done)
        return True

    async def get_dynamic_voice_channel(
        self, member: Member, owner_required: bool
    ) -> Tuple[DynamicVoiceGroup, DynamicVoiceChannel, VoiceChannel, Optional[TextChannel]]:
        if member.voice is None or member.voice.channel is None:
            raise CommandError(translations.not_in_private_voice)

        channel: VoiceChannel = member.voice.channel
        dyn_channel: DynamicVoiceChannel = await run_in_thread(db.first, DynamicVoiceChannel, channel_id=channel.id)
        if dyn_channel is None:
            raise CommandError(translations.not_in_private_voice)
        group: DynamicVoiceGroup = await run_in_thread(db.get, DynamicVoiceGroup, dyn_channel.group_id)
        if group is None or group.public:
            raise CommandError(translations.not_in_private_voice)

        if owner_required and dyn_channel.owner != member.id:
            if not await check_permissions(member, Permission.vc_private_owner):
                raise CommandError(translations.private_voice_owner_required)

        voice_channel: VoiceChannel = self.bot.get_channel(dyn_channel.channel_id)
        text_chat: Optional[TextChannel] = self.bot.get_channel(dyn_channel.text_chat_id)

        return group, dyn_channel, voice_channel, text_chat

    async def member_join(self, member: Member, channel: VoiceChannel):
        await member.add_roles(*await gather_roles(member.guild, channel.id))

        dyn_channel: DynamicVoiceChannel = await run_in_thread(db.first, DynamicVoiceChannel, channel_id=channel.id)
        if dyn_channel is not None:
            group: Optional[DynamicVoiceGroup] = await run_in_thread(db.get, DynamicVoiceGroup, dyn_channel.group_id)
            if group is not None:
                await member.add_roles(*await gather_roles(member.guild, group.channel_id))

            text_chat: Optional[TextChannel] = self.bot.get_channel(dyn_channel.text_chat_id)
            if text_chat is not None:
                await text_chat.set_permissions(member, read_messages=True)
                await text_chat.send(translations.f_dyn_voice_joined(member.mention))
            return

        group: DynamicVoiceGroup = await run_in_thread(db.first, DynamicVoiceGroup, channel_id=channel.id)
        if group is None:
            return

        if channel.category is not None and len(channel.category.channels) >= 49 or len(channel.guild.channels) >= 499:
            await member.move_to(None)
            return

        guild: Guild = channel.guild
        number = len(await run_in_thread(db.all, DynamicVoiceChannel, group_id=group.id)) + 1
        chan: VoiceChannel = await channel.clone(name=group.name + " " + str(number))
        category: Union[CategoryChannel, Guild] = channel.category or guild
        overwrites = {
            guild.default_role: PermissionOverwrite(read_messages=False, connect=False),
            guild.me: PermissionOverwrite(read_messages=True),
        }
        if (team_role := guild.get_role(await run_in_thread(Settings.get, int, "team_role"))) is not None:
            overwrites[team_role] = PermissionOverwrite(read_messages=True, connect=True)
        text_chat: TextChannel = await category.create_text_channel(chan.name, overwrites=overwrites)
        await chan.edit(position=channel.position + number)
        if not group.public:
            await chan.edit(overwrites={**overwrites, member: PermissionOverwrite(read_messages=True, connect=True)})
        try:
            await member.move_to(chan)
        except HTTPException:
            await chan.delete()
            await text_chat.delete()
            return
        else:
            await run_in_thread(DynamicVoiceChannel.create, chan.id, group.id, text_chat.id, member.id)
        await self.update_dynamic_voice_group(group)
        await text_chat.send(translations.f_dyn_voice_created(member.mention))
        if not group.public:
            await text_chat.send(translations.f_private_dyn_voice_help(prefix=await get_prefix()))

    async def member_leave(self, member: Member, channel: VoiceChannel):
        try:
            await member.remove_roles(*await gather_roles(member.guild, channel.id))
        except NotFound:  # member left the server
            pass

        dyn_channel: DynamicVoiceChannel = await run_in_thread(db.first, DynamicVoiceChannel, channel_id=channel.id)
        if dyn_channel is not None:
            group: Optional[DynamicVoiceGroup] = await run_in_thread(db.get, DynamicVoiceGroup, dyn_channel.group_id)
            if group is not None:
                try:
                    await member.remove_roles(*await gather_roles(member.guild, group.channel_id))
                except NotFound:  # member left the server
                    pass

            text_chat: Optional[TextChannel] = self.bot.get_channel(dyn_channel.text_chat_id)
            if text_chat is not None:
                await text_chat.set_permissions(member, overwrite=None)
                await text_chat.send(translations.f_dyn_voice_left(member.mention))

            if member.id == dyn_channel.owner and len(channel.members) > 0:
                new_owner: Member = random.choice(channel.members)
                await run_in_thread(DynamicVoiceChannel.change_owner, dyn_channel.channel_id, new_owner.id)
                if text_chat is not None:
                    await text_chat.send(translations.f_private_voice_owner_changed(new_owner.mention))

        if len(channel.members) > 0:
            return

        dyn_channel: Optional[DynamicVoiceChannel] = await run_in_thread(db.get, DynamicVoiceChannel, channel.id)
        if dyn_channel is None:
            return
        group: DynamicVoiceGroup = await run_in_thread(db.get, DynamicVoiceGroup, dyn_channel.group_id)
        if group is None:
            return

        await channel.delete()
        if (text_channel := self.bot.get_channel(dyn_channel.text_chat_id)) is not None:
            await text_channel.delete()
        await run_in_thread(db.delete, dyn_channel)
        await self.update_dynamic_voice_group(group)

    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> bool:
        if before.channel == after.channel:
            return True

        if (channel := before.channel) is not None:
            await self.channel_lock.acquire(channel.id)
            await self.member_leave(member, channel)
            self.channel_lock.release(channel.id)
        if (channel := after.channel) is not None:
            await self.channel_lock.acquire(channel.id)
            await self.member_join(member, channel)
            self.channel_lock.release(channel.id)
        return True

    async def update_dynamic_voice_group(self, group: DynamicVoiceGroup):
        base_channel: Optional[VoiceChannel] = self.bot.get_channel(group.channel_id)
        if base_channel is None:
            await run_in_thread(db.delete, group)
            return

        channels = []
        for dyn_channel in await run_in_thread(db.all, DynamicVoiceChannel, group_id=group.id):
            channel: Optional[VoiceChannel] = self.bot.get_channel(dyn_channel.channel_id)
            text_chat: Optional[TextChannel] = self.bot.get_channel(dyn_channel.text_chat_id)
            if channel is not None and text_chat is not None:
                channels.append((channel, text_chat))
            else:
                await run_in_thread(db.delete, dyn_channel)

        channels.sort(key=lambda c: c[0].position)

        for i, (channel, text_chat) in enumerate(channels):
            name = f"{group.name} {i + 1}"
            await channel.edit(name=name, position=base_channel.position + i + 1)
            await text_chat.edit(name=name)
        await base_channel.edit(position=base_channel.position)

    @commands.group(aliases=["vc"])
    @guild_only()
    async def voice(self, ctx: Context):
        """
        manage voice channels
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(VoiceChannelCog.voice)

    @voice.group(name="dynamic", aliases=["dyn", "d"])
    @permission_level(Permission.vc_manage_dyn)
    async def dynamic(self, ctx: Context):
        """
        manage dynamic voice channels
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(VoiceChannelCog.dynamic)

    @dynamic.command(name="list", aliases=["l", "?"])
    async def list_dyn(self, ctx: Context):
        """
        list dynamic voice channels
        """

        out = []
        for group in await run_in_thread(db.all, DynamicVoiceGroup):
            cnt = len(await run_in_thread(db.all, DynamicVoiceChannel, group_id=group.id))
            channel: Optional[VoiceChannel] = ctx.guild.get_channel(group.channel_id)
            if channel is None:
                await run_in_thread(db.delete, group)
                continue

            out.append(f"- [{['private', 'public'][group.public]}] " + translations.f_group_list_entry(group.name, cnt))

        if out:
            await ctx.send("\n".join(out))
        else:
            await ctx.send(translations.no_dyn_group)

    @dynamic.command(name="add", aliases=["a", "+"])
    async def add_dyn(self, ctx: Context, visibility: str, *, voice_channel: VoiceChannel):
        """
        create a new dynamic voice channel group
        """

        if visibility.lower() not in ["public", "private"]:
            raise CommandError(translations.error_visibility)
        public = visibility.lower() == "public"

        if await run_in_thread(db.get, DynamicVoiceChannel, voice_channel.id) is not None:
            raise CommandError(translations.dyn_group_already_exists)
        if await run_in_thread(db.first, DynamicVoiceGroup, channel_id=voice_channel.id) is not None:
            raise CommandError(translations.dyn_group_already_exists)

        name: str = re.match(r"^(.*?) ?\d*$", voice_channel.name).group(1) or voice_channel.name
        await run_in_thread(DynamicVoiceGroup.create, name, voice_channel.id, public)
        await voice_channel.edit(name=f"New {name}")
        await ctx.send(translations.dyn_group_created)
        await send_to_changelog(ctx.guild, translations.f_log_dyn_group_created(name))

    @dynamic.command(name="del", aliases=["remove", "r", "d", "-"])
    async def remove_dyn(self, ctx: Context, *, voice_channel: VoiceChannel):
        """
        remove a dynamic voice channel group
        """

        group: DynamicVoiceGroup = await run_in_thread(db.first, DynamicVoiceGroup, channel_id=voice_channel.id)
        if group is None:
            raise CommandError(translations.dyn_group_not_found)

        await run_in_thread(db.delete, group)
        for dync in await run_in_thread(db.all, DynamicVoiceChannel, group_id=group.id):
            channel: Optional[VoiceChannel] = self.bot.get_channel(dync.channel_id)
            text_channel: Optional[TextChannel] = self.bot.get_channel(dync.text_chat_id)
            await run_in_thread(db.delete, dync)
            if channel is not None:
                await channel.delete()
            if text_channel is not None:
                await text_channel.delete()

        await voice_channel.edit(name=group.name)
        await ctx.send(translations.dyn_group_removed)
        await send_to_changelog(ctx.guild, translations.f_log_dyn_group_removed(group.name))

    @voice.command(name="close", aliases=["c"])
    async def close(self, ctx: Context):
        """
        close a private voice channel
        """

        group, dyn_channel, voice_channel, text_channel = await self.get_dynamic_voice_channel(ctx.author, True)
        await run_in_thread(db.delete, dyn_channel)
        if text_channel is not None:
            await text_channel.delete()
        await voice_channel.delete()
        await self.update_dynamic_voice_group(group)
        if text_channel != ctx.channel:
            await ctx.send(translations.private_voice_closed)

    @voice.command(name="invite", aliases=["i", "add", "a", "+"])
    async def invite(self, ctx: Context, member: Member):
        """
        invite a member into a private voice channel
        """

        group, dyn_channel, voice_channel, text_channel = await self.get_dynamic_voice_channel(ctx.author, True)
        await voice_channel.set_permissions(member, read_messages=True, connect=True)
        if text_channel is not None:
            await text_channel.send(translations.f_user_added_to_private_voice(member.mention))
        if text_channel != ctx.channel:
            await ctx.send(translations.user_added_to_private_voice_response)

    @voice.command(name="remove", aliases=["r", "kick", "k", "-"])
    async def remove(self, ctx: Context, member: Member):
        """
        remove a member from a private voice channel
        """

        group, dyn_channel, voice_channel, text_channel = await self.get_dynamic_voice_channel(ctx.author, True)
        if member == ctx.author or member == self.bot.user:
            raise CommandError(translations.cannot_remove_member)

        await voice_channel.set_permissions(member, overwrite=None)
        team_role = await run_in_thread(Settings.get, int, "team_role")
        if member.guild_permissions.administrator or any(role.id == team_role for role in member.roles):
            raise CommandError(translations.member_could_not_be_kicked)

        if member.voice is not None and member.voice.channel == voice_channel:
            await member.move_to(None)
        if text_channel is not None:
            await text_channel.send(translations.f_user_removed_from_private_voice(member.mention))
        if text_channel != ctx.channel:
            await ctx.send(translations.user_removed_from_private_voice_response)

    @voice.command(name="owner", aliases=["o"])
    async def owner(self, ctx: Context, member: Optional[Member]):
        """
        transfer ownership of a private voice channel
        """

        change = member is not None
        _, dyn_channel, voice_channel, text_channel = await self.get_dynamic_voice_channel(ctx.author, change)

        if not change:
            await ctx.send(translations.f_owner_of_private_voice(f"<@{dyn_channel.owner}>"))
            return

        if member not in voice_channel.members:
            raise CommandError(translations.user_not_in_this_channel)
        if member.bot:
            raise CommandError(translations.bot_no_owner_transfer)

        await run_in_thread(DynamicVoiceChannel.change_owner, dyn_channel.channel_id, member.id)
        if text_channel is not None:
            await text_channel.send(translations.f_private_voice_owner_changed(member.mention))
        if text_channel != ctx.channel:
            await ctx.send(translations.private_voice_owner_changed_response)

    @voice.group(name="link", aliases=["l"])
    @permission_level(Permission.vc_manage_link)
    async def link(self, ctx: Context):
        """
        manage links between voice channels and roles
        """

        if ctx.invoked_subcommand is None:
            await ctx.send_help(VoiceChannelCog.link)

    @link.command(name="list", aliases=["l", "?"])
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

    @link.command(name="add", aliases=["a", "+"])
    async def create_link(self, ctx: Context, channel: VoiceChannel, *, role: Role):
        """
        link a voice channel with a role
        """

        if await run_in_thread(db.get, DynamicVoiceChannel, channel.id) is not None:
            raise CommandError(translations.link_on_dynamic_channel_not_created)
        if await run_in_thread(db.first, RoleVoiceLink, role=role.id, voice_channel=channel.id) is not None:
            raise CommandError(translations.link_already_exists)

        if role > ctx.me.top_role:
            raise CommandError(translations.f_link_not_created_too_high(role, ctx.me.top_role))
        if role.managed:
            raise CommandError(translations.f_link_not_created_managed_role(role))

        await run_in_thread(RoleVoiceLink.create, role.id, channel.id)
        for member in channel.members:
            await member.add_roles(role)

        group: Optional[DynamicVoiceGroup] = await run_in_thread(db.first, DynamicVoiceGroup, channel_id=channel.id)
        if group is not None:
            for dyn_channel in await run_in_thread(db.query, DynamicVoiceChannel, group_id=group.id):
                dchannel: Optional[VoiceChannel] = self.bot.get_channel(dyn_channel.channel_id)
                if dchannel is not None:
                    for member in dchannel.members:
                        await member.add_roles(role)

        await ctx.send(translations.f_link_created(channel, role))
        await send_to_changelog(ctx.guild, translations.f_link_created(channel, role))

    @link.command(name="del", aliases=["remove", "r", "d", "-"])
    async def remove_link(self, ctx: Context, channel: VoiceChannel, *, role: Role):
        """
        delete the link between a voice channel and a role
        """

        if (link := await run_in_thread(db.first, RoleVoiceLink, role=role.id, voice_channel=channel.id)) is None:
            raise CommandError(translations.link_not_found)

        await run_in_thread(db.delete, link)
        for member in channel.members:
            await member.remove_roles(role)

        group: Optional[DynamicVoiceGroup] = await run_in_thread(db.first, DynamicVoiceGroup, channel_id=channel.id)
        if group is not None:
            for dyn_channel in await run_in_thread(db.query, DynamicVoiceChannel, group_id=group.id):
                dchannel: Optional[VoiceChannel] = self.bot.get_channel(dyn_channel.channel_id)
                if dchannel is not None:
                    for member in dchannel.members:
                        await member.remove_roles(role)

        await ctx.send(translations.link_deleted)
        await send_to_changelog(ctx.guild, translations.f_log_link_deleted(channel, role))
