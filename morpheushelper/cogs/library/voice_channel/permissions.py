from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class VoiceChannelPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.voice_channel.permissions[self.name]

    vc_private_owner = auto()
    vc_manage_dyn = auto()
    vc_manage_link = auto()
