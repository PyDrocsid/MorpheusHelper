from enum import Enum, auto

from database import run_in_thread
from models.permissions import PermissionModel
from translations import translations


class Permission(Enum):
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

    @property
    def description(self) -> str:
        return translations.permissions[self.name]

    async def resolve(self) -> int:
        return await run_in_thread(PermissionModel.get, self.name)

    async def set(self, level: int):
        await run_in_thread(PermissionModel.set, self.name, level)
