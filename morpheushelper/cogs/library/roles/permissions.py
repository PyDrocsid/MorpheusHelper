from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class RolesPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.roles.permissions[self.name]

    roles_config = auto()
    roles_auth = auto()
    list_members = auto()
