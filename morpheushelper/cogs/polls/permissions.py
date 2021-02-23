from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class PollsPermission(BasePermission):
    team_poll = translations.permissions["team_poll"]
    polls_delete = translations.permissions["polls_delete"]
