from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class ReactionRolePermission(BasePermission):
    @property
    def description(self) -> str:
        return t.reactionrole.permissions[self.name]

    rr_manage = auto()
