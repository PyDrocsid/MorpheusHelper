from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class LoggingPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.logging.permissions[self.name]

    log_manage = auto()
