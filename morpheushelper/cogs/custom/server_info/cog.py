from typing import Optional

from discord import Member, Role, Guild

from PyDrocsid.database import db
from PyDrocsid.settings import RoleSettings
from PyDrocsid.translations import t
from cogs.library import ServerInfoCog
from cogs.library.general.betheprofessional.models import BTPRole
from cogs.library.moderation.invites.models import AllowedInvite

t = t.server_info


class CustomServerInfoCog(ServerInfoCog, name="Server Information"):
    async def get_users(self, guild: Guild) -> list[tuple[str, list[Member]]]:
        async def get_role(role_name) -> Optional[Role]:
            return guild.get_role(await RoleSettings.get(role_name))

        out = []

        role: Role
        if (role := await get_role("admin")) is not None and role.members:
            out.append((t.cnt_admins(cnt=len(role.members)), role.members))
        if (role := await get_role("op")) is not None and role.members:
            out.append((t.cnt_ops(cnt=len(role.members)), role.members))
        if (role := await get_role("mod")) is not None and role.members:
            out.append((t.cnt_mods(cnt=len(role.members)), role.members))

        return out

    async def get_additional_fields(self, guild: Guild) -> list[tuple[str, str]]:
        return [
            (t.topics, t.cnt_topics(cnt=await db.count(BTPRole))),
            (
                t.allowed_discord_server,
                t.cnt_servers_whitelisted(cnt=await db.count(AllowedInvite)),
            ),
        ]
