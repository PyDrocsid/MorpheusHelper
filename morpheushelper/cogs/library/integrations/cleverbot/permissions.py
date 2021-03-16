from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class CleverBotPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.cleverbot.permissions[self.name]

    list = auto()
    manage = auto()
    reset = auto()
