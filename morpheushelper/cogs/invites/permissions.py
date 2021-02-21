from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class Permission(BasePermission):
    invite_bypass = translations.permissions["invite_bypass"]
    invite_manage = translations.permissions["invite_manage"]
