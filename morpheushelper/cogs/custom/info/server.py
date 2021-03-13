from typing import Optional

from PyDrocsid.database import db_thread, db
from discord import Member, Role, Guild

from PyDrocsid.settings import Settings
from PyDrocsid.translations import t
from cogs.library import ServerInfoCog
from cogs.library.betheprofessional.models import BTPRole
from cogs.library.invites.models import AllowedInvite

t = t.info


class CustomServerInfoCog(ServerInfoCog):
    async def get_users(self, guild: Guild) -> list[tuple[str, list[Member]]]:
        async def get_role(role_name) -> Optional[Role]:
            return guild.get_role(await Settings.get(int, role_name + "_role"))

        out = []

        role: Role
        if (role := await get_role("admin")) is not None and role.members:
            out.append((t.cnt_admins(len(role.members)), role.members))
        if (role := await get_role("mod")) is not None and role.members:
            out.append((t.cnt_mods(len(role.members)), role.members))
        if (role := await get_role("supp")) is not None and role.members:
            out.append((t.cnt_supps(len(role.members)), role.members))

        return out

    async def get_additional_fields(self, guild: Guild) -> list[tuple[str, str]]:
        return [
            (t.topics, t.cnt_topics(len(await db_thread(db.all, BTPRole)))),
            (
                t.allowed_discord_server,
                t.cnt_servers_whitelisted(len(await db_thread(db.all, AllowedInvite))),
            ),
        ]
