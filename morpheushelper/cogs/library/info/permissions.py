from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class InfoPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.info.permissions[self.name]

    admininfo = auto()
