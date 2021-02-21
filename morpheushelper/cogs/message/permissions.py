from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class Permission(BasePermission):
    send = translations.permissions["send"]
    edit = translations.permissions["edit"]
    delete = translations.permissions["delete"]
