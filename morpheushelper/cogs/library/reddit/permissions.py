from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class RedditPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.reddit.permissions[self.name]

    manage_reddit = auto()
