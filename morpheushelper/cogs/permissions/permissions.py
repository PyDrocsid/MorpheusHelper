from PyDrocsid.translations import translations

from PyDrocsid.permission import BasePermission


class Permission(BasePermission):
    view_own_permissions = translations.permissions["view_own_permissions"]
    view_all_permissions = translations.permissions["view_all_permissions"]
    manage_permissions = translations.permissions["manage_permissions"]
