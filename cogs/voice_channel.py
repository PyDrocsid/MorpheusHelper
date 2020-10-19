import random
import re
from typing import Optional, Union, Tuple, List, Dict, Set

from PyDrocsid.database import db_thread, db
from PyDrocsid.multilock import MultiLock
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations
from discord import CategoryChannel, PermissionOverwrite, NotFound, Message, Embed, Forbidden
from discord import Member, VoiceState, Guild, VoiceChannel, Role, HTTPException, TextChannel
from discord.ext import commands
from discord.ext.commands import Cog, Bot, guild_only, Context, CommandError, UserInputError

from models.dynamic_voice import DynamicVoiceChannel, DynamicVoiceGroup
from models.role_voice_link import RoleVoiceLink
from permissions import Permission
from util import get_prefix, send_to_changelog, is_teamler


async def gather_roles(guild: Guild, channel_id: int) -> List[Role]:
    return [
        role
        for link in await db_thread(db.all, RoleVoiceLink, voice_channel=channel_id)
        if (role := guild.get_role(link.role)) is not None
    ]


async def get_group_channel(channel: VoiceChannel) -> Tuple[Optional[DynamicVoiceGroup], Optional[DynamicVoiceChannel]]:
    dyn_channel: DynamicVoiceChannel = await db_thread(db.first, DynamicVoiceChannel, channel_id=channel.id)
    if dyn_channel is not None:
        group = await db_thread(db.get, DynamicVoiceGroup, dyn_channel.group_id)
    else:
        group = await db_thread(db.first, DynamicVoiceGroup, channel_id=channel.id)

    return group, dyn_channel


