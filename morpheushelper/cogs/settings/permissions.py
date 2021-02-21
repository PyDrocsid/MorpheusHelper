from PyDrocsid.translations import translations

from PyDrocsid.permission import BasePermission


class Permission(BasePermission):
    change_prefix = translations.permissions["change_prefix"]
