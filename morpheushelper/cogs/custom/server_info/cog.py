from typing import Optional

from discord import Member, Role, Guild

from PyDrocsid.settings import RoleSettings
from PyDrocsid.translations import t
from cogs.library import ServerInfoCog

t = t.server_info


class CustomServerInfoCog(ServerInfoCog, name="Server Information"):
    async def get_users(self, guild: Guild) -> list[tuple[str, list[Member]]]:
        async def get_role(role_name) -> Optional[Role]:
            return guild.get_role(await RoleSettings.get(role_name))

        out = []

        role: Role
        if (role := await get_role("admin")) is not None and role.members:
            out.append((t.cnt_admins(cnt=len(role.members)), role.members))
        if (role := await get_role("mod")) is not None and role.members:
            out.append((t.cnt_mods(cnt=len(role.members)), role.members))

        return out
