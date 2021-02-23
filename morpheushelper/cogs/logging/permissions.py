from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class LoggingPermission(BasePermission):
    log_manage = translations.permissions["log_manage"]
