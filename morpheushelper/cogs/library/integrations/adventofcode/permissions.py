from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class AdventOfCodePermission(BasePermission):
    @property
    def description(self) -> str:
        return t.adventofcode.permissions[self.name]

    clear = auto()
    link = auto()
    role = auto()
