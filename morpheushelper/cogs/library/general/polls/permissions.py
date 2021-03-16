from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class PollsPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.polls.permissions[self.name]

    team_poll = auto()
    delete = auto()
