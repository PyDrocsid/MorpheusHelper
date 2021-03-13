from PyDrocsid.translations import t
from cogs.library.roles.cog import RolesCog

t = t.roles


class CustomRolesCog(RolesCog):
    async def get_configurable_roles(self) -> list[tuple[str, str, bool]]:
        return [
            ("admin", t.admin, False),
            ("mod", t.mod, False),
            ("supp", t.supp, False),
            ("team", t.team, False),
            ("mute", t.mute, True),
        ]
