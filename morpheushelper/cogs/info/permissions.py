from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class InfoPermission(BasePermission):
    admininfo = translations.permissions["admininfo"]
