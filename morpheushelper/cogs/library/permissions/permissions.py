from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class PermissionsPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.permissions.permissions[self.name]

    view_own_permissions = auto()
    view_all_permissions = auto()
    manage_permissions = auto()
