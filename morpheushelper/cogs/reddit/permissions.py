from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class Permission(BasePermission):
    manage_reddit = translations.permissions["manage_reddit"]
