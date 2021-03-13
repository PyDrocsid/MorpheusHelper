from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class ReactionPinPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.reactionpin.permissions[self.name]

    rp_pin = auto()
    rp_manage = auto()