class VoiceChannelCog(Cog, name="Voice Channels"):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.channel_lock = MultiLock()
        self.group_lock = MultiLock()

    async def send_voice_msg(self, channel: TextChannel, public: bool, title: str, msg: str):
        messages: List[Message] = await channel.history(limit=1).flatten()
        if messages and messages[0].author == self.bot.user:
            embeds: List[Embed] = messages[0].embeds
            if len(embeds) == 1 and embeds[0].title == title and len(embeds[0].description + msg) <= 2000:
                embed = embeds[0]
                embed.description += "\n" + msg
                await messages[0].edit(embed=embed)
                return

        embed = Embed(title=title, color=[0x256BE6, 0x03AD28][public], description=msg)
        await channel.send(embed=embed)

    async def on_ready(self):
        guild: Guild = self.bot.guilds[0]
        print(translations.updating_voice_roles)
        linked_roles: Dict[Role, Set[VoiceChannel]] = {}
        for link in await db_thread(db.all, RoleVoiceLink):
            role = guild.get_role(link.role)
            voice = guild.get_channel(link.voice_channel)
            if role is None or voice is None:
                continue

            linked_roles.setdefault(role, set()).add(voice)

            group: Optional[DynamicVoiceGroup] = await db_thread(db.first, DynamicVoiceGroup, channel_id=voice.id)
            if group is None:
                continue
            for dyn_channel in await db_thread(db.all, DynamicVoiceChannel, group_id=group.id):
                channel: Optional[VoiceChannel] = guild.get_channel(dyn_channel.channel_id)
                if channel is not None:
                    linked_roles[role].add(channel)

        for role, channels in linked_roles.items():
            members = set()
            for channel in channels:
                members.update(channel.members)
            for member in members:
                if role not in member.roles:
                    await member.add_roles(role)
            for member in role.members:
                if member not in members:
                    await member.remove_roles(role)

        for group in await db_thread(db.all, DynamicVoiceGroup):
            channel: Optional[VoiceChannel] = guild.get_channel(group.channel_id)
            if channel is None:
                continue

            for member in channel.members:
                group, dyn_channel = await get_group_channel(channel)
                async with self.group_lock[group.id if group is not None else None]:
                    await self.member_join(member, channel, group, dyn_channel)

            for dyn_channel in await db_thread(db.all, DynamicVoiceChannel, group_id=group.id):
                channel: Optional[VoiceChannel] = guild.get_channel(dyn_channel.channel_id)
                if channel is not None and all(member.bot for member in channel.members):
                    await channel.delete()
                    if (text_channel := self.bot.get_channel(dyn_channel.text_chat_id)) is not None:
                        await text_channel.delete()
                    await db_thread(db.delete, dyn_channel)
            await self.update_dynamic_voice_group(group)

        print(translations.voice_init_done)

    async def get_dynamic_voice_channel(
        self, member: Member, owner_required: bool
    ) -> Tuple[DynamicVoiceGroup, DynamicVoiceChannel, VoiceChannel, Optional[TextChannel]]:
        if member.voice is None or member.voice.channel is None:
            raise CommandError(translations.not_in_private_voice)

        channel: VoiceChannel = member.voice.channel
        dyn_channel: DynamicVoiceChannel = await db_thread(db.first, DynamicVoiceChannel, channel_id=channel.id)
        if dyn_channel is None:
            raise CommandError(translations.not_in_private_voice)
        group: DynamicVoiceGroup = await db_thread(db.get, DynamicVoiceGroup, dyn_channel.group_id)
        if group is None or group.public:
            raise CommandError(translations.not_in_private_voice)

        if owner_required and dyn_channel.owner != member.id:
            if not await Permission.vc_private_owner.check_permissions(member):
                raise CommandError(translations.private_voice_owner_required)

        voice_channel: VoiceChannel = self.bot.get_channel(dyn_channel.channel_id)
        text_chat: Optional[TextChannel] = self.bot.get_channel(dyn_channel.text_chat_id)

        return group, dyn_channel, voice_channel, text_chat

    async def member_join(
        self,
        member: Member,
        channel: VoiceChannel,
        group: Optional[DynamicVoiceGroup],
        dyn_channel: Optional[DynamicVoiceChannel],
    ):
        await member.add_roles(*await gather_roles(member.guild, channel.id))

        if dyn_channel is not None:
            if group is not None:
                await member.add_roles(*await gather_roles(member.guild, group.channel_id))

            text_chat: Optional[TextChannel] = self.bot.get_channel(dyn_channel.text_chat_id)
            if text_chat is not None:
                if not group.public:
                    await channel.set_permissions(member, read_messages=True, connect=True)
                await text_chat.set_permissions(member, read_messages=True)
                await self.send_voice_msg(
                    text_chat, group.public, translations.voice_channel, translations.f_dyn_voice_joined(member.mention)
                )
            return

        if group is None:
            return

        if member.bot:
            await member.move_to(None)
            return
        if channel.category is not None and len(channel.category.channels) >= 49 or len(channel.guild.channels) >= 499:
            await member.move_to(None)
            return

        guild: Guild = channel.guild
        number = len(await db_thread(db.all, DynamicVoiceChannel, group_id=group.id)) + 1
        chan: VoiceChannel = await channel.clone(name=group.name + " " + str(number))
        category: Union[CategoryChannel, Guild] = channel.category or guild
        overwrites = {
            guild.default_role: PermissionOverwrite(read_messages=False, connect=False),
            guild.me: PermissionOverwrite(read_messages=True, connect=True),
        }
        if (team_role := guild.get_role(await Settings.get(int, "team_role"))) is not None:
            overwrites[team_role] = PermissionOverwrite(read_messages=True, connect=True)
        text_chat: TextChannel = await category.create_text_channel(chan.name, overwrites=overwrites)

        await text_chat.set_permissions(member, read_messages=True)
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
            await db_thread(DynamicVoiceChannel.create, chan.id, group.id, text_chat.id, member.id)
        await self.update_dynamic_voice_group(group)
        if not group.public:
            await self.send_voice_msg(
                text_chat,
                group.public,
                translations.private_dyn_voice_help_title,
                translations.f_private_dyn_voice_help_content(prefix=await get_prefix()),
            )
        await self.send_voice_msg(
            text_chat, group.public, translations.voice_channel, translations.f_dyn_voice_created(member.mention)
        )

    async def member_leave(
        self,
        member: Member,
        channel: VoiceChannel,
        group: Optional[DynamicVoiceGroup],
        dyn_channel: Optional[DynamicVoiceChannel],
    ):
        try:
            await member.remove_roles(*await gather_roles(member.guild, channel.id))
        except NotFound:  # member left the server
            pass

        if dyn_channel is None or group is None:
            return

        try:
            await member.remove_roles(*await gather_roles(member.guild, group.channel_id))
        except NotFound:  # member left the server
            pass

        text_chat: Optional[TextChannel] = self.bot.get_channel(dyn_channel.text_chat_id)
        if text_chat is not None:
            if group.public:
                await text_chat.set_permissions(member, overwrite=None)
            await self.send_voice_msg(
                text_chat, group.public, translations.voice_channel, translations.f_dyn_voice_left(member.mention)
            )

        members: List[Member] = [member for member in channel.members if not member.bot]
        if not group.public and member.id == dyn_channel.owner and len(members) > 0:
            new_owner: Member = random.choice(members)
            await db_thread(DynamicVoiceChannel.change_owner, dyn_channel.channel_id, new_owner.id)
            if text_chat is not None:
                await self.send_voice_msg(
                    text_chat,
                    group.public,
                    translations.voice_channel,
                    translations.f_private_voice_owner_changed(new_owner.mention),
                )

        if len(members) > 0:
            return

        await channel.delete()
        if text_chat is not None:
            await text_chat.delete()
        await db_thread(db.delete, dyn_channel)
        await self.update_dynamic_voice_group(group)

    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if before.channel == after.channel:
            return

        if (channel := before.channel) is not None:
            async with self.channel_lock[channel.id]:
                group, dyn_channel = await get_group_channel(channel)
                async with self.group_lock[group.id if group is not None else None]:
                    await self.member_leave(member, channel, group, dyn_channel)
        if (channel := after.channel) is not None:
            async with self.channel_lock[channel.id]:
                group, dyn_channel = await get_group_channel(channel)
                async with self.group_lock[group.id if group is not None else None]:
                    await self.member_join(member, channel, group, dyn_channel)

    async def update_dynamic_voice_group(self, group: DynamicVoiceGroup):
        base_channel: Optional[VoiceChannel] = self.bot.get_channel(group.channel_id)
        if base_channel is None:
            await db_thread(db.delete, group)
            return

        channels = []
        for dyn_channel in await db_thread(db.all, DynamicVoiceChannel, group_id=group.id):
            channel: Optional[VoiceChannel] = self.bot.get_channel(dyn_channel.channel_id)
            text_chat: Optional[TextChannel] = self.bot.get_channel(dyn_channel.text_chat_id)
            if channel is not None and text_chat is not None:
                channels.append((channel, text_chat))
            else:
                await db_thread(db.delete, dyn_channel)

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
            raise UserInputError

    @voice.group(name="dynamic", aliases=["dyn", "d"])
    @Permission.vc_manage_dyn.check
    async def voice_dynamic(self, ctx: Context):
        """
        manage dynamic voice channels
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @voice_dynamic.command(name="list", aliases=["l", "?"])
    async def voice_dynamic_list(self, ctx: Context):
        """
        list dynamic voice channels
        """

        out = []
        for group in await db_thread(db.all, DynamicVoiceGroup):
            cnt = len(await db_thread(db.all, DynamicVoiceChannel, group_id=group.id))
            channel: Optional[VoiceChannel] = ctx.guild.get_channel(group.channel_id)
            if channel is None:
                await db_thread(db.delete, group)
                continue

            out.append(f"- [{['private', 'public'][group.public]}] " + translations.f_group_list_entry(group.name, cnt))

        if out:
            await ctx.send("\n".join(out))
        else:
            await ctx.send(translations.no_dyn_group)

    @voice_dynamic.command(name="add", aliases=["a", "+"])
    async def voice_dynamic_add(self, ctx: Context, visibility: str, *, voice_channel: VoiceChannel):
        """
        create a new dynamic voice channel group
        """

        if visibility.lower() not in ["public", "private"]:
            raise CommandError(translations.error_visibility)
        public = visibility.lower() == "public"

        if await db_thread(db.get, DynamicVoiceChannel, voice_channel.id) is not None:
            raise CommandError(translations.dyn_group_already_exists)
        if await db_thread(db.first, DynamicVoiceGroup, channel_id=voice_channel.id) is not None:
            raise CommandError(translations.dyn_group_already_exists)

        name: str = re.match(r"^(.*?) ?\d*$", voice_channel.name).group(1) or voice_channel.name
        await db_thread(DynamicVoiceGroup.create, name, voice_channel.id, public)
        await voice_channel.edit(name=f"New {name}")
        await ctx.send(translations.dyn_group_created)
        await send_to_changelog(ctx.guild, translations.f_log_dyn_group_created(name))

    @voice_dynamic.command(name="remove", aliases=["del", "d", "r", "-"])
    async def voice_dynamic_remove(self, ctx: Context, *, voice_channel: VoiceChannel):
        """
        remove a dynamic voice channel group
        """

        group: DynamicVoiceGroup = await db_thread(db.first, DynamicVoiceGroup, channel_id=voice_channel.id)
        if group is None:
            raise CommandError(translations.dyn_group_not_found)

        await db_thread(db.delete, group)
        for dync in await db_thread(db.all, DynamicVoiceChannel, group_id=group.id):
            channel: Optional[VoiceChannel] = self.bot.get_channel(dync.channel_id)
            text_channel: Optional[TextChannel] = self.bot.get_channel(dync.text_chat_id)
            await db_thread(db.delete, dync)
            if channel is not None:
                await channel.delete()
            if text_channel is not None:
                await text_channel.delete()

        await voice_channel.edit(name=group.name)
        await ctx.send(translations.dyn_group_removed)
        await send_to_changelog(ctx.guild, translations.f_log_dyn_group_removed(group.name))

    @voice.command(name="close", aliases=["c"])
    async def voice_close(self, ctx: Context):
        """
        close a private voice channel
        """

        group, dyn_channel, voice_channel, text_channel = await self.get_dynamic_voice_channel(ctx.author, True)
        await db_thread(db.delete, dyn_channel)

        roles = await gather_roles(voice_channel.guild, group.channel_id)
        for member in voice_channel.members:
            await member.remove_roles(*roles)

        if text_channel is not None:
            await text_channel.delete()
        await voice_channel.delete()
        await self.update_dynamic_voice_group(group)
        if text_channel != ctx.channel:
            await ctx.send(translations.private_voice_closed)

    @voice.command(name="invite", aliases=["i", "add", "a", "+"])
    async def voice_invite(self, ctx: Context, member: Member):
        """
        invite a member into a private voice channel
        """

        if self.bot.user == member:
            raise CommandError(translations.cannot_add_user)

        group, _, voice_channel, text_channel = await self.get_dynamic_voice_channel(ctx.author, True)
        await text_channel.set_permissions(member, read_messages=True)
        await voice_channel.set_permissions(member, read_messages=True, connect=True)

        text = translations.f_user_added_to_private_voice_dm(member.mention)
        if ctx.author.permissions_in(voice_channel).create_instant_invite:
            try:
                text += f"\n{await voice_channel.create_invite(unique=False)}"
            except Forbidden:
                pass

        reponse = translations.f_user_added_to_private_voice(member.mention)
        try:
            await member.send(text)
        except (Forbidden, HTTPException):
            reponse = translations.f_user_added_to_private_voice_no_dm(member.mention)

        if text_channel is not None:
            await self.send_voice_msg(text_channel, group.public, translations.voice_channel, reponse)
        if text_channel != ctx.channel:
            await ctx.send(translations.user_added_to_private_voice_response)

    @voice.command(name="remove", aliases=["r", "kick", "k", "-"])
    async def voice_remove(self, ctx: Context, member: Member):
        """
        remove a member from a private voice channel
        """

        group, _, voice_channel, text_channel = await self.get_dynamic_voice_channel(ctx.author, True)
        if member in (ctx.author, self.bot.user):
            raise CommandError(translations.cannot_remove_member)

        await text_channel.set_permissions(member, overwrite=None)
        await voice_channel.set_permissions(member, overwrite=None)
        if await is_teamler(member):
            raise CommandError(translations.member_could_not_be_kicked)

        if member.voice is not None and member.voice.channel == voice_channel:
            await member.move_to(None)
        if text_channel is not None:
            await self.send_voice_msg(
                text_channel,
                group.public,
                translations.voice_channel,
                translations.f_user_removed_from_private_voice(member.mention),
            )
        if text_channel != ctx.channel:
            await ctx.send(translations.user_removed_from_private_voice_response)

    @voice.command(name="owner", aliases=["o"])
    async def voice_owner(self, ctx: Context, member: Optional[Member]):
        """
        transfer ownership of a private voice channel
        """

        change = member is not None
        group, dyn_channel, voice_channel, text_channel = await self.get_dynamic_voice_channel(ctx.author, change)

        if not change:
            await ctx.send(translations.f_owner_of_private_voice(f"<@{dyn_channel.owner}>"))
            return

        if member not in voice_channel.members:
            raise CommandError(translations.user_not_in_this_channel)
        if member.bot:
            raise CommandError(translations.bot_no_owner_transfer)

        await db_thread(DynamicVoiceChannel.change_owner, dyn_channel.channel_id, member.id)
        if text_channel is not None:
            await self.send_voice_msg(
                text_channel,
                group.public,
                translations.voice_channel,
                translations.f_private_voice_owner_changed(member.mention),
            )
        if text_channel != ctx.channel:
            await ctx.send(translations.private_voice_owner_changed_response)

    @voice.group(name="link", aliases=["l"])
    @Permission.vc_manage_link.check
    async def voice_link(self, ctx: Context):
        """
        manage links between voice channels and roles
        """

        if ctx.invoked_subcommand is None:
            raise UserInputError

    @voice_link.command(name="list", aliases=["l", "?"])
    async def voice_link_list(self, ctx: Context):
        """
        list all links between voice channels and roles
        """

        out = []
        guild: Guild = ctx.guild
        for link in await db_thread(db.all, RoleVoiceLink):
            role: Optional[Role] = guild.get_role(link.role)
            voice: Optional[VoiceChannel] = guild.get_channel(link.voice_channel)
            if role is None or voice is None:
                await db_thread(db.delete, link)
            else:
                out.append(f"`{voice}` (`{voice.id}`) -> `@{role}` (`{role.id}`)")

        await ctx.send("\n".join(out) or translations.no_links_created)

    @voice_link.command(name="add", aliases=["a", "+"])
    async def voice_link_add(self, ctx: Context, channel: VoiceChannel, *, role: Role):
        """
        link a voice channel with a role
        """

        if await db_thread(db.get, DynamicVoiceChannel, channel.id) is not None:
            raise CommandError(translations.link_on_dynamic_channel_not_created)
        if await db_thread(db.first, RoleVoiceLink, role=role.id, voice_channel=channel.id) is not None:
            raise CommandError(translations.link_already_exists)

        if role >= ctx.me.top_role:
            raise CommandError(translations.f_link_not_created_too_high(role, ctx.me.top_role))
        if role.managed:
            raise CommandError(translations.f_link_not_created_managed_role(role))

        await db_thread(RoleVoiceLink.create, role.id, channel.id)
        for member in channel.members:
            await member.add_roles(role)

        group: Optional[DynamicVoiceGroup] = await db_thread(db.first, DynamicVoiceGroup, channel_id=channel.id)
        if group is not None:
            for dyn_channel in await db_thread(db.all, DynamicVoiceChannel, group_id=group.id):
                dchannel: Optional[VoiceChannel] = self.bot.get_channel(dyn_channel.channel_id)
                if dchannel is not None:
                    for member in dchannel.members:
                        await member.add_roles(role)

        await ctx.send(translations.f_link_created(channel, role))
        await send_to_changelog(ctx.guild, translations.f_link_created(channel, role))

    @voice_link.command(name="remove", aliases=["del", "r", "d", "-"])
    async def voice_link_remove(self, ctx: Context, channel: VoiceChannel, *, role: Role):
        """
        delete the link between a voice channel and a role
        """

        if (link := await db_thread(db.first, RoleVoiceLink, role=role.id, voice_channel=channel.id)) is None:
            raise CommandError(translations.link_not_found)

        await db_thread(db.delete, link)
        for member in channel.members:
            await member.remove_roles(role)

        group: Optional[DynamicVoiceGroup] = await db_thread(db.first, DynamicVoiceGroup, channel_id=channel.id)
        if group is not None:
            for dyn_channel in await db_thread(db.all, DynamicVoiceChannel, group_id=group.id):
                dchannel: Optional[VoiceChannel] = self.bot.get_channel(dyn_channel.channel_id)
                if dchannel is not None:
                    for member in dchannel.members:
                        await member.remove_roles(role)

        await ctx.send(translations.link_deleted)
        await send_to_changelog(ctx.guild, translations.f_log_link_deleted(channel, role))
