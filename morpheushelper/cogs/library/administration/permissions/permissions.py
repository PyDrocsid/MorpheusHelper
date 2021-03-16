from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class PermissionsPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.permissions.permissions[self.name]

    view_own = auto()
    view_all = auto()
    manage = auto()
