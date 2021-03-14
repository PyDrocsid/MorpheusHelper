from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class BeTheProfessionalPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.betheprofessional.permissions[self.name]

    manage = auto()
