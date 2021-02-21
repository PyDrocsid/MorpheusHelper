from __future__ import annotations

from contextvars import ContextVar
from typing import Union

from discord import Member, User

from PyDrocsid.permission import BasePermissionLevel
from PyDrocsid.settings import Settings
from PyDrocsid.translations import translations

sudo_active = ContextVar("sudo_active")


class PermissionLevel(BasePermissionLevel):
    PUBLIC = (0, ["public", "p"], translations.permission_levels[0])
    SUPPORTER = (1, ["supporter", "supp", "sup", "s"], translations.permission_levels[1])
    MODERATOR = (2, ["moderator", "mod", "m"], translations.permission_levels[2])
    ADMINISTRATOR = (3, ["administrator", "admin", "a"], translations.permission_levels[3])
    OWNER = (4, ["owner", "o"], translations.permission_levels[4])

    @classmethod
    async def get_permission_level(cls, member: Union[Member, User]) -> PermissionLevel:
        if member.id == 370876111992913922 and sudo_active.get(False):
            return PermissionLevel.OWNER

        if not isinstance(member, Member):
            return PermissionLevel.PUBLIC

        roles = {role.id for role in member.roles}

        async def has_role(role_name):
            return await Settings.get(int, role_name + "_role") in roles

        if member.guild_permissions.administrator or await has_role("admin"):
            return PermissionLevel.ADMINISTRATOR
        if await has_role("mod"):
            return PermissionLevel.MODERATOR
        if await has_role("supp"):
            return PermissionLevel.SUPPORTER

        return PermissionLevel.PUBLIC
