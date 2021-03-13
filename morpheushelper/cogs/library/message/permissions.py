from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class MessagePermission(BasePermission):
    @property
    def description(self) -> str:
        return t.message.permissions[self.name]

    send = auto()
    edit = auto()
    delete = auto()
