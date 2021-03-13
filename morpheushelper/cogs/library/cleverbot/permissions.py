from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class CleverBotPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.cleverbot.permissions[self.name]

    cb_list = auto()
    cb_manage = auto()
    cb_reset = auto()
