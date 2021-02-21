from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class Permission(BasePermission):
    rr_manage = translations.permissions["rr_manage"]
