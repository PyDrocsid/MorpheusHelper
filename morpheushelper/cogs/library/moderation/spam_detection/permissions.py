from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class SpamDetectionPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.spam_detection.permissions[self.name]

    manage = auto()
