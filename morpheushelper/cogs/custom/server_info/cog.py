from typing import Optional

from discord import Member, Role, Guild

from PyDrocsid.database import db_thread, db
from PyDrocsid.settings import Settings
from PyDrocsid.translations import t
from cogs.library import ServerInfoCog
from cogs.library.general.betheprofessional.models import BTPRole
from cogs.library.moderation.invites.models import AllowedInvite

t = t.server_info


class CustomServerInfoCog(ServerInfoCog):
    async def get_users(self, guild: Guild) -> list[tuple[str, list[Member]]]:
        async def get_role(role_name) -> Optional[Role]:
            return guild.get_role(await Settings.get(int, role_name + "_role"))

        out = []

        role: Role
        if (role := await get_role("admin")) is not None and role.members:
            out.append((t.cnt_admins(cnt=len(role.members)), role.members))
        if (role := await get_role("mod")) is not None and role.members:
            out.append((t.cnt_mods(cnt=len(role.members)), role.members))
        if (role := await get_role("supp")) is not None and role.members:
            out.append((t.cnt_supps(cnt=len(role.members)), role.members))

        return out

    async def get_additional_fields(self, guild: Guild) -> list[tuple[str, str]]:
        return [
            (t.topics, t.cnt_topics(cnt=len(await db_thread(db.all, BTPRole)))),
            (
                t.allowed_discord_server,
                t.cnt_servers_whitelisted(cnt=len(await db_thread(db.all, AllowedInvite))),
            ),
        ]
