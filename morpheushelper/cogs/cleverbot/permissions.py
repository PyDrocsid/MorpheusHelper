from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class Permission(BasePermission):
    cb_list = translations.permissions["cb_list"]
    cb_manage = translations.permissions["cb_manage"]
    cb_reset = translations.permissions["cb_reset"]
