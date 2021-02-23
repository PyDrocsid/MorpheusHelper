from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class MediaOnlyPermission(BasePermission):
    mo_bypass = translations.permissions["mo_bypass"]
    mo_manage = translations.permissions["mo_manage"]
