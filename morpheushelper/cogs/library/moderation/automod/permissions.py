from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class AutoModPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.automod.permissions[self.name]

    manage_autokick = auto()
    manage_instantkick = auto()
