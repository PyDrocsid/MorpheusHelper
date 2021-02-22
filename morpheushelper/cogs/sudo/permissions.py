from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class Permission(BasePermission):
    reload = translations.permissions["reload"]
    stop = translations.permissions["stop"]
    kill = translations.permissions["kill"]
