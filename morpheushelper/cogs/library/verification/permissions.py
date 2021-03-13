from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class VerificationPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.verification.permissions[self.name]

    manage_verification = auto()
