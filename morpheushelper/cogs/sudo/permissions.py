from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class SudoPermission(BasePermission):
    reload = translations.permissions["reload"]
    stop = translations.permissions["stop"]
    kill = translations.permissions["kill"]
