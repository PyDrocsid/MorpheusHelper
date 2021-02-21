from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class Permission(BasePermission):
    manage_verification = translations.permissions["manage_verification"]
