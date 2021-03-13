from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class SettingsPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.settings.permissions[self.name]

    change_prefix = auto()
