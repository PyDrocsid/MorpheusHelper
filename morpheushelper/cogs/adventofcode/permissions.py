from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class Permission(BasePermission):
    aoc_clear = translations.permissions["aoc_clear"]
    aoc_link = translations.permissions["aoc_link"]
    aoc_role = translations.permissions["aoc_role"]
