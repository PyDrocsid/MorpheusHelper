from PyDrocsid.permission import BasePermission
from PyDrocsid.translations import translations


class RedditPermission(BasePermission):
    manage_reddit = translations.permissions["manage_reddit"]
