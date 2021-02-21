from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class Permission(BasePermission):
    rp_pin = translations.permissions["rp_pin"]
    rp_manage = translations.permissions["rp_manage"]
