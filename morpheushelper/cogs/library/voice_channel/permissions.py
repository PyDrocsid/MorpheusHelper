from enum import auto

from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import t


class VoiceChannelPermission(BasePermission):
    @property
    def description(self) -> str:
        return t.voice_channel.permissions[self.name]

    private_owner = auto()
    manage_dyn = auto()
    manage_link = auto()
