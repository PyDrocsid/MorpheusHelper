from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class MetaQuestionPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.metaquestion.permissions[self.name]

    reduce = auto()
