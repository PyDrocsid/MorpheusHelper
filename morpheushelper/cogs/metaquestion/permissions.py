from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class Permission(BasePermission):
    mq_reduce = translations.permissions["mq_reduce"]
