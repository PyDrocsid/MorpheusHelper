from contextvars import ContextVar
from enum import auto
from typing import Union

from PyDrocsid.permission import BasePermission, BasePermissionLevel
from PyDrocsid.settings import Settings
from discord import Member, User

sudo_active = ContextVar("sudo_active")


class Permission(BasePermission):
    vc_private_owner = auto()
    vc_manage_dyn = auto()
    vc_manage_link = auto()

    send = auto()
    edit = auto()
    delete = auto()

    rr_manage = auto()

    rp_pin = auto()
    rp_manage = auto()

    news_manage = auto()

    warn = auto()
    mute = auto()
    kick = auto()
    ban = auto()
    view_stats = auto()
    init_join_log = auto()

    manage_autokick = auto()
    manage_instantkick = auto()

    manage_verification = auto()

    mq_reduce = auto()

    mo_bypass = auto()
    mo_manage = auto()

    btp_manage = auto()

    cb_list = auto()
    cb_manage = auto()
    cb_reset = auto()

    invite_bypass = auto()
    invite_manage = auto()

    log_manage = auto()

    change_prefix = auto()
    admininfo = auto()
    view_own_permissions = auto()
    view_all_permissions = auto()

    manage_reddit = auto()

    aoc_clear = auto()
    aoc_link = auto()
    aoc_role = auto()

    @property
    def default_permission_level(self) -> "BasePermissionLevel":
        return PermissionLevel.ADMINISTRATOR


class PermissionLevel(BasePermissionLevel):
    PUBLIC, SUPPORTER, MODERATOR, ADMINISTRATOR, OWNER = range(5)

    @classmethod
    async def get_permission_level(cls, member: Union[Member, User]) -> "PermissionLevel":
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
