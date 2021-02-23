from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class VoiceChannelPermission(BasePermission):
    vc_private_owner = translations.permissions["vc_private_owner"]
    vc_manage_dyn = translations.permissions["vc_manage_dyn"]
    vc_manage_link = translations.permissions["vc_manage_link"]
