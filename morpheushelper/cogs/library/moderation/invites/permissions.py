from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class InvitesPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.invites.permissions[self.name]

    bypass = auto()
    manage = auto()
