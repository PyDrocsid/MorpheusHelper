import os
import re
from typing import Optional

from discord import Client, Member, VoiceState, Message, Role, DMChannel, Guild, VoiceChannel
from discord.utils import get

from database import db, run_in_thread
from models.authorizes_roles import AuthorizedRoles
from models.role_voice_link import RoleVoiceLink
from models.server import Server

db.create_tables()

DEFAULT_PREFIX = "!"


class Bot(Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")

    @staticmethod
    async def check_access(member: Member) -> int:
        if member.guild_permissions.administrator:
            return 2

        roles = set(role.id for role in member.roles)
        for auth in await run_in_thread(db.query, AuthorizedRoles, server=member.guild.id):
            if auth.role in roles:
                return 1
        return 0

    @staticmethod
    def get_prefix(guild: Guild) -> str:
        if (server := db.get(Server, guild.id)) is None:
            server = Server.create(guild.id, DEFAULT_PREFIX)

        return server.prefix

    @staticmethod
    def set_prefix(guild: Guild, prefix: str) -> str:
        if (server := db.get(Server, guild.id)) is None:
            server = Server.create(guild.id, prefix)
        else:
            server.prefix = prefix

        return server.prefix

    async def on_message(self, message: Message):
        if message.author == self.user or isinstance(message.channel, DMChannel):
            return

        guild: Guild = message.guild

        prefix: str = await run_in_thread(Bot.get_prefix, guild)

        if not message.content.startswith(prefix):
            return

        if not (permission_level := await Bot.check_access(message.author)):
            await message.channel.send(f"permission denied {message.author.mention}")
            return

        line = message.content[len(prefix):]
        cmd, *args = line.split()

        if cmd == "prefix":
            if len(args) != 1:
                await message.channel.send(f"usage: {prefix}prefix <new-prefix>")
                return

            new_prefix = args[0]
            if not 0 < len(new_prefix) <= 16:
                await message.channel.send("length of prefix must be between 1 and 16")
                return

            await run_in_thread(Bot.set_prefix, guild, new_prefix)
            await message.channel.send("prefix has been updated")
        elif cmd == "auth":
            if permission_level < 2:
                await message.channel.send(f"permission denied {message.author.mention}")
                return
            if not re.match(r"^auth (list|(add|del) (\d+))$", line):
                await message.channel.send(f"usage: {prefix}auth list|add|del [<role-id>]")
                return

            if args[0] == "list":
                roles = []
                for auth_role in await run_in_thread(db.query, AuthorizedRoles, server=guild.id):
                    if (role := guild.get_role(auth_role.role)) is not None:
                        roles.append(f" - `@{role}` (`{role.id}`)")
                if roles:
                    await message.channel.send(
                        "the following roles are authorized to control this bot:\n" + "\n".join(roles)
                    )
                else:
                    await message.channel.send("only administrators can control this bot")
            elif args[0] == "add":
                role: Optional[Role] = guild.get_role(int(args[1]))
                if role is None:
                    await message.channel.send("this role does not exist")
                    return

                auth: Optional[AuthorizedRoles] = await run_in_thread(
                    db.first, AuthorizedRoles, server=guild.id, role=role.id
                )
                if auth is not None:
                    await message.channel.send(f"role `@{role}` is already authorized")
                    return

                await run_in_thread(AuthorizedRoles.create, guild.id, role.id)
                await message.channel.send(f"role `@{role}` has been authorized to control this bot")
            elif args[0] == "del":
                role_id = int(args[1])
                auth: Optional[AuthorizedRoles] = await run_in_thread(
                    db.first, AuthorizedRoles, server=guild.id, role=role_id
                )

                if auth is None:
                    if (role := guild.get_role(role_id)) is not None:
                        await message.channel.send(f"role `@{role}` is not authorized")
                    else:
                        await message.channel.send("role is not authorized and does not exist")
                    return

                await run_in_thread(db.delete, auth)
                if (role := guild.get_role(role_id)) is not None:
                    await message.channel.send(f"role `@{role}` has been unauthorized to control this bot")
                else:
                    await message.channel.send("role has been unauthorized to control this bot")
        elif cmd == "list":
            out = [
                f"`{voice}` (`{voice.id}`) -> `@{role}` (`{role.id}`)"
                for link in await run_in_thread(db.query, RoleVoiceLink, server=guild.id)
                if (role := guild.get_role(link.role)) is not None
                and (voice := guild.get_channel(link.voice_channel)) is not None
            ]
            await message.channel.send("\n".join(out) or "no links created")
        elif cmd == "link":
            if not re.match(r"^link (\d+) ((\d+)|([a-zA-Z0-9_\-]+))$", line):
                await message.channel.send(f"usage: {prefix}link <voice-channel-id> <role-id>|<role-name>")
                return

            voice_id = int(args[0])

            if args[1].isnumeric():
                if (role := guild.get_role(int(args[1]))) is None:
                    await message.channel.send("role does not exist")
                    return
            else:
                if (role := get(guild.roles, name=args[1])) is None:
                    role = await guild.create_role(name=args[1], mentionable=True)

            if (
                await run_in_thread(db.first, RoleVoiceLink, server=guild.id, role=role.id, voice_channel=voice_id)
                is not None
            ):
                await message.channel.send("link already exists")
                return

            if (voice := guild.get_channel(voice_id)) is None or not isinstance(voice, VoiceChannel):
                await message.channel.send("voice channel does not exist")
                return

            await run_in_thread(RoleVoiceLink.create, guild.id, role.id, voice_id)
            await message.channel.send(f"link has been created between voice channel `{voice}` and role `@{role}`")
        elif cmd == "unlink":
            if not re.match(r"^unlink (\d+) ((\d+)|([a-zA-Z0-9_\-]+))$", line):
                await message.channel.send(f"usage: {prefix}unlink <voice-channel-id> <role-id>|<role-name>")
                return

            voice_id = int(args[0])

            if args[1].isnumeric():
                role_id = int(args[1])
            else:
                if (role := get(guild.roles, name=args[1])) is None:
                    await message.channel.send("role does not exist")
                    return
                role_id = role.id

            if (
                link := await run_in_thread(
                    db.first, RoleVoiceLink, server=guild.id, role=role_id, voice_channel=voice_id
                )
            ) is None:
                await message.channel.send("link does not exists")
                return

            await run_in_thread(db.delete, link)
            await message.channel.send(f"link has been deleted")
        else:
            await message.channel.send("usage: prefix|auth|list|link|unlink [<arguments>]")

    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState):
        if before.channel == after.channel:
            return

        guild: Guild = member.guild
        if before.channel is not None:
            await member.remove_roles(
                *(
                    role
                    for link in await run_in_thread(
                        db.query, RoleVoiceLink, server=guild.id, voice_channel=before.channel.id
                    )
                    if (role := guild.get_role(link.role)) is not None
                )
            )
        if after.channel is not None:
            await member.add_roles(
                *(
                    role
                    for link in await run_in_thread(
                        db.query, RoleVoiceLink, server=guild.id, voice_channel=after.channel.id
                    )
                    if (role := guild.get_role(link.role)) is not None
                )
            )


Bot().run(os.environ["TOKEN"])
