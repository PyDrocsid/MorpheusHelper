from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class ModPermission(BasePermission):
    warn = translations.permissions["warn"]
    mute = translations.permissions["mute"]
    kick = translations.permissions["kick"]
    ban = translations.permissions["ban"]
    view_stats = translations.permissions["view_stats"]
    init_join_log = translations.permissions["init_join_log"]
    manage_roles = translations.permissions["manage_roles"]
