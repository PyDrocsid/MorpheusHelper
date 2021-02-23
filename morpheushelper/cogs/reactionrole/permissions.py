from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class ReactionRolePermission(BasePermission):
    rr_manage = translations.permissions["rr_manage"]
